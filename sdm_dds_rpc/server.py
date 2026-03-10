"""
RPC 서버 - 요청 수신 후 핸들러 호출 및 응답 발행
"""

import threading
import time
import uuid
from collections.abc import Callable
from typing import Any, Type

from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
from cyclonedds.core import ReadCondition, SampleState, ViewState, InstanceState, WaitSet
from cyclonedds.util import duration

from sdm_dds_rpc.exceptions import RPCRemoteError, RPCDuplicateInstanceError

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

REGISTRY_TOPIC = "RPC/ServiceRegistry"
REGISTRY_CHECK_WAIT_SEC = 3.0


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
        participant, REGISTRY_TOPIC, ServiceRegistryEntry
    )
    reg_reader = DataReader(participant, reg_topic)
    reg_writer = DataWriter(participant, reg_topic)

    time.sleep(REGISTRY_CHECK_WAIT_SEC)

    entry = ServiceRegistryEntry(
        service_name=service_name,
        instance_name=instance_name,
        server_guid=server_guid,
    )
    reg_writer.write(entry)
    time.sleep(1.0)

    guids_for_key: set[str] = set()
    for sample in reg_reader.take(N=100):
        if (
            hasattr(sample, "service_name")
            and str(sample.service_name).strip() == service_name
            and hasattr(sample, "instance_name")
            and str(sample.instance_name).strip() == instance_name
        ):
            g = getattr(sample, "server_guid", "") or ""
            guids_for_key.add(str(g).strip())

    if len(guids_for_key) > 1:
        raise RPCDuplicateInstanceError(
            f"서비스 '{service_name}' 인스턴스 '{instance_name}'이(가) 이미 등록되어 있습니다."
        )


class RpcServer:
    """
    RPC 서버. register_service()로 핸들러 등록 후 run()으로 이벤트 루프 실행.

    instance_name 지정 시 해당 인스턴스만 요청 처리.
    중복 인스턴스명 등록 시 RPCDuplicateInstanceError 발생.
    """

    def __init__(self, domain_id: int = 0):
        """
        Args:
            domain_id: DDS 도메인 ID
        """
        self._domain_id = domain_id
        self._participant = DomainParticipant(domain_id=domain_id)
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
        self._registry_writers: list[DataWriter] = []
        self._heartbeat_stop = threading.Event()

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
            RPCDuplicateInstanceError: 중복 인스턴스명으로 등록 시도 시
        """
        inst = instance_name or ""
        reg_writer: DataWriter | None = None

        if inst:
            server_guid = str(uuid.uuid4())
            _check_duplicate_instance(
                self._participant, name, inst, server_guid
            )
            reg_topic = Topic(
                self._participant, REGISTRY_TOPIC, ServiceRegistryEntry
            )
            reg_writer = DataWriter(self._participant, reg_topic)
            entry = ServiceRegistryEntry(
                service_name=name,
                instance_name=inst,
                server_guid=server_guid,
            )
            reg_writer.write(entry)
            self._registry_writers.append(reg_writer)

        req_topic_name = f"{name}/Request"
        rep_topic_name = f"{name}/Reply"

        req_topic = Topic(self._participant, req_topic_name, request_type)
        rep_topic = Topic(self._participant, rep_topic_name, response_type)

        reader = DataReader(self._participant, req_topic)
        writer = DataWriter(self._participant, rep_topic)

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
        """레지스트리 하트비트 (인스턴스 지정 서버만)."""
        while not self._heartbeat_stop.wait(timeout=2.0):
            for _, svc in self._services.items():
                reg_writer = svc[6]
                if reg_writer is not None:
                    # 마지막 등록 정보 재발행 (간단히 유지)
                    pass  # 주기적 재발행은 선택. 현재는 최초 1회만.

    def run(self) -> None:
        """이벤트 루프 실행 (블로킹). Ctrl+C로 종료."""
        if not self._services:
            return

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
            for rc in conditions:
                waitset.detach(rc)
            self._heartbeat_stop.set()
            self._running = False

    def stop(self) -> None:
        """이벤트 루프 종료."""
        self._running = False
