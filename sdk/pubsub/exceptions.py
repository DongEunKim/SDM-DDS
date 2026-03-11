"""
PubSub SDK 예외 정의
"""


class PubSubError(Exception):
    """PubSub 관련 기본 예외."""

    pass


class ConfigurationError(PubSubError):
    """설정 또는 인자 오류."""

    pass


class DiscoveryError(PubSubError):
    """Discovery 관련 오류."""

    pass


class DiscoveryTimeoutError(DiscoveryError):
    """동적 타입 discovery 시간 초과."""

    def __init__(self, topic_name: str, timeout_sec: float) -> None:
        self.topic_name = topic_name
        self.timeout_sec = timeout_sec
        super().__init__(
            f"'{topic_name}' 토픽의 Publisher를 {timeout_sec}초 내에 찾지 못했습니다. "
            "Publisher를 먼저 실행한 후 다시 시도하세요."
        )


class ConnectionError(PubSubError):
    """DDS 엔티티 생성 또는 연결 오류."""

    pass


class PublishError(PubSubError):
    """write() 발행 오류."""

    pass


class SubscribeError(PubSubError):
    """read() 또는 구독 관련 오류."""

    pass


class CallbackError(PubSubError):
    """on_message 콜백 내부 예외."""

    pass


class ClosedError(PubSubError):
    """이미 close()된 엔티티에 대한 작업 시도."""

    pass
