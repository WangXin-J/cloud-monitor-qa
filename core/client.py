"""HTTP 客户端封装：统一超时、日志、耗时统计。

用例里不要直接 import requests，走这里，好处是：
- 换认证方式（token / cookie）只改一处
- 每个请求都有日志和耗时，出问题能定位
"""
from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger("qa.api")


class ApiClient:
    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "cloud-monitor-qa/1.0",
        })

    def request(self, method: str, path: str, *, params=None, json=None, data=None):
        url = f"{self.base_url}{path}"
        started = time.perf_counter()
        response = self.session.request(
            method, url, params=params, json=json, data=data, timeout=self.timeout
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        log.info("%-6s %s -> %s (%.0f ms)", method, url, response.status_code, elapsed_ms)
        return response

    def get(self, path: str, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs):
        return self.request("POST", path, **kwargs)

    def delete(self, path: str, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def close(self):
        self.session.close()
