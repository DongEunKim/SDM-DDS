# IDL 가이드: idls 폴더 구성

SDM-DDS 프로젝트의 `idls/` 디렉터리에 DDS 메시지 IDL을 구성하기 위한 작성 규칙, 폴더 구조, 참조 구조, 타입 정의 방법을 설명합니다.

---

## 1. IDL 개요

### 1.1 IDL이란

**IDL(Interface Definition Language)**은 OMG 표준으로, 데이터 타입과 인터페이스를 언어 중립적으로 정의하는 선언적 언어입니다. DDS에서는 메시지 구조를 정의할 때 사용합니다.

- **역할**: 타입 정의 → IDL 컴파일러(idlc) → C/Python 등 언어별 코드 생성
- **특징**: 강타입, 컴파일 시점 검증, 여러 언어·플랫폼 간 호환

### 1.2 Cyclone DDS idlc

본 프로젝트는 Eclipse Cyclone DDS의 `idlc`로 IDL을 Python 코드로 변환합니다.

```bash
./idls/idl_to_py.sh    # idls/build/에 생성 + pip install -e . 자동 실행
```

> **주의**: IDL 변환은 반드시 `idl_to_py.sh`를 사용하세요. 올바른 출력: `idls/build/`, rpc Python은 `idls/rpc/`에 갱신됨

---

## 2. 작성 규칙

### 2.1 #include는 패키지 경로 기준으로

다른 패키지의 IDL을 참조할 때는 **전체 경로**를 사용하여 애매함을 피합니다.

```idl
#include "std_msgs/msg/Header.idl"   // ✓ 권장
#include "Header.idl"                // ✗ 동일 이름 파일이 여러 개면 혼란
```

### 2.2 파일 기본 구조

권장 구조(ROS/COVESA 스타일):

```idl
/*
 * 라이선스 블록 (선택)
 * Copyright ...
 */

#ifndef __패키지__msg__타입명__idl
#define __패키지__msg__타입명__idl

#include "패키지/경로/파일.idl"   // 의존 타입이 있을 경우

module 패키지 { module msg {

    // 상수, typedef, struct 등

}; };  // module msg::패키지

#endif  // __패키지__msg__타입명__idl
```

| 구성 요소 | 설명 |
|-----------|------|
| **Include Guard** | `#ifndef`/`#define`/`#endif`로 중복 include 방지 |
| **#include** | 참조하는 다른 IDL (패키지 경로 기준 전체 경로 사용) |
| **module** | 네임스페이스. ROS 스타일은 `package.msg` 2단계 사용 |
| **마무리 주석** | `}; };  // module msg::패키지` 형태로 가독성 향상 |

### 2.3 명명 규칙

| 대상 | 규칙 | 예시 |
|------|------|------|
| 파일명 | PascalCase 또는 스네이크. `*.idl` | `HelloWorld.idl`, `NavSatStatus.idl` |
| 모듈 | 소문자, 언더스코어. 하위 `msg` 권장 | `hello_msgs`, `sensor_msgs.msg` |
| struct | PascalCase | `HelloWorld`, `NavSatFix` |
| 멤버 | snake_case | `frame_id`, `position_covariance` |
| 상수 | UPPER_SNAKE | `STATUS_NO_FIX`, `COVARIANCE_TYPE_UNKNOWN` |

### 2.4 주석

- `//` : 한 줄 주석
- `/* ... */` : 블록 주석
- 멤버 단위 설명은 필요 시 추가

---

## 3. 폴더 구조

### 3.1 현재 디렉터리 레이아웃

```
idls/
├── idl_to_py.sh           # 변환 스크립트 (의존성 자동 분석)
├── setup.py               # Python 패키지 설정
├── HelloWorld.idl         # hello_msgs
├── NavSatStatus.idl       # sensor_msgs.msg
├── NavStatFix.idl         # sensor_msgs.msg
├── std_msgs/
│   └── msg/
│       ├── Time.idl       # std_msgs.msg
│       └── Header.idl     # std_msgs.msg
└── build/                 # idlc 출력 (생성됨, .gitignore)
    ├── hello_msgs/
    ├── sensor_msgs/
    └── std_msgs/
```

### 3.2 모듈 vs 폴더

| 패턴 | 폴더 | module | Python import |
|------|------|--------|---------------|
| 단일 모듈 | `idls/HelloWorld.idl` | `module hello_msgs` | `from hello_msgs import HelloWorld` |
| 하위 msg | `idls/std_msgs/msg/Time.idl` | `module std_msgs { module msg` | `from std_msgs.msg import Time` |
| 복수 패키지 | `idls/sensor_msgs/` 없음, 루트에 `.idl` | `sensor_msgs.msg` | `from sensor_msgs.msg import NavSatFix` |

- **단일 모듈**: `idls/` 바로 아래 `.idl` 배치 가능
- **하위 네임스페이스**: `패키지명/msg/` 디렉터리에 `.idl` 배치

---

## 4. 참조 구조

### 4.1 #include

다른 IDL에 정의된 타입을 사용할 때:

```idl
#include "NavSatStatus.idl"        // 같은 검색 경로 내
#include "std_msgs/msg/Header.idl" // 패키지 경로 기준 (권장)
```

- `idl_to_py.sh`는 IDL 파일이 있는 디렉터리와 `idls/` 루트를 `-I`로 자동 설정
- idlc는 `idls/`에서 실행되며 include 경로를 동적으로 구성

### 4.2 모듈 간 타입 참조

```idl
struct NavStatFix {
    std_msgs::msg::Header header;           // 다른 패키지
    sensor_msgs::msg::NavSatStatus status;  // 같은 패키지 내 다른 타입
    double latitude;
    // ...
};
```

- `패키지::msg::타입명` 형식으로 타입 지정
- 사용 전 반드시 해당 IDL을 `#include` 해야 함

### 4.3 의존성 순서

idlc는 **의존 타입이 먼저 변환**되어야 합니다. `idl_to_py.sh`가 `#include`를 파싱해 위상 정렬로 처리 순서를 자동 결정합니다.

```
Time.idl → Header.idl (Time 사용) → NavSatStatus.idl → HelloWorld.idl, NavStatFix.idl
```

---

## 5. 타입 정의

### 5.1 기본 타입 (Primitive)

| IDL 타입 | 설명 | 비고 |
|----------|------|------|
| `short`, `long`, `long long` | 16, 32, 64비트 부호 정수 | |
| `unsigned short`, `unsigned long`, `unsigned long long` | 부호 없는 정수 | |
| `int8`~`int64`, `uint8`~`uint64` | 명시적 비트 크기 | |
| `float`, `double` | 32, 64비트 부동소수 | |
| `char`, `octet` | 문자, 바이트 | |
| `boolean` | 참/거짓 | |

> `int`, `wchar`, `long double`은 Cyclone DDS에서 지원하지 않음.

### 5.2 템플릿 타입

| 타입 | 설명 | 예 |
|------|------|-----|
| `string` | 가변 길이 문자열 | `string msg` |
| `string<N>` | 최대 N자 | `string<256> frame_id` |
| `sequence<T>` | 가변 길이 시퀀스 | `sequence<double> values` |
| `sequence<T,N>` | 최대 N개 | `sequence<octet, 64> data` |

### 5.3 struct

```idl
struct HelloWorld {
    std_msgs::msg::Header header;   // 타임스탬프 등 메타데이터
    string msg;
    long count;
};
```

- 상속 가능: `struct B : A { ... }`
- 배열: `double arr[9]`
- `typedef`로 배열 별칭: `typedef double arr9[9];`

### 5.4 const

```idl
const octet STATUS_NO_FIX = 255;
const octet STATUS_FIX = 0;
```

IDL 내부에서만 사용되며, 런타임 코드로 전달되지는 않습니다.

### 5.5 typedef

```idl
typedef double sensor_msgs__NavSatFix__double_array_9[9];

struct NavSatFix {
    sensor_msgs__NavSatFix__double_array_9 position_covariance;
    // ...
};
```

### 5.6 enum

```idl
enum Status {
    UNKNOWN,
    OK,
    ERROR
};
```

### 5.7 union

```idl
union Data switch (long) {
    case 0: long ival;
    case 1: double dval;
    default: string sval;
};
```

- `switch` 타입: 정수, char, octet, boolean, enum

### 5.8 annotation (XTypes)

| 어노테이션 | 용도 |
|------------|------|
| `@key` | DDS 키 멤버 지정 |
| `@nested` | 토픽 기술자 미생성 (헬퍼 타입용) |
| `@appendable` | 타입 확장성 |
| `@final` | 확장 불가 (기본) |
| `@mutable` | mutable 확장 (struct만) |

예:

```idl
@nested
struct Time {
    long sec;
    unsigned long nanosec;
};
```

---

## 6. idl_to_py.sh 연동

### 6.1 자동 의존성 분석

`idl_to_py.sh`는 **`#include` 기반으로 참조 구조를 자동 파악**합니다.

- 각 IDL에서 `#include "..."` 추출
- include 경로를 .idl이 있는 디렉터리에서 검색해 파일로 해석
- 위상 정렬로 처리 순서 결정 (의존되는 쪽 먼저)
- **순환 참조**나 **존재하지 않는 include** 시 오류 출력 후 종료

→ 새 IDL을 추가해도 스크립트 수정 없이 동작 (단, `#include` 경로가 검색 가능해야 함).

### 6.2 새 IDL 추가 시

1. **파일 위치**: `idls/` 또는 `idls/패키지/msg/` 등
2. **의존성**: 다른 IDL 참조 시 `#include "패키지/경로/파일.idl"` 추가
3. **스크립트 수정**: 불필요 (자동 처리)

### 6.3 오류 예시

| 상황 | 오류 메시지 |
|------|-------------|
| `#include "없는파일.idl"` | `오류: 다음 include를 찾을 수 없습니다:` + 파일 목록 |
| A→B→A 순환 참조 | `오류: 순환 참조가 있습니다:` + 관련 파일 목록 |

### 6.4 Extensibility (`-x`)

- `appendable`: 타입 확장 허용 (기본 사용)
- `final`: 확장 불가, 비 XTypes DDS와 호환

---

## 7. 전체 예시

### 7.1 단순 메시지 (HelloWorld.idl)

```idl
// HelloWorld.idl
#include "std_msgs/msg/Header.idl"

module hello_msgs {

struct HelloWorld {
    std_msgs::msg::Header header;
    string msg;
    long count;
};

};
```

### 7.2 의존성이 있는 메시지 (NavStatFix.idl)

```idl
#ifndef __sensor_msgs__msg__NavStatFix__idl
#define __sensor_msgs__msg__NavStatFix__idl

#include "NavSatStatus.idl"
#include "std_msgs/msg/Header.idl"

module sensor_msgs { module msg {

typedef double sensor_msgs__NavSatFix__double_array_9[9];

struct NavStatFix {
    std_msgs::msg::Header header;
    sensor_msgs::msg::NavSatStatus status;
    double latitude;
    double longitude;
    double altitude;
    sensor_msgs__NavSatFix__double_array_9 position_covariance;
    octet position_covariance_type;
};

}; };  // module msg::sensor_msgs

#endif
```

---

## 8. 참고 자료

- [Cyclone DDS - Supported IDL](https://cyclonedds.io/content/guides/supported-idl.html)
- [OMG IDL Specification](https://www.omg.org/spec/IDL/)
- [DDS-XTypes](https://www.omg.org/spec/DDS-XTypes/)
- [ROS 2 Message/Service IDL](https://docs.ros.org/en/rolling/Concepts/About-ROS-Interfaces.html)
