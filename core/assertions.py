"""断言小工具。

每条断言都带上响应体片段 —— 失败时一眼能看出是代码问题还是服务问题，
这是自动化用例最基本的可用性要求。
"""
from __future__ import annotations

SNIPPET = 300


def _body(resp) -> str:
    text = (resp.text or "").replace("\n", " ")
    return text[:SNIPPET]


def expect_status(resp, expected: int):
    assert resp.status_code == expected, (
        f"期望状态码 {expected}，实际 {resp.status_code}\n"
        f"URL: {resp.request.method} {resp.request.url}\n"
        f"响应: {_body(resp)}"
    )
    return resp


def expect_json(resp) -> dict:
    try:
        return resp.json()
    except ValueError:
        raise AssertionError(f"响应不是合法 JSON: {_body(resp)}") from None


def expect_keys(payload: dict, *keys: str):
    missing = [k for k in keys if k not in payload]
    assert not missing, f"响应缺少字段 {missing}，实际字段 {list(payload)}"


def expect_error(resp, status: int, code: str | None = None):
    expect_status(resp, status)
    body = expect_json(resp)
    expect_keys(body, "code", "message")
    if code is not None:
        assert body["code"] == code, f"错误码不符：期望 {code}，实际 {body['code']}"
    return body


def expect_between(value, low, high, label="值"):
    assert low <= value <= high, f"{label} 应在 [{low}, {high}] 之间，实际 {value}"
