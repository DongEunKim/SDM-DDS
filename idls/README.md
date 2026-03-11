# idls

IDL 정의와 빌드 산출물이 모여 있는 디렉터리입니다. RPC SDK는 `sdk/rpc/`에 별도로 있습니다.

## 구조

| 경로 | 설명 |
|------|------|
| `rpc/` | RPC 공통 타입 (IDL + idlc 생성 Python) |
| `services/` | RPC 서비스 IDL (Add, Calculate 등) |
| `build/` | idlc 빌드 산출물. `idl_to_py.sh` 실행 시 생성 |

## 빌드

```bash
./idl_to_py.sh
```

- 모든 IDL → Python 변환
- `rpc` Python을 `idls/rpc/`에 갱신
- `pip install -e .` (루트 통합 패키지) 자동 실행
