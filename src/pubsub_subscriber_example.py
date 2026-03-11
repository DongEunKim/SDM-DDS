#!/usr/bin/env python3
"""
PubSub SDK를 사용한 구독 예제 (폴링 모드).

실행: source activate_env.sh && python src/pubsub_subscriber_example.py
Publisher를 먼저 실행하거나, 동적 discovery를 위해 Publisher가 있어야 합니다.
"""

import sys
import time

from sdm_dds_pubsub import Subscriber, DiscoveryTimeoutError
from hello_msgs import HelloWorld


def main() -> None:
    """Subscriber 메인 루프 (폴링)."""
    try:
        # datatype 생략 시 동적 discovery (Publisher 선행 필요)
        subscriber = Subscriber("HelloWorld", datatype=HelloWorld)
    except DiscoveryTimeoutError as e:
        print(f"[PubSub SDK] 오류: {e}")
        sys.exit(1)

    print("[PubSub SDK] HelloWorld 구독 중 (폴링). Ctrl+C로 종료")
    try:
        for sample in subscriber.read():
            if hasattr(sample, "msg"):
                recv_us = int(time.time() * 1_000_000)
                send_us = sample.header.stamp.sec * 1_000_000 + sample.header.stamp.nanosec // 1000
                delay_ms = (recv_us - send_us) / 1_000.0
                print(
                    f"[PubSub SDK] 수신: msg='{sample.msg}', count={sample.count}, "
                    f"전송지연={delay_ms:.2f}ms"
                )
    except KeyboardInterrupt:
        print("\n[PubSub SDK] 종료")


if __name__ == "__main__":
    main()
