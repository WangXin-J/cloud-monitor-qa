"""测试数据工厂：所有请求体集中在这里，改字段只改一处。"""
from __future__ import annotations

import itertools
import time

_host_seq = itertools.count(1)


def unique_name(prefix: str = "rule") -> str:
    return f"{prefix}-{int(time.time() * 1000)}-{next(_host_seq)}"


def rule_payload(**overrides) -> dict:
    payload = {
        "name": unique_name(),
        "metric": "cpu",
        "operator": ">",
        "threshold": 90,
        "level": "P1",
        "silenceSeconds": 300,
    }
    payload.update(overrides)
    return payload


def drop(payload: dict, *keys: str) -> dict:
    """复制一份并删掉指定字段，用于必填校验用例。"""
    copied = dict(payload)
    for key in keys:
        copied.pop(key, None)
    return copied
