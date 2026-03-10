"""
idlc로 생성된 Python 메시지 패키지를 pip 설치 가능하게 합니다.
idl_to_py.sh 실행 시 build/에 생성, pip install . 로 설치
"""

from pathlib import Path

from setuptools import setup, find_packages

# idlc 출력: idls/build/
build_dir = Path(__file__).parent / "build"
packages = find_packages(where=str(build_dir)) if build_dir.exists() else []
if not packages:
    packages = ["hello_msgs"]  # build 없을 때 기본값

setup(
    name="sdm-dds-idls",
    description="DDS 메시지 클래스 (idlc로 IDL에서 생성)",
    packages=packages,
    package_dir={"": "build"},
)
