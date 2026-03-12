#!/usr/bin/env python3
"""
Calculate RPC 서버 예제.

Calculate 서비스를 등록하고 op(add/sub/mul)에 따라 a, b를 연산하여 응답합니다.

실행: source activate_env.sh && python src/calculate_server.py [인스턴스명]
예:   python src/calculate_server.py calc-server-1
"""

import sys

from sdm_dds_rpc import RpcServer, RPCDuplicateInstanceError
from rpc import ReplyHeader, RemoteExceptionCode
from services import Calculate


def handle_calculate(request: Calculate.Request) -> Calculate.Reply:
    """Calculate 요청 처리: op에 따라 a, b 연산."""
    op = (request.data.op or "").strip().lower()
    a, b = request.data.a, request.data.b

    if op == "add":
        result = a + b
        msg = f"{a} + {b} = {result}"
    elif op == "sub":
        result = a - b
        msg = f"{a} - {b} = {result}"
    elif op == "mul":
        result = a * b
        msg = f"{a} * {b} = {result}"
    else:
        result = 0
        msg = f"알 수 없는 연산: '{op}'"

    return Calculate.Reply(
        header=ReplyHeader(
            related_request_id="",
            remote_ex=RemoteExceptionCode.REMOTE_EX_OK,
            server_instance="",
        ),
        data=Calculate.Out(result=result, message=msg),
    )


def main() -> None:
    """RPC 서버 메인."""
    instance = sys.argv[1] if len(sys.argv) > 1 else "calc-server-1"

    server = RpcServer(domain_id=0)
    try:
        server.register_service(
            "Calculate",
            Calculate.Request,
            Calculate.Reply,
            handle_calculate,
            instance_name=instance,
        )
    except RPCDuplicateInstanceError as e:
        print(f"[Calculate 서버] 오류: {e}")
        sys.exit(1)

    print(f"[Calculate 서버] 서비스 등록됨 (인스턴스: {instance}). 대기 중. Ctrl+C로 종료")
    try:
        server.run()
    except KeyboardInterrupt:
        server.stop()
    finally:
        server.close()
        print("\n[Calculate 서버] 종료")


if __name__ == "__main__":
    main()
