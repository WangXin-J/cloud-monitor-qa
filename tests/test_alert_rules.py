"""告警规则：增删查 + 参数边界 + 幂等性。

告警规则是「会真的发出通知」的功能，边界比正常路径重要得多：
阈值等于边界值算不算触发、重复创建会不会产生两条规则、删两次会不会 500 ——
这几类问题线上代价最高，所以用例优先覆盖它们。
"""
import pytest

from core.assertions import expect_error, expect_json, expect_keys, expect_status
from core.data import drop, rule_payload, unique_name


# ---------------- 创建 ----------------
def test_create_rule_ok(api, created_rule):
    expect_keys(created_rule, "id", "name", "metric", "operator", "threshold", "level", "enabled")
    assert created_rule["enabled"] is True
    assert created_rule["threshold"] == 90


@pytest.mark.parametrize("missing", ["name", "metric", "operator", "threshold"])
def test_create_missing_required(api, missing):
    payload = drop(rule_payload(), missing)
    expect_error(api.post("/api/alert/rules", json=payload), 400, "INVALID_PARAM")


def test_create_invalid_metric(api):
    expect_error(api.post("/api/alert/rules", json=rule_payload(metric="gpu")), 400, "INVALID_PARAM")


def test_create_invalid_operator(api):
    expect_error(api.post("/api/alert/rules", json=rule_payload(operator="==")), 400, "INVALID_PARAM")


@pytest.mark.parametrize("threshold", [-1, 101, "abc"])
def test_create_threshold_out_of_range(api, threshold):
    expect_error(api.post("/api/alert/rules", json=rule_payload(threshold=threshold)),
                 400, "INVALID_PARAM")


@pytest.mark.parametrize("threshold", [0, 100])
def test_create_threshold_boundary_ok(api, threshold):
    """0 和 100 是合法边界，不能因为「等于」被当成非法值拒掉。"""
    resp = api.post("/api/alert/rules", json=rule_payload(threshold=threshold))
    expect_status(resp, 201)
    rule = expect_json(resp)
    assert rule["threshold"] == threshold
    api.delete(f"/api/alert/rules/{rule['id']}")


def test_create_duplicate_name(api, created_rule):
    expect_error(api.post("/api/alert/rules", json=rule_payload(name=created_rule["name"])),
                 409, "DUPLICATE_NAME")


def test_create_name_too_long(api):
    expect_error(api.post("/api/alert/rules", json=rule_payload(name="x" * 33)),
                 400, "INVALID_PARAM")


# ---------------- 查询 ----------------
def test_list_contains_created(api, created_rule):
    resp = api.get("/api/alert/rules")
    expect_status(resp, 200)
    body = expect_json(resp)
    expect_keys(body, "total", "items")
    ids = [item["id"] for item in body["items"]]
    assert created_rule["id"] in ids, f"刚创建的规则 {created_rule['id']} 没出现在列表里"


# ---------------- 删除 ----------------
def test_delete_ok(api):
    rule = expect_json(api.post("/api/alert/rules", json=rule_payload(name=unique_name("tmp"))))
    expect_status(api.get("/api/alert/rules"), 200)
    expect_status(api.delete(f"/api/alert/rules/{rule['id']}"), 204)
    ids = [item["id"] for item in expect_json(api.get("/api/alert/rules"))["items"]]
    assert rule["id"] not in ids


def test_delete_twice(api):
    """幂等性：删两次，第二次应该是 404，不是 500。"""
    rule = expect_json(api.post("/api/alert/rules", json=rule_payload(name=unique_name("idem"))))
    expect_status(api.delete(f"/api/alert/rules/{rule['id']}"), 204)
    expect_error(api.delete(f"/api/alert/rules/{rule['id']}"), 404, "RULE_NOT_FOUND")


def test_delete_unknown(api):
    expect_error(api.delete("/api/alert/rules/r-does-not-exist"), 404, "RULE_NOT_FOUND")


# ---------------- 事件 ----------------
def test_events_after_create(api, created_rule):
    resp = api.get("/api/alert/events", params={"ruleId": created_rule["id"]})
    expect_status(resp, 200)
    body = expect_json(resp)
    expect_keys(body, "total", "items")
    assert all(e["ruleId"] == created_rule["id"] for e in body["items"])
