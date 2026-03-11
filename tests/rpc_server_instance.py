#!/usr/bin/env python3
"""인스턴스 지정 RPC 서버 (서브프로세스용)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sdm_dds_rpc import RpcServer
from rpc import ReplyHeader, RemoteExceptionCode
from services import Add


def handle_add(req):
    return Add.Reply(
        header=ReplyHeader(
            related_request_id="",
            remote_ex=RemoteExceptionCode.REMOTE_EX_OK,
            server_instance="",
        ),
        data=Add.Out(sum=req.data.a + req.data.b),
    )


if __name__ == "__main__":
    server = RpcServer(domain_id=0)
    server.register_service("Add", Add.Request, Add.Reply, handle_add, instance_name="worker-dup")
    try:
        server.run()
    except KeyboardInterrupt:
        server.stop()
