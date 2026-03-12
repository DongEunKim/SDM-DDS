#!/usr/bin/env python3
"""
HelloWorld 토픽 구독 예제 (PubSub SDK, 동적 타입).

Publisher를 먼저 실행한 후 본 Subscriber를 실행합니다.
datatype 생략 시 동적 discovery로 타입을 획득합니다.

실행: source activate_env.sh && python src/subscriber.py
"""

import sys
import time

from sdm_dds_pubsub import Subscriber, DiscoveryTimeoutError


def main() -> None:
    """Subscriber 메인 루프 (폴링, 동적 discovery)."""
    try:
        # datatype 생략 시 동적 discovery (Publisher 선행 필요)
        subscriber = Subscriber("HelloWorld")
    except DiscoveryTimeoutError as e:
        print(f"[Subscriber] 오류: {e}")
        sys.exit(1)

    print("[Subscriber] HelloWorld 구독 중. Ctrl+C로 종료")
    try:
        with subscriber:
            for sample in subscriber.read():
                if hasattr(sample, "msg"):
                    recv_us = int(time.time() * 1_000_000)
                    send_us = sample.header.stamp.sec * 1_000_000 + sample.header.stamp.nanosec // 1000
                    delay_ms = (recv_us - send_us) / 1_000.0
                    print(
                        f"[Subscriber] 수신: msg='{sample.msg}', count={sample.count}, "
                        f"전송지연={delay_ms:.2f}ms"
                    )
    except KeyboardInterrupt:
        print("\n[Subscriber] 종료")


if __name__ == "__main__":
    main()
