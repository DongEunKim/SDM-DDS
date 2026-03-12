"""
RPC 클라이언트 - 동기 요청-응답 호출
"""

import time
import uuid
from typing import Any, Optional, Type, TypeVar

from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
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
    RPCTimeoutError,
    RPCRemoteError,
)
from cyclonedds.qos import Qos, Policy

try:
    from rpc import RemoteExceptionCode
    REMOTE_EX_OK = RemoteExceptionCode.REMOTE_EX_OK
except ImportError:
    REMOTE_EX_OK = 0

# QoS 타입 (cyclonedds.qos.Qos)
QosType = Any

T = TypeVar("T")

DISCOVERY_WAIT_SEC = 3.0  # 서버 discovery 대기 시간


def _wait_for_server(
    participant: DomainParticipant,
    req_writer: DataWriter,
    wait_sec: float,
) -> None:
    """서버(DataReader) discovery 완료까지 대기."""
    ws = WaitSet(participant)
    ws.attach(req_writer)
    try:
        ws.wait(duration(seconds=wait_sec))
    except Exception:
        pass
    finally:
        ws.detach(req_writer)


def _ensure_header(request: Any, instance: str | None = None) -> None:
    """request.header.request_id, instance_name 설정."""
    rid = str(uuid.uuid4())
    if hasattr(request, "header") and hasattr(request.header, "request_id"):
        request.header.request_id = rid
    if hasattr(request, "header") and hasattr(request.header, "instance_name"):
        request.header.instance_name = (instance or "")


class RpcClient:
    """
    RPC 클라이언트. call()로 동기 요청-응답 호출.

    사용자는 request_id, 토픽명 등을 직접 다룰 필요가 없습니다.
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
            qos: Request/Reply 토픽용 QoS (topic(), datawriter(), datareader() 사용).
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
        self._request_writers: dict[str, tuple[Topic, DataWriter]] = {}
        self._reply_readers: dict[str, tuple[Topic, DataReader]] = {}
        self._closed = False

    def close(self) -> None:
        """리소스를 정리합니다. close() 후 call()/list_servers() 호출 시 RPCClosedError."""
        if self._closed:
            return
        self._closed = True
        self._request_writers.clear()
        self._reply_readers.clear()
        self._participant = None  # type: ignore

    def __enter__(self) -> "RpcClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def call(
        self,
        service_name: str,
        request: Any,
        response_type: Type[T],
        timeout: float = 5.0,
        instance: str | None = None,
    ) -> T:
        """
        동기 RPC 호출.

        Args:
            service_name: 서비스 이름 (토픽 prefix: {service_name}/Request, {service_name}/Reply)
            request: Request 인스턴스 (header는 SDK가 자동 설정)
            response_type: Reply 타입 클래스 (역직렬화용)
            timeout: 대기 시간(초)
            instance: 대상 서버 인스턴스명. None이면 아무 서버나 응답.

        Returns:
            Response 인스턴스 (response.header.server_instance로 응답 서버 확인 가능)

        Raises:
            RPCClosedError: close() 호출 후
            RPCTimeoutError: timeout 초과
            RPCRemoteError: 서버가 remote_ex != OK 로 응답
        """
        if self._closed:
            raise RPCClosedError("RpcClient가 이미 close()되었습니다.")
        _ensure_header(request, instance)
        request_id = request.header.request_id

        req_topic_name = f"{service_name}/Request"
        rep_topic_name = f"{service_name}/Reply"

        request_type = type(request)

        topic_qos = (
            self._qos.topic() if self._qos is not None and hasattr(self._qos, "topic") else None
        )
        writer_qos = (
            self._qos.datawriter()
            if self._qos is not None and hasattr(self._qos, "datawriter")
            else None
        )
        reader_qos = (
            self._qos.datareader()
            if self._qos is not None and hasattr(self._qos, "datareader")
            else None
        )

        if service_name not in self._request_writers:
            req_topic = Topic(
                self._participant, req_topic_name, request_type, qos=topic_qos
            )
            req_writer = DataWriter(
                self._participant, req_topic, qos=writer_qos
            )
            req_writer.set_status_mask(DDSStatus.PublicationMatched)
            self._request_writers[service_name] = (req_topic, req_writer)

        if service_name not in self._reply_readers:
            rep_topic = Topic(
                self._participant, rep_topic_name, response_type, qos=topic_qos
            )
            rep_reader = DataReader(
                self._participant, rep_topic, qos=reader_qos
            )
            self._reply_readers[service_name] = (rep_topic, rep_reader)

        _, req_writer = self._request_writers[service_name]
        _, rep_reader = self._reply_readers[service_name]

        # 서버(DataReader) 발견 대기 - discovery 완료 후 요청 전송
        discovery_wait = min(DISCOVERY_WAIT_SEC, max(0.5, timeout * 0.5))
        _wait_for_server(self._participant, req_writer, discovery_wait)

        req_writer.write(request)

        read_cond = ReadCondition(
            rep_reader,
            SampleState.NotRead | ViewState.Any | InstanceState.Alive,
        )
        waitset = WaitSet(self._participant)
        waitset.attach(read_cond)

        deadline = time.monotonic() + timeout
        try:
            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                to_wait = min(1.0, remaining)
                n = waitset.wait(duration(seconds=to_wait))
                if n == 0:
                    continue
                for sample in rep_reader.take(
                    N=20,
                    condition=read_cond,
                ):
                    if (
                        hasattr(sample, "header")
                        and hasattr(sample.header, "related_request_id")
                        and sample.header.related_request_id == request_id
                    ):
                        if hasattr(sample.header, "remote_ex"):
                            rex = sample.header.remote_ex
                            if rex != REMOTE_EX_OK:
                                code = (
                                    rex.value
                                    if hasattr(rex, "value")
                                    else int(rex)
                                )
                                raise RPCRemoteError(
                                    f"원격 예외 코드: {code}",
                                    code,
                                )
                        return sample
        finally:
            waitset.detach(read_cond)

        raise RPCTimeoutError(
            f"서비스 '{service_name}' 호출 타임아웃 ({timeout}초)"
        )

    def list_servers(
        self,
        service_name: str | None = None,
        timeout: float = 3.0,
    ) -> list[tuple[str, str]]:
        """
        등록된 서버 목록 조회.

        Args:
            service_name: 서비스 이름. None이면 전체 서비스.
            timeout: 레지스트리 discovery 대기 시간(초)

        Returns:
            [(service_name, instance_name), ...] 목록
        """
        if self._closed:
            raise RPCClosedError("RpcClient가 이미 close()되었습니다.")
        try:
            from rpc import ServiceRegistryEntry
        except ImportError:
            return []

        _registry_qos = Qos(
            Policy.Durability.Volatile,
            Policy.History.KeepLast(depth=10),
        )
        reg_topic = Topic(
            self._participant,
            "RPC/ServiceRegistry",
            ServiceRegistryEntry,
            qos=_registry_qos.topic(),
        )
        reg_reader = DataReader(self._participant, reg_topic, qos=_registry_qos.datareader())
        reg_reader.set_status_mask(DDSStatus.SubscriptionMatched)

        ws = WaitSet(self._participant)
        ws.attach(reg_reader)
        try:
            ws.wait(duration(seconds=timeout))
        finally:
            ws.detach(reg_reader)

        time.sleep(1.0)

        result: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for _ in range(3):
            for sample in reg_reader.take(N=100):
                if hasattr(sample, "service_name") and hasattr(sample, "instance_name"):
                    svc = str(sample.service_name).strip()
                    inst = str(sample.instance_name).strip()
                    key = (svc, inst)
                    if key not in seen:
                        seen.add(key)
                        if service_name is None or svc == service_name:
                            result.append((svc, inst))
            if result:
                break
            time.sleep(0.5)
        return result
