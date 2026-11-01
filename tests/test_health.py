"""健康检查：所有其它用例的前提，跑挂了这个，先别看别的问题。"""
from core.assertions import expect_json, expect_keys, expect_status


def test_health_ok(api):
    resp = api.get("/api/health")
    expect_status(resp, 200)
    body = expect_json(resp)
    expect_keys(body, "status", "service", "version")
    assert body["status"] == "ok"
