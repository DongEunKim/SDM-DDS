#!/usr/bin/env python3
"""
Calculate RPC 클라이언트 예제.

Calculate 서비스에 요청을 보내 add/sub/mul 연산 결과를 출력합니다.
서버(calculate_server.py)를 먼저 실행한 후 본 클라이언트를 실행합니다.

실행: source activate_env.sh && python src/calculate_client.py [op] [a] [b]
예:   python src/calculate_client.py add 10 20
      python src/calculate_client.py mul 7 8
"""

import sys

from sdm_dds_rpc import RpcClient
from sdm_dds_rpc.exceptions import RPCTimeoutError
from rpc import RequestHeader
from services import Calculate


def main() -> None:
    """RPC 클라이언트 메인."""
    op = sys.argv[1] if len(sys.argv) > 1 else "add"
    try:
        a = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        b = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    except ValueError:
        print("오류: a, b는 정수여야 합니다.")
        sys.exit(1)

    with RpcClient(domain_id=0) as client:
        servers = client.list_servers(service_name="Calculate", timeout=2.0)
        if servers:
            print(f"[Calculate 클라이언트] 등록된 서버: {servers}")
        else:
            print("[Calculate 클라이언트] 등록된 서버 없음 (서버 시작 대기 중)")

        req = Calculate.Request(
            header=RequestHeader(request_id="", instance_name=""),
            data=Calculate.In(op=op, a=a, b=b),
        )

        print(f"[Calculate 클라이언트] 요청: {op} {a} {b}")
        try:
            rep = client.call("Calculate", req, Calculate.Reply, timeout=5.0)
            print(f"[Calculate 클라이언트] 응답: {rep.data.message}")
            print(f"             결과 = {rep.data.result}")
        except RPCTimeoutError as e:
            print(f"[Calculate 클라이언트] 타임아웃: {e}")
            print("             서버(calculate_server.py)가 실행 중인지 확인하세요.")


if __name__ == "__main__":
    main()
