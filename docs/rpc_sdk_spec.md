# RPC SDK 사양서

DDS-RPC 요청-응답 패턴을 위한 `sdm_dds_rpc` SDK의 사양을 정의합니다.

---

## 1. 개요

### 1.1 목적

- DDS 위에서 요청-응답(Request-Reply) 패턴 통신을 표준화
- 서버/클라이언트가 Request ID, 토픽명, 상관 로직을 직접 다루지 않도록 추상화
- 제네릭 설계로 새 서비스 추가 시 SDK 수정 없이 확장 가능

### 1.2 위치 및 패키지

- **SDK 패키지**: 프로젝트 최상위 `sdm_dds_rpc/`
- **설치**: `pip install -e .` (sdm_dds_rpc 폴더 또는 프로젝트 루트의 pyproject.toml 기준)
- **의존성**: `cyclonedds`, `sdm-dds-idls`

---

## 2. 프로토콜

### 2.1 토픽 네이밍

| 구분 | 패턴 | 예시 |
|------|------|------|
| Request 토픽 | `{ServiceName}/Request` | `Add/Request` |
| Reply 토픽 | `{ServiceName}/Reply` | `Add/Reply` |

### 2.2 공통 헤더 컨벤션

모든 Request/Reply 타입은 다음 구조를 준수합니다.

**Request 타입**
- 필수 필드: `header: RequestHeader`
- `RequestHeader`: `request_id: string<36>` (UUID), `instance_name: string<255>` (선택)

**Reply 타입**
- 필수 필드: `header: ReplyHeader`
- `ReplyHeader`: `related_request_id: string<36>`, `remote_ex: RemoteExceptionCode`

### 2.3 Request ID

- 형식: UUID v4 문자열 (36자, 예: `550e8400-e29b-41d4-a716-446655440000`)
- 클라이언트가 생성, 서버가 Reply의 `related_request_id`에 그대로 설정하여 상관

### 2.4 원격 예외 코드

```
REMOTE_EX_OK = 0
REMOTE_EX_UNSUPPORTED = 1
REMOTE_EX_INVALID_ARGUMENT = 2
REMOTE_EX_OUT_OF_RESOURCES = 3
REMOTE_EX_UNKNOWN_OPERATION = 4
REMOTE_EX_UNKNOWN_EXCEPTION = 5
```

---

## 3. IDL 규칙

### 3.1 모듈 구조

- **rpc 모듈**: `RequestHeader`, `ReplyHeader`, `RemoteExceptionCode` (공통)
- **services 모듈** (또는 서비스별 모듈): 각 서비스의 `*_Request`, `*_Reply`

### 3.2 Request/Reply 정의 템플릿

```idl
// 서비스명_Request
struct Add_Request {
    rpc.RequestHeader header;
    Add_In data;   // 서비스별 입력
};

// 서비스명_Reply
struct Add_Reply {
    rpc.ReplyHeader header;
    Add_Out data;  // 서비스별 출력
};
```

### 3.3 IDL 파일 위치

- `idls/rpc/Headers.idl` : RequestHeader, ReplyHeader, RemoteExceptionCode (공통)
- `idls/services/` : 서비스별 Request/Reply

---

## 4. API 사양

### 4.1 RpcServer (서버)

| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `register_service` | `(name, RequestType, ResponseType, handler) -> None` | 서비스 등록 |
| `run` | `() -> None` | 이벤트 루프 실행 (블로킹) |
| `stop` | `() -> None` | 루프 종료 (선택) |

- `handler`: `(request: RequestType) -> ResponseType` 콜러블
- 서버 내부에서 `request.header.request_id`를 `response.header.related_request_id`에 복사

### 4.2 RpcClient (클라이언트)

| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `call` | `(name, request, ResponseType, timeout=5.0) -> ResponseType` | 동기 호출 |

- `request`: `RequestType` 인스턴스 (header는 SDK가 자동 설정)
- `ResponseType`: 응답 역직렬화용 클래스 (예: `Add_Reply`)
- `timeout`: 초 단위, 초과 시 `RPCTimeoutError` 발생

### 4.3 예외

| 예외 | 발생 조건 |
|------|-----------|
| `RPCTimeoutError` | 지정 시간 내 Reply 수신 실패 |
| `RPCConnectionError` | 서버/토픽 발견 실패 (선택) |
| `RPCRemoteError` | `ReplyHeader.remote_ex != REMOTE_EX_OK` |

---

## 5. 사용 예시

### 5.1 서버

```python
from sdm_dds_rpc import RpcServer
from services.msg import Add_Request, Add_Reply

def handle_add(req: Add_Request) -> Add_Reply:
    return Add_Reply(
        header=...,  # SDK가 related_request_id 설정
        data=Add_Out(sum=req.data.a + req.data.b)
    )

server = RpcServer(domain_id=0)
server.register_service("Add", Add_Request, Add_Reply, handle_add)
server.run()
```

### 5.2 클라이언트

```python
from sdm_dds_rpc import RpcClient
from services.msg import Add_Request, Add_In, Add_Reply, Add_Out

client = RpcClient(domain_id=0)
req = Add_Request(header=..., data=Add_In(a=10, b=20))  # header는 SDK가 채움
rep = client.call("Add", req, Add_Reply, timeout=5.0)
print(rep.data.sum)  # 30
```

> 실제 사용 시 header 생성은 SDK가 내부에서 처리하므로, 사용자는 `data` 부분만 채우는 API로 간소화 가능.

---

## 6. QoS

- Request/Reply 토픽: **Reliable**, **Durable** (Transient Local 권장)
- History: **Keep Last**, Depth 1 (요청-응답은 1:1)

---

## 7. 확장성

- 새 서비스 추가 시: IDL 추가 → idl_to_py 빌드 → `register_service` / `call`로 사용
- **SDK 코드 변경 불필요**
