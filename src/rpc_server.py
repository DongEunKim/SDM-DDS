#!/usr/bin/env python3
"""
Add RPC 서버 예제.

Add 서비스를 등록하고 요청을 수신하면 a + b를 계산하여 응답합니다.
클라이언트(rpc_client.py)를 먼저 실행할 필요는 없으며, 서버를 먼저 실행하는 것을 권장합니다.

실행: source activate_env.sh && python src/rpc_server.py
"""

from sdm_dds_rpc import RpcServer
from rpc import ReplyHeader, RemoteExceptionCode
from services import Add_Request, Add_Reply, Add_In, Add_Out


def handle_add(request: Add_Request) -> Add_Reply:
    """Add 요청 처리: a + b 반환."""
    result = request.data.a + request.data.b
    # header는 SDK가 related_request_id 등 자동 설정
    return Add_Reply(
        header=ReplyHeader(
            related_request_id="",
            remote_ex=RemoteExceptionCode.REMOTE_EX_OK,
            server_instance="",
        ),
        data=Add_Out(sum=result),
    )


def main() -> None:
    """RPC 서버 메인."""
    server = RpcServer(domain_id=0)
    server.register_service("Add", Add_Request, Add_Reply, handle_add)

    print("[RPC 서버] Add 서비스 등록됨. 대기 중. Ctrl+C로 종료")
    try:
        server.run()
    except KeyboardInterrupt:
        server.stop()
        print("\n[RPC 서버] 종료")


if __name__ == "__main__":
    main()
