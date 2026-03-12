#!/usr/bin/env python3
"""
HelloWorld 토픽 발행 예제 (PubSub SDK).

실행: source activate_env.sh && python src/publisher.py
실행 전 Subscriber를 먼저 띄우는 것을 권장합니다.
"""

import time

from sdm_dds_pubsub import Publisher
from hello_msgs import HelloWorld
from std_msgs.msg import Header, Time


def main() -> None:
    """Publisher 메인 루프."""
    print("[Publisher] HelloWorld 발행 시작. Ctrl+C로 종료")
    count = 0
    with Publisher("HelloWorld", HelloWorld) as pub:
        try:
            while True:
                now = time.time()
                sec = int(now)
                nanosec = int((now - sec) * 1_000_000_000)
                header = Header(stamp=Time(sec=sec, nanosec=nanosec), frame_id="")
                msg = HelloWorld(header=header, msg="Hello from DDS!", count=count)
                pub.write(msg)
                print(f"[Publisher] 발행: count={count}, ts={sec}.{nanosec:09d}")
                count += 1
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\n[Publisher] 종료")


if __name__ == "__main__":
    main()
