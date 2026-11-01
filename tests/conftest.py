"""pytest 公共夹具。

默认行为：如果 127.0.0.1:8009 上没有服务，自动拉起 mock/app.py。
接你的真实服务只需要设置环境变量：
    CM_BASE_URL=http://localhost:8080 pytest -q
"""
from __future__ import annotations

import logging
import os
import pathlib
import subprocess
import sys
import time

import pytest
import requests

from core.client import ApiClient
from core.data import rule_payload

ROOT = pathlib.Path(__file__).resolve().parents[1]
PORT = int(os.getenv("CM_PORT", "8009"))
DEFAULT_URL = f"http://127.0.0.1:{PORT}"


def _healthy(url: str, timeout: float = 0.5) -> bool:
    try:
        return requests.get(f"{url}/api/health", timeout=timeout).status_code == 200
    except requests.RequestException:
        return False


@pytest.fixture(scope="session")
def base_url():
    url = os.getenv("CM_BASE_URL")
    if url:
        if not _healthy(url):
            pytest.fail(f"CM_BASE_URL 指向的服务不可用: {url}/api/health")
        return url

    if _healthy(DEFAULT_URL):
        return DEFAULT_URL  # 已经手动起好了，直接用

    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "mock" / "app.py"), str(PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            if _healthy(DEFAULT_URL):
                break
            if proc.poll() is not None:
                pytest.fail("mock 服务启动失败，请先手动执行 python mock/app.py 看报错")
            time.sleep(0.1)
        else:
            pytest.fail("mock 服务启动超时（10s）")
        yield DEFAULT_URL
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture()
def api(base_url):
    client = ApiClient(base_url)
    yield client
    client.close()


@pytest.fixture()
def created_rule(api):
    """建一条规则，用例结束后清理，保证用例之间互不影响。"""
    payload = rule_payload()
    resp = api.post("/api/alert/rules", json=payload)
    assert resp.status_code == 201, f"前置创建规则失败: {resp.status_code} {resp.text[:200]}"
    rule = resp.json()
    yield rule
    api.delete(f"/api/alert/rules/{rule['id']}")


def pytest_configure(config):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
