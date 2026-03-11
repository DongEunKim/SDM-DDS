#!/usr/bin/env python3
"""
PubSub SDK를 사용한 발행 예제.

실행: source activate_env.sh && python src/pubsub_publisher_example.py
"""

import sys
import time

from sdm_dds_pubsub import Publisher
from hello_msgs import HelloWorld
from std_msgs.msg import Header, Time


def main() -> None:
    """Publisher 메인 루프."""
    publisher = Publisher("HelloWorld", HelloWorld)

    print("[PubSub SDK] HelloWorld 발행 시작. Ctrl+C로 종료")
    count = 0
    try:
        while True:
            now = time.time()
            sec = int(now)
            nanosec = int((now - sec) * 1_000_000_000)
            header = Header(stamp=Time(sec=sec, nanosec=nanosec), frame_id="")
            msg = HelloWorld(header=header, msg="Hello from PubSub SDK!", count=count)
            publisher.write(msg)
            print(f"[PubSub SDK] 발행: count={count}, ts={sec}.{nanosec:09d}")
            count += 1
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[PubSub SDK] 종료")


if __name__ == "__main__":
    main()
