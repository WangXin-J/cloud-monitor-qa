"""契约测试：响应格式的统一约束。

单独放一个文件，是因为这类问题一旦破坏，会同时影响所有调用方（前端、告警机器人、
第三方集成），比单个字段对不上严重得多。
"""
import time

from core.assertions import expect_json, expect_status


def test_error_is_json(api):
    resp = api.get("/api/metrics/current")
    expect_status(resp, 400)
    assert "application/json" in resp.headers.get("Content-Type", ""), \
        f"错误响应必须是 JSON，实际 Content-Type={resp.headers.get('Content-Type')}"


def test_error_body_shape(api):
    """所有错误响应统一 {code, message}，前端才能做统一提示。"""
    for resp in (
        api.get("/api/metrics/current"),
        api.get("/api/metrics/current", params={"hostId": "h-999"}),
        api.get("/api/not-exist"),
    ):
        body = expect_json(resp)
        assert set(body) >= {"code", "message"}, f"错误体结构不符: {body}"
        assert isinstance(body["message"], str) and body["message"], "message 不能为空"


def test_current_timestamp_is_fresh(api):
    """时间戳必须是毫秒级且接近当前时间 —— 单位写错（秒 vs 毫秒）会导致
    前端图表整体错位，但接口本身不会报错，属于典型「静默缺陷」。"""
    body = expect_json(api.get("/api/metrics/current", params={"hostId": "h1"}))
    now_ms = int(time.time() * 1000)
    assert abs(now_ms - body["timestamp"]) < 5000, \
        f"timestamp 与当前时间偏差过大: {body['timestamp']} vs {now_ms}"
