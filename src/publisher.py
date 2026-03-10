#!/usr/bin/env python3
"""
HelloWorld 토픽을 발행하는 DDS Publisher 예제.

실행: source activate_env.sh && python src/publisher.py
실행 전 Subscriber를 먼저 띄우는 것을 권장합니다.
"""

import sys
import time

# hello_msgs, std_msgs: pip install -e ./idls 로 설치
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import DataWriter
from hello_msgs import HelloWorld
from std_msgs.msg import Header, Time

DOMAIN_ID = 0
TOPIC_NAME = "HelloWorld"


def main() -> None:
    """Publisher 메인 루프."""
    participant = DomainParticipant(domain_id=DOMAIN_ID)
    topic = Topic(participant, TOPIC_NAME, HelloWorld)
    writer = DataWriter(participant, topic)

    print("[Publisher] HelloWorld 발행 시작. Ctrl+C로 종료")
    count = 0
    try:
        while True:
            now = time.time()
            sec = int(now)
            nanosec = int((now - sec) * 1_000_000_000)
            header = Header(stamp=Time(sec=sec, nanosec=nanosec), frame_id="")
            msg = HelloWorld(header=header, msg="Hello from DDS!", count=count)
            writer.write(msg)
            print(f"[Publisher] 발행: count={count}, ts={sec}.{nanosec:09d}")
            count += 1
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[Publisher] 종료")


if __name__ == "__main__":
    main()
