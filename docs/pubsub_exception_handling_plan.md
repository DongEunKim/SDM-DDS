# PubSub SDK 예외 처리 계획

발행·구독 시 발생 가능한 예외 상황과 처리 방안을 정리합니다.

---

## 1. 예외 계층 구조 (제안)

```text
PubSubError (기본)
├── ConfigurationError     # 설정/인자 오류
├── DiscoveryError         # discovery 관련
│   └── DiscoveryTimeoutError (기존)
├── ConnectionError        # DDS 엔티티 생성/연결 오류
├── PublishError           # write() 실패
├── SubscribeError         # read()/콜백 관련
└── CallbackError          # on_message 콜백 내부 예외
```

---

## 2. Publisher 예외

### 2.1 생성자 (__init__)

| 상황 | 발생 시점 | 처리 방안 |
|------|-----------|-----------|
| **인자 검증 실패** | topic_name 빈 문자열, None | `ConfigurationError` – "topic_name은 비어있을 수 없습니다" |
| **datatype None** | datatype=None | `ConfigurationError` – "datatype은 필수입니다" |
| **domain_id 범위 초과** | domain_id < 0 | `ConfigurationError` – "domain_id는 0 이상이어야 합니다" |
| **Cyclone DDS 미설치** | import/초기화 | cyclonedds가 던지는 예외 그대로 전파 (ImportError 등) |
| **CYCLONEDDS_HOME 미설정** | DomainParticipant 생성 | DDSException 전파 → `ConnectionError`로 래핑 권장 |
| **DomainParticipant 생성 실패** | DomainParticipant() | DDSException → `ConnectionError` |
| **Topic 생성 실패** | Topic() | DDSException → `ConnectionError` |
| **DataWriter 생성 실패** | DataWriter() | DDSException → `ConnectionError` |
| **리소스 부족** | 엔티티 생성 시 | DDS_RETCODE_OUT_OF_RESOURCES → `ConnectionError` |

### 2.2 write()

| 상황 | 발생 시점 | 처리 방안 |
|------|-----------|-----------|
| **msg None** | write(None) | `ConfigurationError` 또는 TypeError |
| **msg 타입 불일치** | datatype과 다른 타입 | `PublishError` – "메시지 타입이 topic datatype과 일치하지 않습니다" |
| **직렬화 실패** | 잘못된 필드 값 | DDSException → `PublishError` |
| **History 풀** | QoS 제한 초과 | DDSException → `PublishError` |
| **이미 닫힌 writer** | write after close | DDSException/IllegalOperation → `PublishError` |

---

## 3. Subscriber 예외

### 3.1 생성자 (__init__)

| 상황 | 발생 시점 | 처리 방안 |
|------|-----------|-----------|
| **인자 검증 실패** | topic_name 빈 문자열, discovery_timeout < 0 | `ConfigurationError` |
| **on_message + read 혼용** | (없음 – read()에서 검사) | - |
| **DomainParticipant 등 생성 실패** | Publisher와 동일 | `ConnectionError` |
| **discover_datatype 실패** | datatype=None 시 timeout | `DiscoveryTimeoutError` (기존) |
| **get_types_for_typeid 실패** | type_id 조회 중 | DDSException → `DiscoveryError` |
| **Topic/DataReader 생성 실패** | Publisher와 동일 | `ConnectionError` |

### 3.2 read()

| 상황 | 발생 시점 | 처리 방안 |
|------|-----------|-----------|
| **콜백 모드에서 read() 호출** | 이미 처리됨 | `RuntimeError` → `SubscribeError`로 명시적 래핑 권장 |
| **timeout_sec < 0** | read(timeout_sec=-1) | `ConfigurationError` |
| **max_samples <= 0** | read(max_samples=0) | `ConfigurationError` |
| **Reader 닫힘** | read 중 엔티티 소멸 | DDSException → `SubscribeError` |
| **waitset.wait() 예외** | DDS 내부 오류 | DDSException → `SubscribeError` |

### 3.3 콜백 (on_message)

| 상황 | 발생 시점 | 처리 방안 |
|------|-----------|-----------|
| **콜백 내부 예외** | on_message(msg) 내부에서 raise | 기본: 로그 후 무시. 옵션: `on_error` 콜백 또는 예외 전파 (스레드 안전성 주의) |
| **콜백 블로킹** | on_message에서 무거운 작업 | 문서화로 권고, SDK에서는 처리 불가 |

---

## 4. _discovery 모듈 예외

| 상황 | 발생 시점 | 처리 방안 |
|------|-----------|-----------|
| **timeout_sec <= 0** | discover_datatype(timeout_sec=0) | `ConfigurationError` 또는 검증 후 호출 |
| **get_types_for_typeid 실패** | type_id 조회 timeout/오류 | DDSException → 호출자가 `DiscoveryError`로 래핑 |
| **participant None/잘못됨** | 내부 검증 | 호출 전 검증 (Publisher/Subscriber 쪽) |

---

## 5. Cyclone DDS 예외 래핑

Cyclone DDS Python은 `DDSException`(또는 유사 예외)을 던질 수 있음. 공통 처리 전략:

1. **인자/설정 오류** (BAD_PARAMETER 등) → `ConfigurationError`
2. **리소스/연결 오류** (OUT_OF_RESOURCES, TIMEOUT 등) → `ConnectionError` / `DiscoveryError`
3. **write 실패** → `PublishError`
4. **read/콜백 실패** → `SubscribeError`
5. **원인 알 수 없음** → `PubSubError`로 래핑 후 전파

---

## 6. 구현 우선순위

### Phase 1 (필수) ✅ 완료
1. `exceptions.py` – 예외 클래스 정의
2. Publisher/Subscriber **인자 검증** (topic_name, datatype, domain_id, timeout 등)
3. DDSException **래핑** (ConnectionError, PublishError, SubscribeError)
4. DiscoveryTimeoutError → DiscoveryError 하위로 이동

### Phase 2 (권장) ✅ 완료
5. `write()` – msg None/타입 검증
6. `read()` – timeout_sec, max_samples 검증
7. 콜백 내부 예외 – `on_error` 콜백 옵션

### Phase 3 (선택) ✅ 완료
8. `close()` 메서드 – 명시적 정리 및 "이미 닫힘" 검사
9. 컨텍스트 매니저 (`with` 구문) 지원
10. 로깅 설정 – on_error 콜백으로 대체 (Phase 2에서 구현)

---

## 7. API 변경 제안

### Subscriber 콜백 예외 처리 옵션

```python
Subscriber(
    "HelloWorld",
    datatype=HelloWorld,
    on_message=callback,
    on_error=lambda exc, msg: log.error(...),  # 콜백 예외 시 호출
    raise_on_callback_error=False,             # True면 예외 전파 (위험)
)
```

### Publisher/Subscriber close()

```python
publisher.close()   # writer/participant 정리
subscriber.close()  # reader/participant 정리
# close() 후 write()/read() → PubSubError
```
