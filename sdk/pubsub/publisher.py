"""
Publisher - DDS 토픽 발행용 간편 래퍼

사용 예:
    publisher = Publisher("HelloWorld", HelloWorld)
    publisher.write(msg)

    with Publisher("HelloWorld", HelloWorld) as pub:
        pub.write(msg)
"""

from __future__ import annotations

from typing import Any, Optional, Type, TypeVar

from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import DataWriter

from sdm_dds_pubsub.exceptions import (
    ConfigurationError,
    ConnectionError,
    PublishError,
    ClosedError,
)

try:
    from cyclonedds.core import DDSException
except ImportError:
    DDSException = Exception  # cyclonedds 미설치 시 fallback

# QoS 타입 (cyclonedds.qos.Qos)
QosType = Any


T = TypeVar("T")


class Publisher:
    """
    DDS 토픽 발행자.

    topic_name과 datatype으로 토픽을 생성하고, write()로 메시지를 발행합니다.
    """

    def __init__(
        self,
        topic_name: str,
        datatype: Type[T],
        participant: Optional[DomainParticipant] = None,
        domain_id: int = 0,
        qos: Optional[QosType] = None,
    ) -> None:
        """
        Args:
            topic_name: DDS 토픽 이름
            datatype: 발행할 메시지 타입 (IDL로 생성된 클래스)
            participant: 기존 DomainParticipant. None이면 domain_id로 생성
            domain_id: participant가 None일 때 사용할 DDS 도메인 ID (기본 0)
            qos: 커스텀 QoS (cyclonedds.qos.Qos). topic(), datawriter() 사용
        """
        # 인자 검증
        if not topic_name or not isinstance(topic_name, str):
            raise ConfigurationError(
                "topic_name은 비어있지 않은 문자열이어야 합니다."
            )
        if datatype is None:
            raise ConfigurationError("datatype은 필수입니다.")
        if participant is None and domain_id < 0:
            raise ConfigurationError(
                f"domain_id는 0 이상이어야 합니다. (현재: {domain_id})"
            )

        self._topic_name = topic_name
        self._datatype = datatype
        self._owns_participant = participant is None

        try:
            if participant is not None:
                self._participant = participant
            else:
                self._participant = DomainParticipant(domain_id=domain_id)
        except DDSException as e:
            raise ConnectionError(
                f"DDS 도메인 참가자 생성 실패 (domain_id={domain_id}): {e}"
            ) from e

        topic_qos = qos.topic() if qos is not None and hasattr(qos, "topic") else None
        try:
            self._topic = Topic(
                self._participant, topic_name, datatype, qos=topic_qos
            )
        except DDSException as e:
            raise ConnectionError(
                f"토픽 생성 실패 ('{topic_name}'): {e}"
            ) from e

        writer_qos = (
            qos.datawriter() if qos is not None and hasattr(qos, "datawriter") else None
        )
        try:
            self._writer = DataWriter(
                self._participant, self._topic, qos=writer_qos
            )
        except DDSException as e:
            raise ConnectionError(
                f"DataWriter 생성 실패 ('{topic_name}'): {e}"
            ) from e

        self._closed = False

    def close(self) -> None:
        """
        리소스를 정리합니다. close() 후 write() 호출 시 ClosedError 발생.
        """
        if self._closed:
            return
        self._closed = True
        self._writer = None  # type: ignore
        self._topic = None  # type: ignore
        self._participant = None  # type: ignore

    def __enter__(self) -> "Publisher[T]":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def write(self, msg: T) -> None:
        """
        메시지를 토픽에 발행합니다.

        Args:
            msg: datatype 인스턴스

        Raises:
            ClosedError: close() 호출 후
            ConfigurationError: msg가 None인 경우
            PublishError: 발행 실패 (타입 불일치, 직렬화 오류 등)
        """
        if self._closed:
            raise ClosedError("Publisher가 이미 close()되었습니다.")

        if msg is None:
            raise ConfigurationError("msg는 None일 수 없습니다.")

        if not isinstance(msg, self._datatype):
            raise PublishError(
                f"메시지 타입이 topic datatype({self._datatype})과 일치하지 않습니다. "
                f"수신 타입: {type(msg)}"
            )

        try:
            self._writer.write(msg)
        except DDSException as e:
            raise PublishError(f"메시지 발행 실패: {e}") from e
