"""
동적 타입 발견 유틸리티

DCPSPublication/DCPSSubscription에서 토픽 타입을 조회합니다.
"""

import time
from typing import Any, Optional

from cyclonedds.domain import DomainParticipant
from cyclonedds.builtin import BuiltinTopicDcpsPublication, BuiltinTopicDcpsSubscription
from cyclonedds.builtin import BuiltinDataReader
from cyclonedds.dynamic import get_types_for_typeid
from cyclonedds.core import ReadCondition, ViewState, InstanceState, SampleState
from cyclonedds.util import duration


def discover_datatype(
    participant: DomainParticipant,
    topic_name: str,
    timeout_sec: float = 10.0,
) -> Optional[Any]:
    """
    DCPSPublication/DCPSSubscription에서 토픽에 대한 타입을 발견합니다.

    Args:
        participant: DomainParticipant
        topic_name: 조회할 토픽 이름
        timeout_sec: discovery 대기 시간(초)

    Returns:
        발견된 타입, 없으면 None

    Raises:
        ConfigurationError: timeout_sec <= 0
    """
    if timeout_sec <= 0:
        from sdm_dds_pubsub.exceptions import ConfigurationError
        raise ConfigurationError(
            f"timeout_sec는 양수여야 합니다. (현재: {timeout_sec})"
        )

    rd_pub = BuiltinDataReader(participant, BuiltinTopicDcpsPublication)
    rc_pub = ReadCondition(
        rd_pub, SampleState.NotRead | ViewState.Any | InstanceState.Alive
    )
    rd_sub = BuiltinDataReader(participant, BuiltinTopicDcpsSubscription)
    rc_sub = ReadCondition(
        rd_sub, SampleState.NotRead | ViewState.Any | InstanceState.Alive
    )

    poll_count = int(timeout_sec * 250)  # 4ms 간격
    for _ in range(poll_count):
        for pub in rd_pub.take(N=20, condition=rc_pub):
            if pub.topic_name == topic_name and pub.type_id is not None:
                datatype, _ = get_types_for_typeid(
                    participant, pub.type_id, duration(seconds=5)
                )
                return datatype
        for sub in rd_sub.take(N=20, condition=rc_sub):
            if sub.topic_name == topic_name and sub.type_id is not None:
                datatype, _ = get_types_for_typeid(
                    participant, sub.type_id, duration(seconds=5)
                )
                return datatype
        time.sleep(0.004)

    return None
