#!/usr/bin/env python3
"""
Add RPC 서버 예제.

Add 서비스를 등록하고 요청을 수신하면 a + b를 계산하여 응답합니다.
instance_name으로 서버를 구분하며, 동일 인스턴스명 중복 실행 시 RPCDuplicateInstanceError 발생.

실행: source activate_env.sh && python src/rpc_server.py [인스턴스명]
예:   python src/rpc_server.py add-server-1
"""

import sys

from sdm_dds_rpc import RpcServer, RPCDuplicateInstanceError
from rpc import ReplyHeader, RemoteExceptionCode
from services import Add


def handle_add(request: Add.Request) -> Add.Reply:
    """Add 요청 처리: a + b 반환."""
    result = request.data.a + request.data.b
    return Add.Reply(
        header=ReplyHeader(
            related_request_id="",
            remote_ex=RemoteExceptionCode.REMOTE_EX_OK,
            server_instance="",
        ),
        data=Add.Out(sum=result),
    )


def main() -> None:
    """RPC 서버 메인."""
    instance = sys.argv[1] if len(sys.argv) > 1 else "add-server-1"

    server = RpcServer(domain_id=0)
    try:
        server.register_service(
            "Add", Add.Request, Add.Reply, handle_add, instance_name=instance
        )
    except RPCDuplicateInstanceError as e:
        print(f"[RPC 서버] 오류: {e}")
        print(f"             다른 인스턴스명으로 실행하세요. 예: python src/rpc_server.py add-server-2")
        sys.exit(1)

    print(f"[RPC 서버] Add 서비스 등록됨 (인스턴스: {instance}). 대기 중. Ctrl+C로 종료")
    try:
        server.run()
    except KeyboardInterrupt:
        server.stop()
    finally:
        server.close()
        print("\n[RPC 서버] 종료")


if __name__ == "__main__":
    main()
