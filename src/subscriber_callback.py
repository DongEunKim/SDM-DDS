#!/usr/bin/env python3
"""
HelloWorld 토픽 콜백 구독 예제 (PubSub SDK).

Publisher를 먼저 실행한 후 본 Subscriber를 실행합니다.

실행: source activate_env.sh && python src/subscriber_callback.py
"""

import sys
import time

from sdm_dds_pubsub import Subscriber, DiscoveryTimeoutError
from hello_msgs import HelloWorld


def on_message(msg) -> None:
    """수신 메시지 콜백."""
    if hasattr(msg, "msg"):
        recv_us = int(time.time() * 1_000_000)
        send_us = msg.header.stamp.sec * 1_000_000 + msg.header.stamp.nanosec // 1000
        delay_ms = (recv_us - send_us) / 1_000.0
        print(
            f"[Callback] 수신: msg='{msg.msg}', count={msg.count}, "
            f"전송지연={delay_ms:.2f}ms"
        )


def main() -> None:
    """콜백 기반 Subscriber."""
    try:
        subscriber = Subscriber(
            "HelloWorld",
            datatype=HelloWorld,
            on_message=on_message,
        )
    except DiscoveryTimeoutError as e:
        print(f"[Subscriber] 오류: {e}")
        sys.exit(1)

    print("[Subscriber] HelloWorld 콜백 구독 중. Ctrl+C로 종료")
    try:
        with subscriber:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Subscriber] 종료")


if __name__ == "__main__":
    main()
