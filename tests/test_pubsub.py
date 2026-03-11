#!/usr/bin/env python3
"""
PubSub SDK 테스트

실행: source activate_env.sh && python tests/test_pubsub.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sdm_dds_pubsub import (
    Publisher,
    Subscriber,
    ConfigurationError,
    DiscoveryTimeoutError,
    PublishError,
    SubscribeError,
    ClosedError,
)
from hello_msgs import HelloWorld
from std_msgs.msg import Header, Time


def _make_hello(msg: str = "test", count: int = 0) -> HelloWorld:
    now = time.time()
    sec = int(now)
    nanosec = int((now - sec) * 1_000_000_000)
    header = Header(stamp=Time(sec=sec, nanosec=nanosec), frame_id="")
    return HelloWorld(header=header, msg=msg, count=count)


def test_publisher_configuration_error():
    """Publisher 인자 검증 오류."""
    print("\n[테스트 1] Publisher ConfigurationError")

    try:
        Publisher("", HelloWorld)
        sys.exit(1)
    except ConfigurationError:
        pass

    try:
        Publisher("topic", None)
        sys.exit(1)
    except ConfigurationError:
        pass

    try:
        Publisher("topic", HelloWorld, domain_id=-1)
        sys.exit(1)
    except ConfigurationError:
        pass

    print("  통과: topic_name 빈문자열, datatype None, domain_id < 0")


def test_publisher_write_errors():
    """Publisher write() 예외."""
    print("\n[테스트 2] Publisher write() 예외")

    pub = Publisher("HelloWorld", HelloWorld)

    try:
        pub.write(None)
        sys.exit(1)
    except ConfigurationError:
        pass

    try:
        pub.write("wrong type")
        sys.exit(1)
    except PublishError:
        pass

    pub.close()
    try:
        pub.write(_make_hello())
        sys.exit(1)
    except ClosedError:
        pass

    print("  통과: write(None), 타입 불일치, close 후 write")


def test_subscriber_configuration_error():
    """Subscriber 인자 검증 오류."""
    print("\n[테스트 3] Subscriber ConfigurationError")

    try:
        Subscriber("", datatype=HelloWorld)
        sys.exit(1)
    except ConfigurationError:
        pass

    try:
        Subscriber("topic", datatype=HelloWorld, discovery_timeout=0)
        sys.exit(1)
    except ConfigurationError:
        pass

    try:
        Subscriber("topic", datatype=HelloWorld, domain_id=-1)
        sys.exit(1)
    except ConfigurationError:
        pass

    print("  통과: topic_name 빈문자열, discovery_timeout<=0, domain_id<0")


def test_subscriber_read_errors():
    """Subscriber read() 예외."""
    print("\n[테스트 4] Subscriber read() 예외")

    # 콜백 모드에서 read()
    sub_cb = Subscriber("HelloWorld", datatype=HelloWorld, on_message=lambda m: None)
    try:
        next(sub_cb.read())
        sys.exit(1)
    except SubscribeError:
        pass

    # read(max_samples=0)
    sub = Subscriber("HelloWorld", datatype=HelloWorld)
    try:
        next(sub.read(max_samples=0))
        sys.exit(1)
    except ConfigurationError:
        pass

    # close 후 read()
    sub.close()
    try:
        next(sub.read())
        sys.exit(1)
    except ClosedError:
        pass

    print("  통과: 콜백 모드 read(), max_samples=0, close 후 read")


def test_close_duplicate():
    """close() 중복 호출."""
    print("\n[테스트 5] close() 중복 호출")

    pub = Publisher("HelloWorld", HelloWorld)
    pub.close()
    pub.close()

    sub = Subscriber("HelloWorld", datatype=HelloWorld)
    sub.close()
    sub.close()

    print("  통과: 중복 close() 예외 없음")


def test_with_statement():
    """with 구문."""
    print("\n[테스트 6] with 구문")

    with Publisher("HelloWorld", HelloWorld) as pub:
        pub.write(_make_hello("with pub", 1))

    with Subscriber("HelloWorld", datatype=HelloWorld) as sub:
        pass

    print("  통과: with Publisher, with Subscriber")


def test_e2e_publish_subscribe():
    """E2E 발행-구독."""
    print("\n[테스트 7] E2E 발행-구독")

    pub = Publisher("HelloWorld", HelloWorld)
    sub = Subscriber("HelloWorld", datatype=HelloWorld)

    pub.write(_make_hello("e2e", 42))

    received = []
    for msg in sub.read(timeout_sec=3):
        received.append(msg)
        if len(received) >= 1:
            break

    assert len(received) >= 1
    assert received[0].msg == "e2e"
    assert received[0].count == 42

    pub.close()
    sub.close()

    print("  통과: write -> read 성공")


def test_on_error_callback():
    """on_error 콜백 호출."""
    print("\n[테스트 8] on_error 콜백")

    errors = []

    def on_msg(msg):
        raise ValueError("의도적 예외")

    def on_err(exc, msg):
        errors.append((exc, msg))

    sub = Subscriber(
        "HelloWorld",
        datatype=HelloWorld,
        on_message=on_msg,
        on_error=on_err,
    )

    # Publisher가 한 번 발행
    pub = Publisher("HelloWorld", HelloWorld)
    pub.write(_make_hello("trigger", 0))
    time.sleep(0.5)

    assert len(errors) >= 1
    assert isinstance(errors[0][0], ValueError)
    assert errors[0][0].args[0] == "의도적 예외"

    pub.close()
    sub.close()

    print("  통과: on_error 호출 확인")


def main():
    print("=== PubSub SDK 테스트 ===")
    test_publisher_configuration_error()
    test_publisher_write_errors()
    test_subscriber_configuration_error()
    test_subscriber_read_errors()
    test_close_duplicate()
    test_with_statement()
    test_e2e_publish_subscribe()
    test_on_error_callback()
    print("\n=== 모든 테스트 완료 ===")


if __name__ == "__main__":
    main()
