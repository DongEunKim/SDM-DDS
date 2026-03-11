# SDM-DDS

SDM(Software Defined Machine) 프로젝트의 DDS(Data Distribution Service) 통합 및 개발을 위한 저장소입니다.

Eclipse Cyclone DDS를 사용하여 Python 기반 Pub/Sub 및 RPC(요청-응답) 예제를 제공합니다.

## 요구 사항

- Python 3.7+
- CMake 3.10+
- GCC (또는 호환 C 컴파일러)
- Git

## 프로젝트 구조

```
SDM-DDS/
├── venv/              # Python 가상환경
├── cyclonedds/        # Eclipse Cyclone DDS C 라이브러리 (소스 + 빌드)
├── idls/              # IDL 전용 (소스 + 변환)
│   ├── rpc/           # RPC 공통 (IDL + 생성 Python)
│   ├── services/      # RPC 서비스 IDL (Add, Calculate 등)
│   ├── build/         # idlc 산출물 (생성됨)
│   └── idl_to_py.sh   # IDL → Python 변환
├── sdk/               # SDK 전용
│   ├── rpc/           # RPC SDK (client, server, exceptions)
│   └── setup.py       # pip install -e . 로 SDK 단독 설치
├── src/               # 예제
│   ├── publisher.py   # HelloWorld 정적 타입 발행
│   ├── subscriber.py  # XTypes 동적 타입 구독 (WaitSet 폴링)
│   ├── subscriber_callback.py  # HelloWorld 콜백 구독 (Listener)
│   ├── rpc_server.py  # Add RPC 서버 예제
│   └── rpc_client.py  # Add RPC 클라이언트 예제
├── docs/              # 문서
├── activate_env.sh    # 환경 활성화 스크립트
├── requirements.txt   # Python 의존성
└── README.md
```

## 시작하기

### 1. 환경 활성화

```bash
source activate_env.sh
```

이 스크립트는 가상환경 활성화와 Cyclone DDS 라이브러리 경로(`CYCLONEDDS_HOME`, `LD_LIBRARY_PATH`)를 설정합니다.

### 2. IDL → Python 변환 및 설치

```bash
./idls/idl_to_py.sh
```

- `idls/` 내 모든 IDL을 `#include` 기반으로 의존성 분석 후 변환
- `idls/build/`에 생성된 패키지 출력
- `rpc` Python을 idls/rpc/에 갱신 (IDL과 함께 위치)
- `pip install -e .` (sdm-dds-rpc 통합 패키지) 자동 실행

### 3. Pub/Sub 예제 실행

**터미널 1** (Subscriber 먼저 실행):

```bash
source activate_env.sh
python src/subscriber.py           # 동적 타입 + WaitSet 폴링
python src/subscriber_callback.py  # 정적 타입 + Listener 콜백
```

**터미널 2** (Publisher 실행):

```bash
source activate_env.sh
python src/publisher.py
```

- `subscriber.py`: XTypes 동적 타입 발견 + WaitSet 폴링
- `subscriber_callback.py`: 정적 타입 + Listener 콜백 (`on_data_available`)

### 4. RPC 예제 실행

**터미널 1** (서버 먼저 실행, 인스턴스명 지정):

```bash
source activate_env.sh
python src/rpc_server.py add-server-1
```

**터미널 2** (클라이언트 실행):

```bash
source activate_env.sh
python src/rpc_client.py              # 아무 서버나 응답
python src/rpc_client.py add-server-1 # 특정 서버 지정
```

- 서버: `instance_name`으로 구분, 동일 인스턴스명 중복 실행 시 오류
- 클라이언트: `list_servers()`로 등록된 서버 조회, `response.header.server_instance`로 응답 서버 확인

- Add 예제: `rpc_server.py`, `rpc_client.py`
- Calculate 예제: `calculate_server.py`, `calculate_client.py` (op: add/sub/mul)

RPC SDK 사용법은 [docs/rpc_sdk_spec.md](docs/rpc_sdk_spec.md)를 참조하세요.

## 메시지 타입

| 패키지 | 타입 | 설명 |
|--------|------|------|
| hello_msgs | HelloWorld | 예제 메시지 (header, msg, count) |
| sensor_msgs.msg | NavSatStatus, NavSatFix | GNSS 관련 메시지 |
| std_msgs.msg | Time, Header | 공통 타입 |
| rpc | RequestHeader, ReplyHeader | RPC 공통 헤더 |
| services | Add, Calculate (Add.Request, Calculate.In 등) | RPC 서비스 |

## 의존성

| 패키지 | 용도 |
|--------|------|
| sdm-dds-rpc | 통합 패키지 (`pip install -e .`): RPC SDK + IDL 생성 메시지 패키지 |
| cyclonedds | Eclipse Cyclone DDS Python API (sdm-dds-rpc 의존성) |

## 문서

- [docs/idl_guide.md](docs/idl_guide.md) – IDL 작성 규칙, 폴더 구조, 참조 구조
- [docs/rpc_sdk_spec.md](docs/rpc_sdk_spec.md) – RPC SDK 사양 및 사용법
- [docs/idl_change_without_source_modification.md](docs/idl_change_without_source_modification.md) – XTypes 동적 타입 발견 원리

## 라이선스

<!-- TODO: 라이선스 정보 추가 -->
