#!/usr/bin/env python3
"""
Add RPC 클라이언트 예제.

Add 서비스에 요청을 보내고 응답을 출력합니다.
서버(rpc_server.py)를 먼저 실행한 후 본 클라이언트를 실행합니다.
list_servers()로 등록된 서버를 조회하고, instance로 특정 서버를 지정할 수 있습니다.

실행: source activate_env.sh && python src/rpc_client.py [인스턴스명]
예:   python src/rpc_client.py              # 아무 서버나 응답
      python src/rpc_client.py add-server-1 # 특정 서버 지정
"""

import sys

from sdm_dds_rpc import RpcClient
from sdm_dds_rpc.exceptions import RPCTimeoutError
from rpc import RequestHeader
from services import Add


def main() -> None:
    """RPC 클라이언트 메인."""
    instance = sys.argv[1] if len(sys.argv) > 1 else None

    with RpcClient(domain_id=0) as client:
        servers = client.list_servers(service_name="Add", timeout=2.0)
        if servers:
            print(f"[RPC 클라이언트] 등록된 Add 서버: {servers}")
        else:
            print("[RPC 클라이언트] 등록된 Add 서버 없음 (서버 시작 대기 중)")

        request = Add.Request(
            header=RequestHeader(request_id="", instance_name=""),
            data=Add.In(a=10, b=20),
        )

        target = f" (대상: {instance})" if instance else ""
        print(f"[RPC 클라이언트] Add 서비스 호출: 10 + 20{target}")
        try:
            response = client.call(
                "Add", request, Add.Reply, timeout=5.0, instance=instance
            )
            svc_inst = str(getattr(response.header, "server_instance", "") or "").strip()
            print(f"[RPC 클라이언트] 응답: sum = {response.data.sum}  (응답 서버: {svc_inst or '미지정'})")
        except RPCTimeoutError as e:
            print(f"[RPC 클라이언트] 타임아웃: {e}")
            print("             서버(rpc_server.py)가 실행 중인지 확인하세요.")


if __name__ == "__main__":
    main()
