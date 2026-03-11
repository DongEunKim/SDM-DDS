#!/bin/bash
# idl_to_py.sh
# IDL 파일을 Cyclone DDS idlc로 Python 코드로 변환합니다.
# - #include 기반 참조 구조 자동 파악, 위상 정렬 후 변환
# - 순환 참조/해당 없는 include 시 오류 출력
#
# 사용법:
#   ./idl_to_py.sh              # idls/ 변환 + pip install -e . (통합 패키지) 자동 실행
#   ./idl_to_py.sh <IDL_DIR>    # 지정 폴더 변환 + pip 설치
#
# 출력: idls/build/
# 사용: pip install . (idls/에서) 후 from sensor_msgs.msg import NavSatFix 등
#
# IDL 작성 규칙: #include는 패키지 경로 기준으로 작성 (예: "std_msgs/msg/Header.idl")

set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_IDL_DIR="${SCRIPT_DIR}"
CYCLONEDDS_HOME="${PROJECT_ROOT}/cyclonedds/install"

if [[ -n "${1:-}" ]]; then
    if [[ -d "${1}" ]]; then
        IDL_DIR="$(cd "${1}" && pwd)"
    else
        echo "오류: 지정한 경로가 디렉터리가 아니거나 존재하지 않습니다: ${1}" >&2
        exit 1
    fi
else
    IDL_DIR="${DEFAULT_IDL_DIR}"
fi

export CYCLONEDDS_HOME
export PATH="${CYCLONEDDS_HOME}/bin:${PATH}"

if [[ ! -d "${CYCLONEDDS_HOME}" ]]; then
    echo "오류: Cyclone DDS가 설치되지 않았습니다. (${CYCLONEDDS_HOME})" >&2
    exit 1
fi

if [[ ! -d "${IDL_DIR}" ]]; then
    echo "오류: IDL 디렉터리가 없습니다. (${IDL_DIR})" >&2
    exit 1
fi

# 출력 디렉터리: idls/build/ (매 실행 시 초기화)
BUILD_DIR="${IDL_DIR}/build"
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"

EXTENSIBILITY="-x appendable"

# 참조 구조 자동 파악: #include 기반 의존성 분석 및 위상 정렬
export IDL_DIR
idl_ordered="$(
python3 << 'PYEOF'
import os
import re
import sys
from collections import deque

idl_dir = os.environ.get("IDL_DIR", ".")
idl_dir = os.path.abspath(idl_dir)

# 모든 .idl 파일 (IDL_DIR 기준 상대 경로, build/ 제외)
all_idls = []
for root, dirs, files in os.walk(idl_dir):
    dirs[:] = [d for d in dirs if d != "build"]
    for f in files:
        if f.endswith(".idl"):
            path = os.path.join(root, f)
            rel = os.path.relpath(path, idl_dir)
            all_idls.append(rel)

# include 검색 경로: idl_dir 및 .idl이 있는 하위 디렉터리
search_dirs = ["."]
for rel in all_idls:
    d = os.path.dirname(rel)
    if d and d not in search_dirs:
        search_dirs.append(d)
search_dirs = sorted(set(search_dirs), key=lambda x: (x.count("/"), x))

def resolve_include(inc_path):
    """#include 경로를 실제 파일 경로(IDL_DIR 기준 상대)로 변환"""
    inc_path = inc_path.strip().strip('"\'')
    for sd in search_dirs:
        candidate = os.path.normpath(os.path.join(sd, inc_path))
        full = os.path.join(idl_dir, candidate)
        if os.path.isfile(full):
            return candidate
    return None

def get_includes(rel_path):
    """IDL 파일에서 #include 추출"""
    full = os.path.join(idl_dir, rel_path)
    if not os.path.isfile(full):
        return []
    with open(full, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    matches = re.findall(r'#include\s+["\']([^"\']+)["\']', content)
    return matches

# 의존성 그래프: file -> [deps]
deps = {f: [] for f in all_idls}
unresolved = []

for rel in all_idls:
    for inc in get_includes(rel):
        resolved = resolve_include(inc)
        if resolved:
            if resolved != rel and resolved not in deps[rel]:
                deps[rel].append(resolved)
        else:
            unresolved.append((rel, inc))

if unresolved:
    print("오류: 다음 include를 찾을 수 없습니다:", file=sys.stderr)
    for f, inc in unresolved:
        print(f"  {f}: #include \"{inc}\"", file=sys.stderr)
    sys.exit(1)

# 위상 정렬 (Kahn): A가 B를 include하면 B가 먼저 와야 함
# pred[d] = A들 (A가 d를 참조). B 출력 시 B를 참조하는 A들의 남은 의존 개수 감소
pred = {f: [] for f in all_idls}
for f in all_idls:
    for d in deps[f]:
        pred[d].append(f)

in_degree = {f: len(deps[f]) for f in all_idls}
queue = deque(f for f in all_idls if in_degree[f] == 0)
result = []

while queue:
    n = queue.popleft()
    result.append(n)
    for p in pred[n]:
        in_degree[p] -= 1
        if in_degree[p] == 0:
            queue.append(p)

if len(result) != len(all_idls):
    cycle_candidates = [f for f in all_idls if f not in result]
    print("오류: 순환 참조가 있습니다:", file=sys.stderr)
    for f in cycle_candidates:
        print(f"  {f}", file=sys.stderr)
    sys.exit(1)

print(" ".join(result))
PYEOF
)" || {
    echo "의존성 분석 실패" >&2
    exit 1
}

# include 경로: IDL 위치의 디렉터리들 + . (루트). 구체 경로를 먼저 두어 동일폴더/상대 include 정상 해석
include_dirs=""
for rel in $idl_ordered; do
    dir="${rel%/*}"
    if [[ -n "${dir}" && "${dir}" != "${rel}" ]]; then
        include_dirs="${include_dirs} ${dir}"
    fi
done
# 구체 경로 먼저(깊은 순), 마지막에 . 추가
include_dirs=$(echo "$include_dirs" | tr ' ' '\n' | sort -u | awk '{print length, $0}' | sort -rn | cut -d' ' -f2-)
include_dirs="${include_dirs} ."
INCLUDE_OPTS=""
for d in $include_dirs; do
    INCLUDE_OPTS="${INCLUDE_OPTS} -I ${d}"
done

echo "[의존성 순서] $idl_ordered"
echo ""

converted=0
cd "${IDL_DIR}"
for rel in $idl_ordered; do
    src="${IDL_DIR}/${rel}"
    if [[ -f "${src}" ]]; then
        echo "변환 중: ${rel}"
        idlc -l py -o build ${INCLUDE_OPTS} ${EXTENSIBILITY} "${rel}"
        ((converted++)) || true
    fi
done

if [[ "${converted}" -eq 0 ]]; then
    echo "경고: 변환된 .idl 파일이 없습니다." >&2
    exit 0
fi

# idlc -o build 는 Python 출력에 적용되지 않음. 생성된 패키지를 build/로 이동
# idlc가 IDL module에 따라 디렉터리 생성 (sensor_msgs, std_msgs 등) → __init__.py 있는 하위 디렉터리 기준
# sdm_dds_rpc는 SDK(sdk/rpc)에 있으므로 idls/ 이동 대상에서 제외
for d in "${IDL_DIR}"/*/; do
    pkg=$(basename "$d")
    [[ "$pkg" == "build" ]] && continue
    [[ "$pkg" == "sdm_dds_rpc" ]] && continue
    if [[ -f "${d}__init__.py" ]]; then
        mv "$d" "${BUILD_DIR}/"
    fi
done

# .idl 소스 파일을 idls/로 복원 (build에는 생성된 .py만 남김)
while IFS= read -r -d '' f; do
    rel="${f#${BUILD_DIR}/}"
    dest="${IDL_DIR}/${rel}"
    mkdir -p "$(dirname "${dest}")"
    mv "$f" "$dest"
done < <(find "${BUILD_DIR}" -name "*.idl" -print0 2>/dev/null)

# RPC 서비스 네임스페이스 후처리 (Add.Request, Add.Reply 등)
if python3 "${SCRIPT_DIR}/add_service_namespaces.py" "${BUILD_DIR}"; then
    :
fi

# rpc: build 출력을 idls/rpc에 복사 (IDL과 Python이 idls/rpc에 함께 위치)
if [[ -d "${BUILD_DIR}/rpc" ]]; then
    cp -f "${BUILD_DIR}"/rpc/*.py "${IDL_DIR}/rpc/"
    echo "  [후처리] rpc Python -> idls/rpc/"
fi

echo ""
echo "완료. 출력: ${BUILD_DIR}"

# 통합 패키지 설치 (pip install -e . 한 번에 sdk + idlc 출력 포함)
echo "패키지 설치 중..."
if python3 -m pip install -e "${PROJECT_ROOT}"; then
    echo "패키지 설치 완료: sdm-dds-rpc (sdk + idls 통합)"
else
    echo "패키지 설치 실패. 수동: pip install -e ." >&2
fi
