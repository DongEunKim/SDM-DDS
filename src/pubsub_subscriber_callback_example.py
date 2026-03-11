#!/usr/bin/env python3
"""
PubSub SDK를 사용한 구독 예제 (콜백 모드).

실행: source activate_env.sh && python src/pubsub_subscriber_callback_example.py
Publisher를 먼저 실행해야 합니다.
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
            f"[PubSub SDK] 콜백 수신: msg='{msg.msg}', count={msg.count}, "
            f"전송지연={delay_ms:.2f}ms"
        )


def main() -> None:
    """Subscriber 메인 (콜백)."""
    try:
        subscriber = Subscriber(
            "HelloWorld",
            datatype=HelloWorld,
            on_message=on_message,
        )
    except DiscoveryTimeoutError as e:
        print(f"[PubSub SDK] 오류: {e}")
        sys.exit(1)

    print("[PubSub SDK] HelloWorld 구독 중 (콜백). Ctrl+C로 종료")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[PubSub SDK] 종료")


if __name__ == "__main__":
    main()
