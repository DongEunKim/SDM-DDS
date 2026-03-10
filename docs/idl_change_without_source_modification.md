# IDL 변경 시 소스코드 수정 없이 동작하는 원리

## 개요

SDM-DDS Subscriber는 **DDS-XTypes 기반 동적 타입 발견**을 사용하여, Publisher가 IDL을 변경해도 구독자 소스코드를 수정하지 않고 새 타입으로 구독할 수 있습니다. 이 문서는 그 원리와 관련 메커니즘을 설명합니다.

---

## 1. 전통적 DDS 접근법의 한계

전통적인 DDS Pub/Sub에서는 다음과 같은 흐름이 필요합니다:

```
IDL 파일 → IDL 컴파일러(idlc) → 언어별 타입/직렬화 코드 생성 → 애플리케이션 컴파일
```

- IDL을 변경하면 **idlc로 코드 재생성**이 필요합니다.
- C/C++의 경우 **애플리케이션 재컴파일**이 필요합니다.
- Python의 경우 생성된 모듈(`idls/build/`)이 변경되므로, IDL 수정 시 `idl_to_py.sh`를 다시 실행해야 합니다.

즉, **IDL 변경 = 코드 재생성**이 기본 모델입니다. Publisher는 반드시 idlc 재실행이 필요하지만, **Subscriber는 동적 타입을 사용하면 소스 수정 없이** 새 타입을 받을 수 있습니다.

---

## 2. DDS-XTypes 기반 동적 타입 발견

### 2.1 핵심 아이디어

토픽의 타입 정보를 **런타임에 네트워크로부터 조회**하여, 구독자가 해당 타입을 미리 알지 못해도 구독할 수 있게 합니다.

### 2.2 DDS-XTypes란

[DDS-XTypes (Extensible and Dynamic Topic Types for DDS)](https://www.omg.org/spec/DDS-XTypes/) OMG 명세는 다음을 가능하게 합니다:

- 토픽의 **타입 기술(Type Object)**이 discovery 정보와 함께 전달됩니다.
- 타입이 네트워크 상에서 **공유·조회** 가능합니다.
- 구독자는 Publisher가 제공하는 타입 기술을 활용해 **컴파일 시점에 타입을 알지 못해도** 데이터를 역직렬화하고 구독할 수 있습니다.

### 2.3 동작 흐름

1. **Publisher**: IDL로 생성된 타입으로 토픽에 발행합니다. DDS 미들웨어가 `TypeInformation`(TypeIdentifier 포함)을 discovery 메시지에 실어 보냅니다.
2. **Subscriber**: Built-in Topic `DCPSPublication`/`DCPSSubscription`을 읽어 특정 토픽에 대한 `type_id`를 얻습니다.
3. **Type Lookup**: `type_id`로 원격 노드에 TypeObject 조회를 요청합니다.
4. **런타임 타입 생성**: TypeObject를 수신한 뒤, 이에 해당하는 **런타임 타입(클래스)**을 생성합니다.
5. 이 타입으로 Topic/DataReader를 생성하여 구독합니다.

### 2.4 Cyclone DDS Python 예시

Cyclone DDS Python은 `cyclonedds.dynamic.get_types_for_typeid()`로 이를 지원합니다:

```python
from cyclonedds.dynamic import get_types_for_typeid
from cyclonedds.builtin import BuiltinTopicDcpsPublication
from cyclonedds.core import ReadCondition

# Built-in Topic에서 토픽의 type_id 획득
for pub in publication_reader.take(...):
    if pub.topic_name == "HelloWorld" and pub.type_id is not None:
        datatype, _ = get_types_for_typeid(participant, pub.type_id, timeout)
        # datatype: 런타임에 생성된 Python 클래스 (IdlStruct)
        topic = Topic(participant, "HelloWorld", datatype)
        reader = DataReader(participant, topic)
        # 구독 시작
```

**특징**:

- 구독자에는 **어떤 IDL/타입도 하드코딩할 필요가 없습니다**.
- Publisher가 새 IDL로 변경되어도, Publisher 쪽에서 idlc 재실행만 하면 됩니다.
- Subscriber는 **소스 수정 없이** Publisher가 제공하는 새 타입으로 구독할 수 있습니다.
- 다만, `sample.msg`, `sample.header.stamp` 등 **필드 접근 방식**이 바뀌면 Subscriber 코드 수정이 필요합니다. (예: `ts` → `header.stamp`)

---

## 3. SDM-DDS 프로젝트 구조

현재 SDM-DDS 구조:

| 구분 | 설명 |
|------|------|
| IDL 소스 | `idls/HelloWorld.idl`, `idls/NavStatFix.idl`, `idls/std_msgs/msg/` 등 |
| idlc 출력 | `idls/build/` (hello_msgs, sensor_msgs, std_msgs) |
| Publisher | `hello_msgs.HelloWorld` 등 **생성된 타입**을 직접 사용, 정적 타입 |
| Subscriber | `get_types_for_typeid()`로 **동적 타입** 획득 후 구독 |

### 3.1 동적 구독 적용 상태

- Subscriber(`src/subscriber.py`)는 Built-in Topic으로 `HelloWorld` 토픽의 `type_id`를 획득합니다.
- `get_types_for_typeid()`로 런타임 타입을 받아 Topic/DataReader를 생성합니다.
- Publisher가 IDL을 바꾸고 idlc로 재생성해도, Subscriber 소스는 그대로 두고 실행할 수 있습니다.
- 단, 새 타입의 필드 구조(예: `header`, `stamp`)를 사용하는 로직은 필요에 따라 수정해야 합니다.

---

## 4. 다른 접근법 (참고)

### 4.1 런타임 IDL 로딩 (Fast DDS 방식)

Fast DDS는 IDL을 **실행 시점**에 파싱하여 DynamicType을 만드는 방식을 지원합니다. 애플리케이션 재컴파일 없이 IDL 파일 경로·타입 이름만 설정으로 변경하면 됩니다. Cyclone DDS는 이 방식을 기본 지원하지 않습니다.

### 4.2 매핑 기반 추상화 (Kuksa DDS-Provider)

DDS 토픽·필드를 VSS(Vehicle Signal Specification) datapoint에 매핑하고, 애플리케이션은 DDS 타입 대신 datapoint 기준으로 동작합니다. IDL 변경 시 **매핑 파일만 갱신**하면 핵심 로직 수정을 최소화할 수 있습니다.

---

## 5. 요약

| 항목 | 내용 |
|------|------|
| **Publisher** | IDL 변경 시 `idl_to_py.sh` 재실행 필요. `hello_msgs.HelloWorld` 등 정적 타입 사용. |
| **Subscriber** | XTypes 동적 타입 발견 사용. 타입 획득은 런타임에 자동. 필드 접근 로직은 새 타입에 맞게 수정할 수 있음. |
| **필요 조건** | Cyclone DDS가 XTypes/Type Discovery를 지원하도록 빌드되어 있어야 함. |

---

## 참고 자료

- [DDS-XTypes OMG 명세](https://www.omg.org/spec/DDS-XTypes/)
- Cyclone DDS - Type support: `cyclonedds/docs/dev/typesupport.md`
- Cyclone DDS - Type discovery: `cyclonedds/docs/dev/type_discovery.md`
- [Fast DDS - Dynamic Types IDL Parsing](https://fast-dds.docs.eprosima.com/en/3.x/fastdds/xtypes/idl_parsing.html)
- [Eclipse Kuksa DDS Provider](https://github.com/eclipse-kuksa/kuksa-dds-provider)
