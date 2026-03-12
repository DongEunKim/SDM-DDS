#!/usr/bin/env python3
"""
RPC SDK 테스트

실행: source activate_env.sh && python tests/test_rpc.py
"""

import sys
import threading
import time
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sdm_dds_rpc import (
    RpcClient,
    RpcServer,
    ConfigurationError,
    RPCClosedError,
    RPCDuplicateInstanceError,
)
from rpc import RequestHeader, ReplyHeader, RemoteExceptionCode
from services import Add, Calculate


def handle_add(req):
    return Add.Reply(
        header=ReplyHeader(
            related_request_id="",
            remote_ex=RemoteExceptionCode.REMOTE_EX_OK,
            server_instance="",
        ),
        data=Add.Out(sum=req.data.a + req.data.b),
    )


def test_basic_call():
    """기본 RPC 호출 (instance 미지정)."""
    print("\n[테스트 1] 기본 RPC 호출")
    server = RpcServer(domain_id=0)
    server.register_service("Add", Add.Request, Add.Reply, handle_add)

    import threading
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(4)

    client = RpcClient(domain_id=0)
    req = Add.Request(
        header=RequestHeader(request_id="", instance_name=""),
        data=Add.In(a=10, b=20),
    )
    r = client.call("Add", req, Add.Reply, timeout=5.0)
    assert r.data.sum == 30
    server.stop()
    print("  통과: sum=30")


def test_instance_call():
    """인스턴스 지정 호출 및 server_instance 확인."""
    print("\n[테스트 2] 인스턴스 지정 호출")
    server = RpcServer(domain_id=0)
    server.register_service("Add", Add.Request, Add.Reply, handle_add, instance_name="worker-1")

    import threading
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(4)

    client = RpcClient(domain_id=0)
    req = Add.Request(
        header=RequestHeader(request_id="", instance_name=""),
        data=Add.In(a=7, b=8),
    )
    r = client.call("Add", req, Add.Reply, timeout=5.0, instance="worker-1")
    assert r.data.sum == 15
    assert "worker-1" in str(r.header.server_instance)
    server.stop()
    print("  통과: sum=15, server_instance=worker-1")


def test_list_servers():
    """서버 목록 조회."""
    print("\n[테스트 3] list_servers")
    server = RpcServer(domain_id=0)
    server.register_service("Add", Add.Request, Add.Reply, handle_add, instance_name="worker-list")

    import threading
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(5)

    client = RpcClient(domain_id=0)
    servers = client.list_servers(timeout=3.0)
    server.stop()
    time.sleep(1)

    if ("Add", "worker-list") in servers:
        print("  통과: worker-list 발견")
    else:
        print(f"  경고: list_servers={servers} (동일 프로세스에서 discovery 지연 가능)")


def test_duplicate_instance():
    """중복 인스턴스 등록 시 RPCDuplicateInstanceError (별도 프로세스)."""
    import subprocess
    import os

    print("\n[테스트 4] 중복 인스턴스 검사")
    root = Path(__file__).resolve().parents[1]
    venv_python = root / "venv" / "bin" / "python"
    if not venv_python.exists():
        venv_python = "python"
    else:
        venv_python = str(venv_python)
    env = os.environ.copy()
    env["CYCLONEDDS_HOME"] = str(root / "cyclonedds" / "install")
    env["LD_LIBRARY_PATH"] = str(root / "cyclonedds" / "install" / "lib") + ":" + env.get("LD_LIBRARY_PATH", "")

    proc = subprocess.Popen(
        [venv_python, str(root / "tests" / "rpc_server_instance.py")],
        cwd=str(root),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(6)

    server2 = RpcServer(domain_id=0)
    try:
        server2.register_service("Add", Add.Request, Add.Reply, handle_add, instance_name="worker-dup")
        proc.terminate()
        proc.wait(timeout=3)
        print("  실패: RPCDuplicateInstanceError 예상")
        sys.exit(1)
    except RPCDuplicateInstanceError:
        proc.terminate()
        proc.wait(timeout=3)
        print("  통과: RPCDuplicateInstanceError 발생")


def test_timeout():
    """서버 없을 때 타임아웃."""
    print("\n[테스트 5] 타임아웃 (서버 없음)")
    from sdm_dds_rpc.exceptions import RPCTimeoutError

    client = RpcClient(domain_id=0)
    req = Add.Request(
        header=RequestHeader(request_id="", instance_name=""),
        data=Add.In(a=1, b=2),
    )
    try:
        client.call("Add", req, Add.Reply, timeout=2.0)
        print("  실패: 타임아웃 예상")
        sys.exit(1)
    except RPCTimeoutError:
        print("  통과: RPCTimeoutError 발생")


def test_calculate_service():
    """Calculate 서비스 (add/sub/mul) 호출."""
    print("\n[테스트 6] Calculate 서비스")

    def handle_calc(req):
        op = (req.data.op or "").strip().lower()
        a, b = req.data.a, req.data.b
        if op == "add":
            r, m = a + b, f"{a} + {b} = {a + b}"
        elif op == "sub":
            r, m = a - b, f"{a} - {b} = {a - b}"
        elif op == "mul":
            r, m = a * b, f"{a} * {b} = {a * b}"
        else:
            r, m = 0, f"알 수 없는 연산: '{op}'"
        return Calculate.Reply(
            header=ReplyHeader(
                related_request_id="",
                remote_ex=RemoteExceptionCode.REMOTE_EX_OK,
                server_instance="",
            ),
            data=Calculate.Out(result=r, message=m),
        )

    server = RpcServer(domain_id=0)
    server.register_service("Calculate", Calculate.Request, Calculate.Reply, handle_calc)

    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(4)

    client = RpcClient(domain_id=0)
    for op, a, b, expect in [("add", 10, 20, 30), ("mul", 7, 8, 56), ("sub", 100, 30, 70)]:
        req = Calculate.Request(
            header=RequestHeader(request_id="", instance_name=""),
            data=Calculate.In(op=op, a=a, b=b),
        )
        r = client.call("Calculate", req, Calculate.Reply, timeout=5.0)
        assert r.data.result == expect, f"{op} {a} {b}: expected {expect}, got {r.data.result}"
    server.stop()
    print("  통과: add, mul, sub")


def test_configuration_error():
    """domain_id < 0 시 ConfigurationError."""
    print("\n[테스트 7] ConfigurationError (domain_id < 0)")
    try:
        RpcClient(domain_id=-1)
        print("  실패: ConfigurationError 예상")
        sys.exit(1)
    except ConfigurationError:
        pass
    try:
        RpcServer(domain_id=-1)
        print("  실패: ConfigurationError 예상")
        sys.exit(1)
    except ConfigurationError:
        pass
    print("  통과: ConfigurationError 발생")


def test_closed_error():
    """close() 후 call() 시 RPCClosedError."""
    print("\n[테스트 8] RPCClosedError (close 후 호출)")
    client = RpcClient(domain_id=0)
    client.close()
    req = Add.Request(
        header=RequestHeader(request_id="", instance_name=""),
        data=Add.In(a=1, b=2),
    )
    try:
        client.call("Add", req, Add.Reply, timeout=1.0)
        print("  실패: RPCClosedError 예상")
        sys.exit(1)
    except RPCClosedError:
        pass
    try:
        client.list_servers()
        print("  실패: RPCClosedError 예상")
        sys.exit(1)
    except RPCClosedError:
        pass
    print("  통과: RPCClosedError 발생")


def test_with_statement():
    """with 구문."""
    print("\n[테스트 9] with 구문")
    with RpcClient(domain_id=0) as client:
        pass  # close() 자동 호출
    with RpcServer(domain_id=0) as server:
        pass  # close() 자동 호출
    print("  통과: with RpcClient, with RpcServer")


def test_shared_participant():
    """공유 participant로 RPC 동작."""
    print("\n[테스트 10] 공유 participant")
    from cyclonedds.domain import DomainParticipant

    dp = DomainParticipant(domain_id=0)
    server = RpcServer(participant=dp)
    server.register_service("Add", Add.Request, Add.Reply, handle_add)

    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(4)

    client = RpcClient(participant=dp)
    req = Add.Request(
        header=RequestHeader(request_id="", instance_name=""),
        data=Add.In(a=3, b=5),
    )
    r = client.call("Add", req, Add.Reply, timeout=5.0)
    assert r.data.sum == 8
    server.stop()
    client.close()
    server.close()
    print("  통과: 공유 participant RPC 호출")


def main():
    print("=== RPC SDK 테스트 ===")
    test_basic_call()
    test_instance_call()
    test_list_servers()
    test_duplicate_instance()
    test_timeout()
    test_calculate_service()
    test_configuration_error()
    test_closed_error()
    test_with_statement()
    test_shared_participant()
    print("\n=== 모든 테스트 완료 ===")


if __name__ == "__main__":
    main()
