"""
SDK 패키지 설치 설정

RPC SDK(sdk/rpc) + PubSub SDK(sdk/pubsub)를 설치합니다.

사용:
  pip install -e .          # sdk/ 디렉터리에서 실행
  pip install -e ./sdk      # 프로젝트 루트에서 실행
"""

from setuptools import setup

setup(
    name="sdm-dds-rpc",
    version="0.1.0",
    description="DDS 기반 RPC 및 PubSub SDK",
    python_requires=">=3.8",
    install_requires=["cyclonedds"],
    packages=["sdm_dds_rpc", "sdm_dds_pubsub"],
    package_dir={"sdm_dds_rpc": "rpc", "sdm_dds_pubsub": "pubsub"},
)
