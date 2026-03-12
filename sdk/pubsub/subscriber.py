"""
Subscriber - DDS 토픽 구독용 간편 래퍼

콜백 모드:
    def on_msg(msg):
        print(msg)
    subscriber = Subscriber("HelloWorld", datatype=HelloWorld, on_message=on_msg)

폴링 모드:
    subscriber = Subscriber("HelloWorld", datatype=HelloWorld)
    for msg in subscriber.read():
        print(msg)
"""

from __future__ import annotations

from typing import Any, Callable, Iterator, Optional, Type, TypeVar, Union

from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.sub import DataReader
from cyclonedds.core import Listener, ReadCondition, ViewState, InstanceState, SampleState, WaitSet
from cyclonedds.util import duration

from sdm_dds_pubsub._discovery import discover_datatype
from sdm_dds_pubsub.exceptions import (
    ConfigurationError,
    ConnectionError,
    DiscoveryError,
    DiscoveryTimeoutError,
    SubscribeError,
    CallbackError,
    ClosedError,
)

# DDSException 래핑용
try:
    from cyclonedds.core import DDSException
except ImportError:
    DDSException = Exception  # cyclonedds 미설치 시 fallback

# QoS 타입 (cyclonedds.qos.Qos)
QosType = Any


T = TypeVar("T")


class Subscriber:
    """
    DDS 토픽 구독자.

    datatype을 명시하면 정적 타입, 생략하면 동적 discovery(Publisher 선행 필요).
    on_message를 넘기면 콜백 모드, 아니면 read()로 폴링.
    """

    def __init__(
        self,
        topic_name: str,
        datatype: Optional[Type[T]] = None,
        on_message: Optional[Callable[[T], None]] = None,
        on_error: Optional[Callable[[Exception, Any], None]] = None,
        participant: Optional[DomainParticipant] = None,
        domain_id: int = 0,
        discovery_timeout: float = 10.0,
        qos: Optional[QosType] = None,
    ) -> None:
        """
        Args:
            topic_name: DDS 토픽 이름
            datatype: 메시지 타입. None이면 동적 discovery
            on_message: 콜백 함수 (인자: 수신 메시지). None이면 read() 사용
            on_error: on_message 내부 예외 시 호출 (exc, msg). None이면 예외 무시
            participant: 기존 DomainParticipant. None이면 domain_id로 생성
            domain_id: participant가 None일 때 사용할 DDS 도메인 ID (기본 0)
            discovery_timeout: datatype=None일 때 discovery 대기 시간(초)
            qos: 커스텀 QoS (cyclonedds.qos.Qos). topic(), datareader() 사용
        """
        # 인자 검증
        if not topic_name or not isinstance(topic_name, str):
            raise ConfigurationError("topic_name은 비어있지 않은 문자열이어야 합니다.")
        if discovery_timeout <= 0:
            raise ConfigurationError(
                f"discovery_timeout은 양수여야 합니다. (현재: {discovery_timeout})"
            )
        if participant is None and domain_id < 0:
            raise ConfigurationError(
                f"domain_id는 0 이상이어야 합니다. (현재: {domain_id})"
            )

        self._topic_name = topic_name
        self._on_error = on_error

        try:
            if participant is not None:
                self._participant = participant
            else:
                self._participant = DomainParticipant(domain_id=domain_id)
        except DDSException as e:
            raise ConnectionError(
                f"DDS 도메인 참가자 생성 실패 (domain_id={domain_id}): {e}"
            ) from e

        if datatype is not None:
            resolved_type: Union[Type[T], Any] = datatype
        else:
            try:
                resolved_type = discover_datatype(
                    self._participant, topic_name, timeout_sec=discovery_timeout
                )
            except DDSException as e:
                raise DiscoveryError(
                    f"타입 discovery 중 오류 ('{topic_name}'): {e}"
                ) from e
            if resolved_type is None:
                raise DiscoveryTimeoutError(topic_name, discovery_timeout)

        topic_qos = qos.topic() if qos is not None and hasattr(qos, "topic") else None
        try:
            self._topic = Topic(
                self._participant, topic_name, resolved_type, qos=topic_qos
            )
        except DDSException as e:
            raise ConnectionError(
                f"토픽 생성 실패 ('{topic_name}'): {e}"
            ) from e

        reader_qos = (
            qos.datareader()
            if qos is not None and hasattr(qos, "datareader")
            else None
        )

        if on_message is not None:

            def _on_data_available(reader: DataReader) -> None:
                for sample in reader.take(N=64):
                    try:
                        on_message(sample)
                    except Exception as exc:
                        if on_error is not None:
                            try:
                                on_error(exc, sample)
                            except Exception:
                                pass  # on_error 내부 예외는 로깅 등으로 처리
                        # on_error 없으면 예외 무시 (기본)

            listener = Listener(on_data_available=_on_data_available)
            try:
                self._reader = DataReader(
                    self._participant, self._topic,
                    qos=reader_qos, listener=listener
                )
            except DDSException as e:
                raise ConnectionError(
                    f"DataReader 생성 실패 ('{topic_name}'): {e}"
                ) from e
            self._on_message = on_message
            self._read_cond = None
            self._waitset = None
        else:
            try:
                self._reader = DataReader(
                    self._participant, self._topic, qos=reader_qos
                )
            except DDSException as e:
                raise ConnectionError(
                    f"DataReader 생성 실패 ('{topic_name}'): {e}"
                ) from e
            self._read_cond = ReadCondition(
                self._reader,
                SampleState.NotRead | ViewState.Any | InstanceState.Alive,
            )
            self._waitset = WaitSet(self._participant)
            self._waitset.attach(self._read_cond)
            self._on_message = None

        self._closed = False

    def close(self) -> None:
        """
        리소스를 정리합니다. close() 후 read() 호출 시 ClosedError 발생.
        """
        if self._closed:
            return
        self._closed = True
        self._reader = None  # type: ignore
        self._topic = None  # type: ignore
        self._participant = None  # type: ignore
        self._read_cond = None  # type: ignore
        self._waitset = None  # type: ignore

    def __enter__(self) -> Subscriber[T]:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def read(
        self,
        timeout_sec: Optional[float] = None,
        max_samples: int = 64,
    ) -> Iterator[T]:
        """
        수신된 메시지를 순회합니다. (폴링 모드)

        on_message 콜백을 사용한 경우 read()를 호출하지 마세요.

        Args:
            timeout_sec: 다음 샘플 대기 시간(초). None이면 무한 대기
            max_samples: 한 번에 가져올 최대 샘플 수

        Yields:
            수신된 메시지
        """
        if self._closed:
            raise ClosedError("Subscriber가 이미 close()되었습니다.")

        if self._on_message is not None:
            raise SubscribeError(
                "콜백 모드(on_message)에서는 read()를 사용할 수 없습니다."
            )

        if timeout_sec is not None and timeout_sec < 0:
            raise ConfigurationError(
                f"timeout_sec는 0 이상이어야 합니다. (현재: {timeout_sec})"
            )
        if max_samples <= 0:
            raise ConfigurationError(
                f"max_samples는 1 이상이어야 합니다. (현재: {max_samples})"
            )

        wait_duration = (
            duration(seconds=timeout_sec)
            if timeout_sec is not None
            else duration(seconds=2**31 - 1)  # 실질적 무한
        )

        try:
            while True:
                if self._waitset.wait(wait_duration) == 0:
                    continue
                for sample in self._reader.take(
                    N=max_samples, condition=self._read_cond
                ):
                    yield sample
        except DDSException as e:
            raise SubscribeError(f"구독 읽기 중 오류: {e}") from e
