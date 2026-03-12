"""
RPC 서버 - 요청 수신 후 핸들러 호출 및 응답 발행
"""

import threading
import time
import uuid
from collections.abc import Callable
from typing import Any, Optional, Type

from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
from cyclonedds.qos import Qos, Policy
from cyclonedds.core import (
    ReadCondition,
    SampleState,
    ViewState,
    InstanceState,
    WaitSet,
    DDSStatus,
)
from cyclonedds.util import duration

from sdm_dds_rpc.exceptions import (
    ConfigurationError,
    RPCClosedError,
    RPCRemoteError,
    RPCDuplicateInstanceError,
)

try:
    from rpc import RemoteExceptionCode, ServiceRegistryEntry
except ImportError:

    class RemoteExceptionCode:
        REMOTE_EX_OK = 0
        REMOTE_EX_UNKNOWN_EXCEPTION = 5

    class ServiceRegistryEntry:
        service_name: str = ""
        instance_name: str = ""
        server_guid: str = ""

# QoS 타입 (cyclonedds.qos.Qos)
QosType = Any

REGISTRY_TOPIC = "RPC/ServiceRegistry"
REGISTRY_CHECK_WAIT_SEC = 3.0

# 레지스트리: Volatile - 서버 종료 시 항목 제거, 하트비트로 동작 중인 서버만 노출
_REGISTRY_QOS = Qos(
    Policy.Durability.Volatile,
    Policy.History.KeepLast(depth=10),
)


def _copy_header_to_reply(
    request: Any, reply: Any, server_instance: str = ""
) -> None:
    """request.header를 reply.header에 복사 (related_request_id, server_instance)."""
    if not hasattr(request, "header") or not hasattr(reply, "header"):
        return
    req_h = request.header
    rep_h = reply.header
    if hasattr(req_h, "request_id") and hasattr(rep_h, "related_request_id"):
        rep_h.related_request_id = req_h.request_id
    if hasattr(rep_h, "remote_ex"):
        rep_h.remote_ex = RemoteExceptionCode.REMOTE_EX_OK
    if hasattr(rep_h, "server_instance"):
        rep_h.server_instance = server_instance


def _check_duplicate_instance(
    participant: DomainParticipant,
    service_name: str,
    instance_name: str,
    server_guid: str,
) -> None:
    """동일 (service_name, instance_name) 등록 여부 확인. 중복 시 RPCDuplicateInstanceError."""
    reg_topic = Topic(
        participant, REGISTRY_TOPIC, ServiceRegistryEntry, qos=_REGISTRY_QOS.topic()
    )
    reg_reader = DataReader(participant, reg_topic, qos=_REGISTRY_QOS.datareader())
    reg_reader.set_status_mask(DDSStatus.SubscriptionMatched)
    reg_writer = DataWriter(participant, reg_topic, qos=_REGISTRY_QOS.datawriter())

    ws = WaitSet(participant)
    ws.attach(reg_reader)
    try:
        ws.wait(duration(seconds=REGISTRY_CHECK_WAIT_SEC))
    finally:
        ws.detach(reg_reader)

    entry = ServiceRegistryEntry(
        service_name=service_name,
        instance_name=instance_name,
        server_guid=server_guid,
    )
    reg_writer.write(entry)
    time.sleep(1.5)

    other_guid_seen = False
    for sample in reg_reader.take(N=100):
        if (
            hasattr(sample, "service_name")
            and str(sample.service_name).strip() == service_name
            and hasattr(sample, "instance_name")
            and str(sample.instance_name).strip() == instance_name
        ):
            g = str(getattr(sample, "server_guid", "") or "").strip()
            if g != server_guid:
                other_guid_seen = True
                break

    if other_guid_seen:
        raise RPCDuplicateInstanceError(
            f"서비스 '{service_name}' 인스턴스 '{instance_name}'이(가) 이미 등록되어 있습니다."
        )


class RpcServer:
    """
    RPC 서버. register_service()로 핸들러 등록 후 run()으로 이벤트 루프 실행.

    instance_name 지정 시 해당 인스턴스만 요청 처리.
    중복 인스턴스명 등록 시 RPCDuplicateInstanceError 발생.
    """

    def __init__(
        self,
        participant: Optional[DomainParticipant] = None,
        domain_id: int = 0,
        qos: Optional[QosType] = None,
    ) -> None:
        """
        Args:
            participant: 기존 DomainParticipant. None이면 domain_id로 생성.
            domain_id: participant가 None일 때 사용할 DDS 도메인 ID (기본 0).
            qos: Request/Reply 토픽용 QoS (topic(), datareader(), datawriter() 사용).
        """
        if participant is None and domain_id < 0:
            raise ConfigurationError(
                f"domain_id는 0 이상이어야 합니다. (현재: {domain_id})"
            )
        if participant is not None:
            self._participant = participant
        else:
            self._participant = DomainParticipant(domain_id=domain_id)
        self._qos = qos
        self._services: dict[
            str,
            tuple[
                type,
                type,
                Callable[[Any], Any],
                DataReader,
                DataWriter,
                str,
                DataWriter | None,
            ],
        ] = {}
        self._running = False
        self._registry_entries: list[tuple[DataWriter, ServiceRegistryEntry]] = []
        self._heartbeat_stop = threading.Event()
        self._closed = False

    def close(self) -> None:
        """리소스를 정리합니다. run() 중이면 stop() 후 정리."""
        if self._closed:
            return
        self._closed = True
        self.stop()
        self._services.clear()
        self._registry_entries.clear()
        self._participant = None  # type: ignore

    def __enter__(self) -> "RpcServer":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def register_service(
        self,
        name: str,
        request_type: type,
        response_type: type,
        handler: Callable[[Any], Any],
        instance_name: str | None = None,
    ) -> None:
        """
        서비스 등록.

        Args:
            name: 서비스 이름
            request_type: Request 타입 클래스
            response_type: Response 타입 클래스
            handler: (request) -> response 콜러블
            instance_name: 서버 인스턴스명. 지정 시 해당 인스턴스만 요청 처리.
                동일 (name, instance_name)이 이미 등록되어 있으면 RPCDuplicateInstanceError.

        Raises:
            RPCClosedError: close() 호출 후
            RPCDuplicateInstanceError: 중복 인스턴스명으로 등록 시도 시
        """
        if self._closed:
            raise RPCClosedError("RpcServer가 이미 close()되었습니다.")
        inst = instance_name or ""
        reg_writer: DataWriter | None = None

        if inst:
            server_guid = str(uuid.uuid4())
            _check_duplicate_instance(
                self._participant, name, inst, server_guid
            )
            reg_topic = Topic(
                self._participant, REGISTRY_TOPIC, ServiceRegistryEntry, qos=_REGISTRY_QOS.topic()
            )
            reg_writer = DataWriter(self._participant, reg_topic, qos=_REGISTRY_QOS.datawriter())
            entry = ServiceRegistryEntry(
                service_name=name,
                instance_name=inst,
                server_guid=server_guid,
            )
            reg_writer.write(entry)
            self._registry_entries.append((reg_writer, entry))

        req_topic_name = f"{name}/Request"
        rep_topic_name = f"{name}/Reply"

        topic_qos = (
            self._qos.topic()
            if self._qos is not None and hasattr(self._qos, "topic")
            else None
        )
        reader_qos = (
            self._qos.datareader()
            if self._qos is not None and hasattr(self._qos, "datareader")
            else None
        )
        writer_qos = (
            self._qos.datawriter()
            if self._qos is not None and hasattr(self._qos, "datawriter")
            else None
        )

        req_topic = Topic(
            self._participant, req_topic_name, request_type, qos=topic_qos
        )
        rep_topic = Topic(
            self._participant, rep_topic_name, response_type, qos=topic_qos
        )
        reader = DataReader(
            self._participant, req_topic, qos=reader_qos
        )
        writer = DataWriter(
            self._participant, rep_topic, qos=writer_qos
        )

        self._services[name] = (
            request_type,
            response_type,
            handler,
            reader,
            writer,
            inst,
            reg_writer,
        )

    def _heartbeat_loop(self) -> None:
        """레지스트리 하트비트 (늦게 참여하는 reader가 수신할 수 있도록 재발행)."""
        while not self._heartbeat_stop.wait(timeout=1.5):
            for writer, entry in self._registry_entries:
                writer.write(entry)

    def run(self) -> None:
        """이벤트 루프 실행 (블로킹). Ctrl+C로 종료."""
        if self._closed:
            raise RPCClosedError("RpcServer가 이미 close()되었습니다.")
        if not self._services:
            return

        hb_thread = None
        if self._registry_entries:
            hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            hb_thread.start()

        conditions = []
        readers = []
        handlers = []
        writers = []
        instance_names = []

        for name, (_, _, handler, reader, writer, inst, _) in self._services.items():
            rc = ReadCondition(
                reader,
                SampleState.NotRead | ViewState.Any | InstanceState.Alive,
            )
            conditions.append(rc)
            readers.append(reader)
            handlers.append(handler)
            writers.append(writer)
            instance_names.append(inst)

        waitset = WaitSet(self._participant)
        for rc in conditions:
            waitset.attach(rc)

        self._running = True
        try:
            while self._running:
                if waitset.wait(duration(seconds=1)) == 0:
                    continue
                for i, (reader, handler, writer, inst) in enumerate(
                    zip(readers, handlers, writers, instance_names)
                ):
                    for request in reader.take(
                        N=20,
                        condition=conditions[i],
                    ):
                        req_inst = ""
                        if hasattr(request, "header") and hasattr(
                            request.header, "instance_name"
                        ):
                            req_inst = str(
                                request.header.instance_name or ""
                            ).strip()

                        if inst:
                            if req_inst != inst:
                                continue
                        elif req_inst:
                            continue

                        try:
                            reply = handler(request)
                            _copy_header_to_reply(
                                request, reply, server_instance=inst
                            )
                            writer.write(reply)
                        except Exception:
                            reply_type = self._services[
                                list(self._services.keys())[i]
                            ][1]
                            try:
                                reply = reply_type()
                                _copy_header_to_reply(
                                    request, reply, server_instance=inst
                                )
                                reply.header.remote_ex = (
                                    RemoteExceptionCode.REMOTE_EX_UNKNOWN_EXCEPTION
                                )
                                if hasattr(reply.header, "server_instance"):
                                    reply.header.server_instance = inst
                                writer.write(reply)
                            except Exception:
                                pass
                            raise
        finally:
            self._heartbeat_stop.set()
            for rc in conditions:
                waitset.detach(rc)
            self._running = False

    def stop(self) -> None:
        """이벤트 루프 종료."""
        self._running = False
