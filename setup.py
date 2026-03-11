"""
프로젝트 루트 setup.py - pyproject.toml과 함께 사용

idls/build 패키지(rpc, sensor_msgs 등) + sdk/rpc(sdm_dds_rpc)를 통합 설치합니다.
"""
from setuptools import find_packages, setup

# idlc 출력 + sdm_dds_rpc (sdk/rpc) + sdm_dds_pubsub (sdk/pubsub)
idlc_packages = find_packages("idls/build", include=["rpc", "sensor_msgs", "std_msgs", "services", "hello_msgs"])
all_packages = idlc_packages + ["sdm_dds_rpc", "sdm_dds_pubsub"]
package_dir = {
    "": "idls/build",
    "sdm_dds_rpc": "sdk/rpc",
    "sdm_dds_pubsub": "sdk/pubsub",
}

setup(packages=all_packages, package_dir=package_dir)
