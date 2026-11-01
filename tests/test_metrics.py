"""指标接口：正常路径 + 参数校验 + 分页边界。

思考方式：先把「接口应该怎么回应」写成契约，再用用例逐条钉住。
参数校验用例占一半是刻意的 —— 线上 80% 的缺陷出在异常入参上。
"""
import time

import pytest

from core.assertions import expect_between, expect_error, expect_json, expect_keys, expect_status

METRICS = ["cpu", "mem", "disk", "net"]


# ---------------- 实时指标 ----------------
def test_current_ok(api):
    resp = api.get("/api/metrics/current", params={"hostId": "h1"})
    expect_status(resp, 200)
    body = expect_json(resp)
    expect_keys(body, "hostId", "hostName", "timestamp", "metrics")
    assert body["hostId"] == "h1"
    expect_keys(body["metrics"], *METRICS)


def test_current_missing_host(api):
    expect_error(api.get("/api/metrics/current"), 400, "INVALID_PARAM")


def test_current_unknown_host(api):
    expect_error(api.get("/api/metrics/current", params={"hostId": "h-999"}), 404, "HOST_NOT_FOUND")


def test_current_metrics_in_range(api):
    """指标必须落在物理上有意义的区间，越界说明采集逻辑算错了。"""
    body = expect_json(api.get("/api/metrics/current", params={"hostId": "h2"}))
    metrics = body["metrics"]
    expect_between(metrics["cpu"], 0, 100, "cpu")
    expect_between(metrics["mem"], 0, 100, "mem")
    expect_between(metrics["disk"], 0, 100, "disk")
    assert metrics["net"] >= 0, f"net 不能为负: {metrics['net']}"


# ---------------- 历史指标 ----------------
def test_history_default_paging(api):
    resp = api.get("/api/metrics/history", params={"hostId": "h1", "metric": "cpu"})
    expect_status(resp, 200)
    body = expect_json(resp)
    expect_keys(body, "total", "page", "size", "items")
    assert body["page"] == 1
    assert body["size"] == 20
    assert len(body["items"]) <= body["size"]


def test_history_missing_host(api):
    expect_error(api.get("/api/metrics/history", params={"metric": "cpu"}), 400, "INVALID_PARAM")


@pytest.mark.parametrize("metric", ["gpu", "CPU", "cpu ", ""])
def test_history_invalid_metric(api, metric):
    expect_error(api.get("/api/metrics/history", params={"hostId": "h1", "metric": metric}),
                 400, "INVALID_PARAM")


def test_history_time_reversed(api):
    now = int(time.time())
    expect_error(
        api.get("/api/metrics/history", params={
            "hostId": "h1", "metric": "cpu", "start": now, "end": now - 3600,
        }),
        400, "INVALID_PARAM",
    )


@pytest.mark.parametrize("size", [0, -1, 101, 1000])
def test_history_size_out_of_range(api, size):
    expect_error(
        api.get("/api/metrics/history", params={"hostId": "h1", "metric": "cpu", "size": size}),
        400, "INVALID_PARAM",
    )


def test_history_page_zero(api):
    expect_error(
        api.get("/api/metrics/history", params={"hostId": "h1", "metric": "cpu", "page": 0}),
        400, "INVALID_PARAM",
    )


def test_history_beyond_last_page(api):
    """翻页翻过头应该是空列表，而不是报错、也不该返回上一页的数据。"""
    resp = api.get("/api/metrics/history", params={"hostId": "h1", "metric": "cpu", "page": 999, "size": 20})
    expect_status(resp, 200)
    body = expect_json(resp)
    assert body["items"] == [], f"越界页应返回空列表，实际返回 {len(body['items'])} 条"


@pytest.mark.parametrize("metric", METRICS)
def test_history_all_metrics(api, metric):
    resp = api.get("/api/metrics/history", params={"hostId": "h1", "metric": metric, "size": 5})
    expect_status(resp, 200)
    body = expect_json(resp)
    assert len(body["items"]) == 5
    for item in body["items"]:
        expect_keys(item, "ts", "value")
