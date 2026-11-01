"""cloud-monitor 演示服务（Mock Target）

用途：让自动化用例在**没有你的真实服务**时也能跑起来，产出一份能截图的报告。
接真实服务时，把 CM_BASE_URL 指向你的服务即可，本文件不需要动。

只用标准库，不额外装依赖。
    python mock/app.py            # 默认 127.0.0.1:8009
    python mock/app.py 9000       # 指定端口
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOSTS = {"h1": "web-01", "h2": "web-02"}
METRICS = ("cpu", "mem", "disk", "net")
OPERATORS = (">", "<", ">=", "<=")
LEVELS = ("P1", "P2", "P3")
MAX_PAGE_SIZE = 100
HISTORY_TOTAL = 200

RULES: "dict[str, dict]" = {}
SEQ = {"n": 0}


def _one(query: "dict[str, list[str]]", key: str):
    values = query.get(key)
    if not values:
        return None
    return values[0]


def _to_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"参数不是整数: {value}")


def _err(code: str, message: str):
    return {"code": code, "message": message}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # 静默日志，避免干扰 pytest 输出
        pass

    # ---------- 基础 ----------
    def _send(self, status: int, payload=None):
        body = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _fail(self, status: int, code: str, message: str):
        self._send(status, _err(code, message))

    # ---------- GET ----------
    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)

        if url.path == "/api/health":
            return self._send(200, {
                "status": "ok",
                "service": "cloud-monitor-mock",
                "version": "1.0.0",
                "uptimeSeconds": int(time.time() - STARTED_AT),
            })

        if url.path == "/api/metrics/current":
            return self._current(query)

        if url.path == "/api/metrics/history":
            return self._history(query)

        if url.path == "/api/alert/rules":
            items = list(RULES.values())
            return self._send(200, {"total": len(items), "items": items})

        if url.path == "/api/alert/events":
            rule_id = _one(query, "ruleId")
            events = [e for e in EVENTS if rule_id is None or e["ruleId"] == rule_id]
            return self._send(200, {"total": len(events), "items": events})

        return self._fail(404, "NOT_FOUND", f"接口不存在: {url.path}")

    def _current(self, query):
        host_id = _one(query, "hostId")
        if not host_id:
            return self._fail(400, "INVALID_PARAM", "hostId 必填")
        if host_id not in HOSTS:
            return self._fail(404, "HOST_NOT_FOUND", f"主机不存在: {host_id}")

        seed = int(time.time()) % 97
        metrics = {
            "cpu": round((seed % 60) + 5.5, 1),
            "mem": round((seed % 70) + 20.0, 1),
            "disk": 71.0,
            "net": round((seed % 30) / 10.0, 2),
        }
        return self._send(200, {
            "hostId": host_id,
            "hostName": HOSTS[host_id],
            "timestamp": int(time.time() * 1000),
            "metrics": metrics,
        })

    def _history(self, query):
        host_id = _one(query, "hostId")
        if not host_id:
            return self._fail(400, "INVALID_PARAM", "hostId 必填")
        if host_id not in HOSTS:
            return self._fail(404, "HOST_NOT_FOUND", f"主机不存在: {host_id}")

        metric = _one(query, "metric")
        if metric not in METRICS:
            return self._fail(400, "INVALID_PARAM", f"metric 非法: {metric}，可选 {list(METRICS)}")

        try:
            start = _to_int(_one(query, "start"))
            end = _to_int(_one(query, "end"))
            page = _to_int(_one(query, "page"))
            size = _to_int(_one(query, "size"))
        except ValueError as exc:
            return self._fail(400, "INVALID_PARAM", str(exc))

        # 注意：不能用 `or 1` 兜底，否则 page=0 / size=0 会被悄悄改成默认值，
        # 非法参数就变成合法请求了 —— 这正是要防的那类缺陷。
        if page is None:
            page = 1
        if size is None:
            size = 20

        if start is not None and end is not None and start > end:
            return self._fail(400, "INVALID_PARAM", "start 不能大于 end")
        if page < 1:
            return self._fail(400, "INVALID_PARAM", "page 从 1 开始")
        if size < 1 or size > MAX_PAGE_SIZE:
            return self._fail(400, "INVALID_PARAM", f"size 取值范围 1..{MAX_PAGE_SIZE}")

        base = end or int(time.time())
        offset = (page - 1) * size
        items = []
        for i in range(size):
            seq = offset + i
            if seq >= HISTORY_TOTAL:
                break
            items.append({
                "ts": base - (seq * 60),
                "value": round(10 + (seq % 50) * 0.8, 1),
            })
        return self._send(200, {
            "hostId": host_id,
            "metric": metric,
            "page": page,
            "size": size,
            "total": HISTORY_TOTAL,
            "items": items,
        })

    # ---------- POST ----------
    def do_POST(self):
        url = urlparse(self.path)
        if url.path != "/api/alert/rules":
            return self._fail(404, "NOT_FOUND", f"接口不存在: {url.path}")

        raw = b""
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._fail(400, "INVALID_JSON", "请求体不是合法 JSON")
        if not isinstance(data, dict):
            return self._fail(400, "INVALID_JSON", "请求体必须是 JSON 对象")

        problem = self._validate_rule(data)
        if problem:
            return self._fail(400, "INVALID_PARAM", problem)

        if any(rule["name"] == data["name"] for rule in RULES.values()):
            return self._fail(409, "DUPLICATE_NAME", f"规则名已存在: {data['name']}")

        SEQ["n"] += 1
        rule = {
            "id": "r-%d" % SEQ["n"],
            "name": data["name"],
            "metric": data["metric"],
            "operator": data["operator"],
            "threshold": data["threshold"],
            "level": data.get("level", "P2"),
            "silenceSeconds": data.get("silenceSeconds", 300),
            "enabled": True,
            "createdAt": int(time.time() * 1000),
        }
        RULES[rule["id"]] = rule
        EVENTS.append({"ruleId": rule["id"], "ts": int(time.time() * 1000), "value": data["threshold"], "level": rule["level"]})
        return self._send(201, rule)

    @staticmethod
    def _validate_rule(data: dict):
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            return "name 必填且为非空字符串"
        if len(name) > 32:
            return "name 长度不能超过 32"
        if data.get("metric") not in METRICS:
            return f"metric 非法，可选 {list(METRICS)}"
        if data.get("operator") not in OPERATORS:
            return f"operator 非法，可选 {list(OPERATORS)}"
        threshold = data.get("threshold")
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
            return "threshold 必须是数字"
        if threshold < 0 or threshold > 100:
            return "threshold 取值范围 0..100"
        if data.get("level") is not None and data["level"] not in LEVELS:
            return f"level 非法，可选 {list(LEVELS)}"
        silence = data.get("silenceSeconds")
        if silence is not None and (not isinstance(silence, int) or silence < 0):
            return "silenceSeconds 必须是非负整数"
        return None

    # ---------- DELETE ----------
    def do_DELETE(self):
        url = urlparse(self.path)
        prefix = "/api/alert/rules/"
        if not url.path.startswith(prefix):
            return self._fail(404, "NOT_FOUND", f"接口不存在: {url.path}")
        rule_id = url.path[len(prefix):]
        if rule_id not in RULES:
            return self._fail(404, "RULE_NOT_FOUND", f"规则不存在: {rule_id}")
        RULES.pop(rule_id)
        return self._send(204, None)


STARTED_AT = time.time()
EVENTS: "list[dict]" = []


def main():
    port = 8009
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    port = int(os.getenv("CM_PORT", port))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"cloud-monitor mock listening on http://127.0.0.1:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
