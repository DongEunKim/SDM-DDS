# idls와 SDK 분리

## 개요

`idls/`는 IDL 전용, `packages/`는 SDK 전용으로 역할을 분리합니다.

## 구조

| 디렉터리 | 역할 | 포함 내용 |
|----------|------|-----------|
| **idls/** | IDL 전용 | IDL 소스, idl_to_py.sh, idlc 출력(build/) |
| **sdk/** | SDK 전용 | sdk/rpc (client, server, exceptions), setup.py |

## 분리 원칙

1. **idls/**  
   - IDL 작성, 변환, 생성된 Python 메시지 타입만 관리  
   - 런타임 구현(SDK) 포함하지 않음  

2. **packages/**  
   - RPC 요청-응답 프레임워크 구현  
   - idlc 결과와 독립적으로 관리 가능  

3. **통합 설치**  
   - `pip install -e .` 한 번으로 SDK + idlc 출력을 함께 설치  
   - sdm-dds-idls 별도 패키지는 사용하지 않음  
