# PubSub SDK 사양

DDS 토픽 발행/구독을 간소화한 `sdm_dds_pubsub` SDK 사양입니다.

---

## 1. 개요

| 클래스 | 메서드 | 용도 |
|--------|--------|------|
| **Publisher** | `write(msg)` | 토픽 발행 |
| **Subscriber** | `read()` | 토픽 구독 (폴링) |
| **Subscriber** | `on_message=` | 토픽 구독 (콜백) |

---

## 2. Publisher

```python
from sdm_dds_pubsub import Publisher
from hello_msgs import HelloWorld

publisher = Publisher("HelloWorld", HelloWorld)
publisher.write(msg)
publisher.close()  # 리소스 정리

# with 구문
with Publisher("HelloWorld", HelloWorld) as pub:
    pub.write(msg)
```

### 생성자

| 인자 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| topic_name | str | - | DDS 토픽 이름 |
| datatype | Type | - | 발행할 메시지 타입 |
| domain_id | int | 0 | DDS 도메인 ID |

---

## 3. Subscriber

### 3.1 폴링 모드 (read)

```python
from sdm_dds_pubsub import Subscriber
from hello_msgs import HelloWorld

subscriber = Subscriber("HelloWorld", datatype=HelloWorld)
for msg in subscriber.read():
    print(msg)
subscriber.close()

# with 구문
with Subscriber("HelloWorld", datatype=HelloWorld) as sub:
    for msg in sub.read():
        print(msg)
```

### 3.2 콜백 모드 (on_message)

```python
def on_message(msg):
    print(msg)

def on_error(exc, msg):
    print(f"콜백 예외: {exc}, msg={msg}")

subscriber = Subscriber(
    "HelloWorld",
    datatype=HelloWorld,
    on_message=on_message,
    on_error=on_error,  # 생략 시 콜백 내부 예외 무시
)
# 메인 스레드 유지 (예: time.sleep)
import time
while True:
    time.sleep(1)
```

### 3.3 동적 타입 discovery

`datatype`을 생략하면 DCPSPublication/DCPSSubscription에서 타입을 발견합니다.  
**Publisher를 먼저 실행**해야 합니다.

```python
from sdm_dds_pubsub import Subscriber, DiscoveryTimeoutError

try:
    subscriber = Subscriber("HelloWorld")  # datatype 생략
except DiscoveryTimeoutError as e:
    print(f"discovery 실패: {e}")
```

### 생성자

| 인자 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| topic_name | str | - | DDS 토픽 이름 |
| datatype | Type \| None | None | 메시지 타입 (None이면 동적 discovery) |
| on_message | Callable \| None | None | 콜백 (None이면 read() 사용) |
| on_error | Callable \| None | None | on_message 내부 예외 시 호출 (exc, msg) |
| domain_id | int | 0 | DDS 도메인 ID |
| discovery_timeout | float | 10.0 | 동적 discovery 대기 시간(초) |

### read()

| 인자 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| timeout_sec | float \| None | None | 다음 샘플 대기 시간 (None=무한) |
| max_samples | int | 64 | 한 번에 가져올 최대 샘플 수 |

- **콜백 모드에서는 read()를 호출할 수 없습니다.**

---

## 4. 예외

| 예외 | 설명 |
|------|------|
| PubSubError | PubSub 관련 기본 예외 |
| ConfigurationError | 인자/설정 오류 (topic_name 빈 문자열, domain_id < 0 등) |
| DiscoveryError | discovery 관련 오류 |
| DiscoveryTimeoutError | 동적 discovery 시간 초과 (datatype=None) |
| ConnectionError | DDS 엔티티 생성 실패 |
| PublishError | write() 실패 (msg None, 타입 불일치, 직렬화 오류 등) |
| SubscribeError | read() 호출 오류 (콜백 모드에서 read() 등) |
| CallbackError | on_message 콜백 내부 예외 (on_error로 처리 권장) |
| ClosedError | close() 후 write()/read() 호출 시 |

---

## 5. 예제

- `src/pubsub_publisher_example.py` - 발행
- `src/pubsub_subscriber_example.py` - 구독 (폴링)
- `src/pubsub_subscriber_callback_example.py` - 구독 (콜백)
