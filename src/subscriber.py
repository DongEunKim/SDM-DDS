#!/usr/bin/env python3
"""
HelloWorld 토픽을 동적 타입으로 구독하는 DDS Subscriber 예제.

XTypes 기반 타입 발견으로 런타임에 타입을 획득하여 구독합니다.
Publisher를 먼저 실행한 후 본 Subscriber를 실행합니다.

실행: source activate_env.sh && python src/subscriber.py
"""

import sys
import time

from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.sub import DataReader
from cyclonedds.builtin import BuiltinTopicDcpsPublication, BuiltinTopicDcpsSubscription
from cyclonedds.builtin import BuiltinDataReader
from cyclonedds.dynamic import get_types_for_typeid
from cyclonedds.core import ReadCondition, ViewState, InstanceState, SampleState, WaitSet
from cyclonedds.util import duration

DOMAIN_ID = 0
TOPIC_NAME = "HelloWorld"
DISCOVERY_TIMEOUT_SEC = 10


def discover_datatype(participant: DomainParticipant, topic_name: str):
    """토픽에 대한 타입을 DCPSPublication/DCPSSubscription에서 발견합니다."""
    rd_pub = BuiltinDataReader(participant, BuiltinTopicDcpsPublication)
    rc_pub = ReadCondition(
        rd_pub, SampleState.NotRead | ViewState.Any | InstanceState.Alive
    )
    rd_sub = BuiltinDataReader(participant, BuiltinTopicDcpsSubscription)
    rc_sub = ReadCondition(
        rd_sub, SampleState.NotRead | ViewState.Any | InstanceState.Alive
    )

    for _ in range(int(DISCOVERY_TIMEOUT_SEC * 250)):  # 4ms 간격 폴링
        for pub in rd_pub.take(N=20, condition=rc_pub):
            if pub.topic_name == topic_name and pub.type_id is not None:
                datatype, _ = get_types_for_typeid(
                    participant, pub.type_id, duration(seconds=5)
                )
                return datatype
        for sub in rd_sub.take(N=20, condition=rc_sub):
            if sub.topic_name == topic_name and sub.type_id is not None:
                datatype, _ = get_types_for_typeid(
                    participant, sub.type_id, duration(seconds=5)
                )
                return datatype
        time.sleep(0.004)

    return None


def main() -> None:
    """동적 타입 Subscriber 메인 루프."""
    participant = DomainParticipant(domain_id=DOMAIN_ID)

    print(f"[Subscriber] '{TOPIC_NAME}' 토픽 타입 발견 중... (최대 {DISCOVERY_TIMEOUT_SEC}초)")
    datatype = discover_datatype(participant, TOPIC_NAME)
    if datatype is None:
        print(f"[Subscriber] 오류: '{TOPIC_NAME}' 토픽의 Publisher를 찾지 못했습니다.")
        print("             Publisher를 먼저 실행한 후 다시 시도하세요.")
        sys.exit(1)

    print(f"[Subscriber] 동적 타입 획득: {datatype}")
    topic = Topic(participant, TOPIC_NAME, datatype)
    reader = DataReader(participant, topic)

    read_cond = ReadCondition(
        reader, SampleState.NotRead | ViewState.Any | InstanceState.Alive
    )
    waitset = WaitSet(participant)
    waitset.attach(read_cond)

    print("[Subscriber] HelloWorld 대기 중. Ctrl+C로 종료")
    try:
        while True:
            if waitset.wait(duration(seconds=1)) == 0:
                continue
            for sample in reader.take(N=10, condition=read_cond):
                if hasattr(sample, "msg"):
                    recv_us = int(time.time() * 1_000_000)
                    send_us = sample.header.stamp.sec * 1_000_000 + sample.header.stamp.nanosec // 1000
                    delay_us = recv_us - send_us
                    delay_ms = delay_us / 1_000.0
                    print(
                        f"[Subscriber] 수신: msg='{sample.msg}', count={sample.count}, "
                        f"전송지연={delay_ms:.2f}ms"
                    )
    except KeyboardInterrupt:
        print("\n[Subscriber] 종료")


if __name__ == "__main__":
    main()
