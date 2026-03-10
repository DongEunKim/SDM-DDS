"""
RPC SDK 예외 정의
"""


class RPCError(Exception):
    """RPC 관련 기본 예외."""

    pass


class RPCTimeoutError(RPCError):
    """지정된 시간 내에 Reply를 수신하지 못한 경우."""

    pass


class RPCConnectionError(RPCError):
    """서버/토픽 발견 실패 등의 연결 오류."""

    pass


class RPCDuplicateInstanceError(RPCError):
    """같은 서비스에 중복된 인스턴스명으로 등록 시도한 경우."""

    pass


class RPCRemoteError(RPCError):
    """서버에서 반환한 원격 예외 (ReplyHeader.remote_ex != REMOTE_EX_OK)."""

    def __init__(self, message: str, remote_ex_code: int):
        super().__init__(message)
        self.remote_ex_code = remote_ex_code
