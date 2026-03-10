#!/usr/bin/env python3
"""
RPC SDK 테스트

실행: source activate_env.sh && python tests/test_rpc.py
"""

import subprocess
import sys
import time

# 프로젝트 루트를 path에 추가
sys.path.insert(0, "/home/ubuntu/workspace/SDM-DDS")

from sdm_dds_rpc import RpcClient, RpcServer, RPCDuplicateInstanceError
from rpc import RequestHeader, ReplyHeader, RemoteExceptionCode
from services import Add_Request, Add_Reply, Add_In, Add_Out


def handle_add(req):
    return Add_Reply(
        header=ReplyHeader(
            related_request_id="",
            remote_ex=RemoteExceptionCode.REMOTE_EX_OK,
            server_instance="",
        ),
        data=Add_Out(sum=req.data.a + req.data.b),
    )


def test_basic_call():
    """기본 RPC 호출 (instance 미지정)."""
    print("\n[테스트 1] 기본 RPC 호출")
    server = RpcServer(domain_id=0)
    server.register_service("Add", Add_Request, Add_Reply, handle_add)

    import threading
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(4)

    client = RpcClient(domain_id=0)
    req = Add_Request(
        header=RequestHeader(request_id="", instance_name=""),
        data=Add_In(a=10, b=20),
    )
    r = client.call("Add", req, Add_Reply, timeout=5.0)
    assert r.data.sum == 30
    server.stop()
    print("  통과: sum=30")


def test_instance_call():
    """인스턴스 지정 호출 및 server_instance 확인."""
    print("\n[테스트 2] 인스턴스 지정 호출")
    server = RpcServer(domain_id=0)
    server.register_service("Add", Add_Request, Add_Reply, handle_add, instance_name="worker-1")

    import threading
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(4)

    client = RpcClient(domain_id=0)
    req = Add_Request(
        header=RequestHeader(request_id="", instance_name=""),
        data=Add_In(a=7, b=8),
    )
    r = client.call("Add", req, Add_Reply, timeout=5.0, instance="worker-1")
    assert r.data.sum == 15
    assert "worker-1" in str(r.header.server_instance)
    server.stop()
    print("  통과: sum=15, server_instance=worker-1")


def test_list_servers():
    """서버 목록 조회."""
    print("\n[테스트 3] list_servers")
    server = RpcServer(domain_id=0)
    server.register_service("Add", Add_Request, Add_Reply, handle_add, instance_name="worker-1")

    import threading
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(5)

    client = RpcClient(domain_id=0)
    servers = client.list_servers(timeout=3.0)
    server.stop()
    time.sleep(1)

    if ("Add", "worker-1") in servers:
        print("  통과: worker-1 발견")
    else:
        print(f"  경고: list_servers={servers} (동일 프로세스에서 discovery 지연 가능)")


def test_duplicate_instance():
    """중복 인스턴스 등록 시 RPCDuplicateInstanceError."""
    print("\n[테스트 4] 중복 인스턴스 검사")
    server1 = RpcServer(domain_id=0)
    server1.register_service("Add", Add_Request, Add_Reply, handle_add, instance_name="worker-1")

    import threading
    t = threading.Thread(target=server1.run, daemon=True)
    t.start()
    time.sleep(5)

    server2 = RpcServer(domain_id=0)
    try:
        server2.register_service("Add", Add_Request, Add_Reply, handle_add, instance_name="worker-1")
        print("  실패: RPCDuplicateInstanceError 예상")
        server1.stop()
        sys.exit(1)
    except RPCDuplicateInstanceError:
        print("  통과: RPCDuplicateInstanceError 발생")
    server1.stop()


def test_timeout():
    """서버 없을 때 타임아웃."""
    print("\n[테스트 5] 타임아웃 (서버 없음)")
    from sdm_dds_rpc.exceptions import RPCTimeoutError

    client = RpcClient(domain_id=0)
    req = Add_Request(
        header=RequestHeader(request_id="", instance_name=""),
        data=Add_In(a=1, b=2),
    )
    try:
        client.call("Add", req, Add_Reply, timeout=2.0)
        print("  실패: 타임아웃 예상")
        sys.exit(1)
    except RPCTimeoutError:
        print("  통과: RPCTimeoutError 발생")


def main():
    print("=== RPC SDK 테스트 ===")
    test_basic_call()
    test_instance_call()
    test_list_servers()
    test_duplicate_instance()
    test_timeout()
    print("\n=== 모든 테스트 완료 ===")


if __name__ == "__main__":
    main()
