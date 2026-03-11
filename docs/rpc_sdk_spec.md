# RPC SDK 사양서

DDS-RPC 요청-응답 패턴을 위한 `sdm_dds_rpc` SDK의 사양 및 사용 가이드입니다.

---

## 목차

1. [개요](#1-개요)
2. [시작하기](#2-시작하기)
3. [프로토콜](#3-프로토콜)
4. [IDL 규칙](#4-idl-규칙)
5. [API 사양](#5-api-사양)
6. [사용 예시](#6-사용-예시)
7. [QoS](#7-qos)
8. [새 서비스 추가하기](#8-새-서비스-추가하기)
9. [문제 해결](#9-문제-해결)
10. [FAQ](#10-faq)

---

## 1. 개요

### 1.1 목적

- DDS 위에서 요청-응답(Request-Reply) 패턴 통신을 표준화합니다.
- 서버/클라이언트가 Request ID, 토픽명, 상관 로직을 직접 다루지 않도록 추상화합니다.
- 제네릭 설계로 새 서비스 추가 시 **SDK 코드 수정 없이** IDL만 추가하면 됩니다.

### 1.2 대상 독자

- DDS 기반 RPC를 사용하려는 개발자
- Eclipse Cyclone DDS + Python 환경에서 요청-응답 통신이 필요한 경우
- 서버 인스턴스 관리(다중 서버, 특정 서버 지정)가 필요한 경우

### 1.3 패키지 및 의존성

| 항목 | 설명 |
|------|------|
| **SDK 패키지** | `sdk/rpc/`, `idls/rpc/` (idls/rpc는 idlc 출력) |
| **설치** | `./idls/idl_to_py.sh` 실행 후 `pip install -e .` (프로젝트 루트에서 한 번만) |
| **의존성** | `cyclonedds`만 필요 (rpc 타입은 패키지에 포함) |

---

## 2. 시작하기

### 2.1 사전 준비

1. **환경 활성화**
   ```bash
   source activate_env.sh
   ```

2. **IDL 변환 및 패키지 설치**
   ```bash
   ./idls/idl_to_py.sh
   ```
   이 스크립트는 IDL을 Python으로 변환하고 `sdm-dds-rpc` 통합 패키지를 설치합니다.

### 2.2 최소 동작 확인 (5분)

**터미널 1 – 서버 실행**
```bash
source activate_env.sh
python src/rpc_server.py
```

**터미널 2 – 클라이언트 실행**
```bash
source activate_env.sh
python src/rpc_client.py
```

클라이언트가 `sum = 30` (10 + 20)을 출력하면 정상입니다.

### 2.3 아키텍처 개요

```
┌─────────────────┐                    ┌─────────────────┐
│   RpcClient     │   Add/Request      │   RpcServer     │
│                 │ ─────────────────► │                 │
│  client.call()  │   Add/Reply        │  handle_add()   │
│                 │ ◄───────────────── │                 │
└─────────────────┘                    └─────────────────┘
        │                                       │
        └───────────────┬───────────────────────┘
                        │ DDS 도메인 (domain_id=0)
                        │ RPC/ServiceRegistry (서버 목록)
                        ▼
              ┌─────────────────────┐
              │  Eclipse Cyclone DDS │
              └─────────────────────┘
```

---

## 3. 프로토콜

### 3.1 토픽 네이밍

| 구분 | 패턴 | 예시 |
|------|------|------|
| Request 토픽 | `{ServiceName}/Request` | `Add/Request` |
| Reply 토픽 | `{ServiceName}/Reply` | `Add/Reply` |

서비스 이름(예: `Add`)만 정하면 Request/Reply 토픽명은 자동으로 결정됩니다.

### 3.2 공통 헤더

모든 Request/Reply 타입은 아래 구조를 따라야 합니다.

**Request 타입**
- `header: RequestHeader` (필수)
- `RequestHeader.request_id`: UUID v4 문자열 (36자), **클라이언트에서 생성, SDK가 자동 설정**
- `RequestHeader.instance_name`: 대상 서버 인스턴스명 (선택, 지정 시 해당 서버만 응답)

**Reply 타입**
- `header: ReplyHeader` (필수)
- `ReplyHeader.related_request_id`: 요청의 `request_id`와 동일 (상관 매칭용)
- `ReplyHeader.remote_ex`: 원격 예외 코드 (0이면 정상)
- `ReplyHeader.server_instance`: 응답한 서버의 인스턴스명

### 3.3 원격 예외 코드

| 코드 | 상수 | 설명 |
|------|------|------|
| 0 | `REMOTE_EX_OK` | 정상 |
| 1 | `REMOTE_EX_UNSUPPORTED` | 지원하지 않음 |
| 2 | `REMOTE_EX_INVALID_ARGUMENT` | 잘못된 인자 |
| 3 | `REMOTE_EX_OUT_OF_RESOURCES` | 리소스 부족 |
| 4 | `REMOTE_EX_UNKNOWN_OPERATION` | 알 수 없는 연산 |
| 5 | `REMOTE_EX_UNKNOWN_EXCEPTION` | 기타 예외 |

핸들러에서 예외가 발생하면 `REMOTE_EX_UNKNOWN_EXCEPTION`으로 Reply가 전송되고, 클라이언트는 `RPCRemoteError`를 받습니다.

---

## 4. IDL 규칙

### 4.1 모듈 구조

- **rpc 모듈**: `RequestHeader`, `ReplyHeader`, `RemoteExceptionCode` (공통)
- **services 모듈**: 각 서비스의 `*_Request`, `*_Reply`, `*_In`, `*_Out`

### 4.2 Request/Reply 정의 템플릿

새 서비스를 정의할 때 아래 템플릿을 따르세요.

```idl
// idls/services/AddService.idl 예시

#include "rpc/Headers.idl"

module services {

@nested
struct Add_In {
    long a;
    long b;
};

@nested
struct Add_Out {
    long sum;
};

struct Add_Request {
    rpc::RequestHeader header;
    Add_In data;
};

struct Add_Reply {
    rpc::ReplyHeader header;
    Add_Out data;
};
};
```

- `*_In`: 요청 데이터 (서비스별 입력)
- `*_Out`: 응답 데이터 (서비스별 출력)
- `*_Request`: `header` + `*_In` (data)
- `*_Reply`: `header` + `*_Out` (data)

### 4.3 IDL 파일 위치

| 경로 | 용도 |
|------|------|
| `idls/rpc/Headers.idl` | RequestHeader, ReplyHeader, RemoteExceptionCode |
| `idls/rpc/ServiceRegistry.idl` | ServiceRegistryEntry (서버 목록, 중복 검사) |
| `idls/services/*.idl` | 서비스별 Request/Reply 정의 |

### 4.4 서비스 네임스페이스 (idl_to_py 후처리)

`idl_to_py.sh` 실행 시 `*_Request`, `*_Reply`, `*_In`, `*_Out`를 하나의 네임스페이스로 묶습니다.

```python
from services import Add  # Add.Request, Add.Reply, Add.In, Add.Out

# 권장: 네임스페이스 사용 (직관적)
req = Add.Request(header=..., data=Add.In(a=10, b=20))
rep = Add.Reply(header=..., data=Add.Out(sum=30))

# 하위 호환: 기존 이름도 사용 가능
from services import Add_Request, Add_Reply, Add_In, Add_Out
```

| 네임스페이스 | 동일 타입 |
|-------------|----------|
| `Add.Request` | `Add_Request` |
| `Add.Reply` | `Add_Reply` |
| `Add.In` | `Add_In` |
| `Add.Out` | `Add_Out` |

---

## 5. API 사양

### 5.1 RpcServer (서버)

#### 생성자

```python
RpcServer(domain_id: int = 0)
```

- `domain_id`: DDS 도메인 ID (클라이언트와 동일해야 통신 가능)

#### register_service

```python
register_service(
    name: str,
    request_type: type,
    response_type: type,
    handler: Callable[[RequestType], ResponseType],
    instance_name: str | None = None
) -> None
```

| 매개변수 | 설명 |
|----------|------|
| `name` | 서비스 이름 (토픽 prefix, 예: `"Add"`) |
| `request_type` | Request 타입 클래스 (예: `Add.Request`) |
| `response_type` | Reply 타입 클래스 (예: `Add.Reply`) |
| `handler` | `(request) -> response` 콜러블. 요청을 받아 응답을 반환 |
| `instance_name` | (선택) 서버 인스턴스명. 지정 시 해당 인스턴스로만 요청 처리. 동일 서비스에 중복 등록 시 `RPCDuplicateInstanceError` 발생 |

- `instance_name`을 지정한 서버만 `list_servers()`로 조회됩니다.
- `instance_name` 없이 등록하면 "인스턴스 미지정" 서버가 되어, `instance` 없이 호출한 클라이언트 요청만 처리합니다.

#### run / stop

```python
run() -> None   # 블로킹. 이벤트 루프 실행
stop() -> None  # 루프 종료
```

`run()`은 `stop()`이 호출되거나 KeyboardInterrupt까지 블로킹됩니다.

---

### 5.2 RpcClient (클라이언트)

#### 생성자

```python
RpcClient(domain_id: int = 0)
```

#### call

```python
call(
    service_name: str,
    request: RequestType,
    response_type: Type[ReplyType],
    timeout: float = 5.0,
    instance: str | None = None
) -> ReplyType
```

| 매개변수 | 설명 |
|----------|------|
| `service_name` | 서비스 이름 (예: `"Add"`) |
| `request` | Request 인스턴스. `header`는 SDK가 자동 설정 |
| `response_type` | Reply 타입 클래스 (역직렬화용) |
| `timeout` | 대기 시간(초). 초과 시 `RPCTimeoutError` |
| `instance` | (선택) 대상 서버 인스턴스명. `None`이면 아무 서버나 응답 |

**반환값**: Reply 인스턴스. `response.header.server_instance`로 응답한 서버를 확인할 수 있습니다.

#### list_servers

```python
list_servers(
    service_name: str | None = None,
    timeout: float = 3.0
) -> list[tuple[str, str]]
```

| 매개변수 | 설명 |
|----------|------|
| `service_name` | 필터링할 서비스 이름. `None`이면 전체 |
| `timeout` | 레지스트리 discovery 대기 시간(초) |

**반환값**: `[(service_name, instance_name), ...]` 목록.

> **범위**: 레지스트리(`RPC/ServiceRegistry`)는 **동일 DDS 도메인**에서만 유효합니다. 다른 도메인의 서버는 조회되지 않습니다.

---

### 5.3 예외

| 예외 | 발생 조건 |
|------|-----------|
| `RPCTimeoutError` | `timeout` 내에 Reply를 수신하지 못함 (서버 없음, 네트워크 지연 등) |
| `RPCRemoteError` | 서버가 `remote_ex != REMOTE_EX_OK`로 응답. `e.remote_ex_code`로 코드 확인 |
| `RPCDuplicateInstanceError` | 동일 `(서비스명, instance_name)`으로 서버를 등록하려 할 때 |
| `RPCConnectionError` | (선택) 서버/토픽 발견 실패. 현재 구현에서는 주로 `RPCTimeoutError`로 대체됨 |

---

## 6. 사용 예시

### 6.1 서버 – 기본 (인스턴스 미지정)

```python
from sdm_dds_rpc import RpcServer
from rpc import ReplyHeader, RemoteExceptionCode
from services import Add

def handle_add(req: Add.Request) -> Add.Reply:
    result = req.data.a + req.data.b
    return Add.Reply(
        header=ReplyHeader(
            related_request_id="",
            remote_ex=RemoteExceptionCode.REMOTE_EX_OK,
            server_instance="",
        ),
        data=Add.Out(sum=result),
    )

server = RpcServer(domain_id=0)
server.register_service("Add", Add.Request, Add.Reply, handle_add)
server.run()
```

### 6.2 서버 – 인스턴스 지정 (다중 서버)

```python
# 인스턴스명으로 서버 구분, list_servers()에 등록됨
server.register_service(
    "Add", Add.Request, Add.Reply, handle_add,
    instance_name="add-server-1"
)
```

### 6.3 클라이언트 – 기본 호출

```python
from sdm_dds_rpc import RpcClient
from rpc import RequestHeader
from services import Add

client = RpcClient(domain_id=0)
req = Add.Request(
    header=RequestHeader(request_id="", instance_name=""),
    data=Add.In(a=10, b=20),
)
rep = client.call("Add", req, Add.Reply, timeout=5.0)
print(rep.data.sum)  # 30
```

### 6.4 클라이언트 – 특정 서버 지정

```python
# list_servers()로 확인 후 특정 인스턴스 지정
servers = client.list_servers(service_name="Add")
print(servers)  # [('Add', 'add-server-1'), ...]

rep = client.call("Add", req, Add.Reply, instance="add-server-1")
print(rep.header.server_instance)  # add-server-1
```

### 6.5 에러 처리

```python
from sdm_dds_rpc import RpcClient
from sdm_dds_rpc.exceptions import RPCTimeoutError, RPCRemoteError

try:
    rep = client.call("Add", req, Add.Reply, timeout=3.0)
except RPCTimeoutError as e:
    print(f"타임아웃: {e}")  # 서버가 없거나 응답 지연
except RPCRemoteError as e:
    print(f"원격 예외: {e}, 코드={e.remote_ex_code}")
```

---

## 7. QoS

| 항목 | 설정 | 설명 |
|------|------|------|
| Durability | Volatile (레지스트리) / Transient Local (Request, Reply) | 레지스트리는 일시적, Request/Reply는 지속성 유지 |
| Reliability | Reliable | 요청-응답은 손실 없이 전달 |
| History | Keep Last, Depth 1 | 1:1 패턴에 적합 |

---

## 8. 새 서비스 추가하기

1. **IDL 작성** – `idls/services/SubtractService.idl` 등
   ```idl
   #include "rpc/Headers.idl"
   module services {
     @nested struct Subtract_In { long a; long b; };
     @nested struct Subtract_Out { long diff; };
     struct Subtract_Request { rpc::RequestHeader header; Subtract_In data; };
     struct Subtract_Reply { rpc::ReplyHeader header; Subtract_Out data; };
   };
   ```

2. **변환 및 설치**
   ```bash
   ./idls/idl_to_py.sh
   ```

3. **서버 등록**
   ```python
   from services import Subtract
   server.register_service("Subtract", Subtract.Request, Subtract.Reply, handle_subtract)
   ```

4. **클라이언트 호출**
   ```python
   req = Subtract.Request(header=..., data=Subtract.In(a=20, b=7))
   rep = client.call("Subtract", req, Subtract.Reply)
   ```

**SDK 코드 수정은 필요 없습니다.** IDL 추가와 빌드만 하면 됩니다.

---

## 9. 문제 해결

### 타임아웃이 자주 발생해요

- 서버가 **먼저** 실행 중인지 확인하세요.
- `domain_id`가 클라이언트와 서버에서 동일한지 확인하세요.
- 방화벽이나 멀티캐스트가 막혀 있지 않은지 확인하세요.

### list_servers()가 비어 있어요

- `instance_name`을 지정한 서버만 등록됩니다. `instance_name` 없이 등록한 서버는 목록에 없습니다.
- 서버 시작 후 discovery에 시간이 걸릴 수 있으므로 `timeout`을 늘려보세요 (예: 5초).

### RPCDuplicateInstanceError가 발생해요

- 같은 `(서비스명, instance_name)`으로 다른 프로세스가 이미 서버를 등록했습니다.
- 다른 `instance_name`을 사용하거나, 기존 서버를 종료하세요.

### header를 직접 채워야 하나요?

- `request_id`, `instance_name`은 SDK가 `call()` 시점에 자동 설정합니다.
- 서버 핸들러에서는 `ReplyHeader.related_request_id` 등을 설정해야 합니다. 예제를 참고하세요.

---

## 10. FAQ

**Q. Python 외에 C/C++에서도 사용할 수 있나요?**  
A. 현재 SDK는 Python 전용입니다. C/C++는 Cyclone DDS API로 직접 구현해야 합니다. C에서는 `Add_Request` 등의 네이밍 규칙, C++에서는 `Add::Request` 형태의 namespace 적용이 가능합니다.

**Q. 비동기 호출을 지원하나요?**  
A. 현재는 동기 `call()`만 제공합니다. 비동기는 별도 구현이 필요합니다.

**Q. 서버가 여러 개일 때 누가 응답하나요?**  
A. `instance`를 지정하지 않으면 **먼저 응답한** 서버의 Reply를 사용합니다. 특정 서버를 지정하려면 `instance` 인자를 사용하세요.

**Q. DDS 도메인을 바꿔도 되나요?**  
A. 네. `domain_id`만 맞추면 됩니다. 서버와 클라이언트가 같은 `domain_id`를 사용해야 합니다.
