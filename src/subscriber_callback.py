#!/usr/bin/env python3
"""
HelloWorld 토픽을 콜백 방식으로 구독하는 DDS Subscriber 예제.

DataReader Listener의 on_data_available를 사용하여 데이터 수신 시 콜백이 호출됩니다.
Publisher를 먼저 실행한 후 본 Subscriber를 실행합니다.

실행: source activate_env.sh && python src/subscriber_callback.py
"""

import sys
import time

from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.sub import DataReader
from cyclonedds.core import Listener, ViewState, InstanceState, SampleState

from hello_msgs import HelloWorld

DOMAIN_ID = 0
TOPIC_NAME = "HelloWorld"


def on_hello_data(reader) -> None:
    """HelloWorld 데이터 수신 시 호출되는 콜백."""
    for sample in reader.take(N=10):
        if hasattr(sample, "msg"):
            recv_us = int(time.time() * 1_000_000)
            send_us = sample.header.stamp.sec * 1_000_000 + sample.header.stamp.nanosec // 1000
            delay_ms = (recv_us - send_us) / 1_000.0
            print(
                f"[Callback] 수신: msg='{sample.msg}', count={sample.count}, "
                f"전송지연={delay_ms:.2f}ms"
            )


def main() -> None:
    """콜백 기반 Subscriber."""
    participant = DomainParticipant(domain_id=DOMAIN_ID)
    topic = Topic(participant, TOPIC_NAME, HelloWorld)

    listener = Listener(on_data_available=on_hello_data)
    reader = DataReader(participant, topic, listener=listener)

    print("[Subscriber] HelloWorld 콜백 구독 중. Ctrl+C로 종료")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Subscriber] 종료")


if __name__ == "__main__":
    main()
