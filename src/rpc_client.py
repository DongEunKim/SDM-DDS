#!/usr/bin/env python3
"""
Add RPC 클라이언트 예제.

Add 서비스에 요청을 보내고 응답을 출력합니다.
서버(rpc_server.py)를 먼저 실행한 후 본 클라이언트를 실행합니다.

실행: source activate_env.sh && python src/rpc_client.py
"""

from sdm_dds_rpc import RpcClient
from sdm_dds_rpc.exceptions import RPCTimeoutError
from rpc import RequestHeader
from services import Add_Request, Add_Reply, Add_In


def main() -> None:
    """RPC 클라이언트 메인."""
    client = RpcClient(domain_id=0)

    # request_id는 SDK가 자동 설정
    request = Add_Request(
        header=RequestHeader(request_id="", instance_name=""),
        data=Add_In(a=10, b=20),
    )

    print("[RPC 클라이언트] Add 서비스 호출: 10 + 20")
    try:
        response = client.call("Add", request, Add_Reply, timeout=5.0)
        svc_inst = getattr(
            response.header, "server_instance", ""
        )
        print(
            f"[RPC 클라이언트] 응답: sum = {response.data.sum}"
            + (f" (서버: {svc_inst})" if svc_inst else "")
        )
    except RPCTimeoutError as e:
        print(f"[RPC 클라이언트] 타임아웃: {e}")
        print("             서버(rpc_server.py)가 실행 중인지 확인하세요.")


if __name__ == "__main__":
    main()
