#!/bin/bash
# SDM-DDS 프로젝트 환경 활성화 스크립트
# 사용법: source activate_env.sh
# (또는 . activate_env.sh)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CYCLONEDDS_HOME="${SCRIPT_DIR}/cyclonedds/install"
export PATH="${CYCLONEDDS_HOME}/bin:${PATH}"
export LD_LIBRARY_PATH="${CYCLONEDDS_HOME}/lib:${LD_LIBRARY_PATH}"
source "${SCRIPT_DIR}/venv/bin/activate"
echo "가상환경 활성화됨. CYCLONEDDS_HOME=${CYCLONEDDS_HOME}"
