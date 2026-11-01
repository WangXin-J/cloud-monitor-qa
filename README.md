# cloud-monitor 接口自动化测试

![api-tests](https://github.com/WangXin-J/cloud-monitor-qa/actions/workflows/api-tests.yml/badge.svg)

云主机监控系统的接口自动化测试套件，覆盖指标查询与告警规则两类核心接口，包含正常路径、参数校验、边界值与幂等性场景。

- 框架：Pytest + Requests，`client / data / assertions / cases` 四层结构
- 用例：**44 条**（参数化展开后）
- 持续集成：GitHub Actions，push 与 PR 自动执行

---

## 被测服务

本仓库验证的是 cloud-monitor 的 HTTP 接口契约。

仓库内的 `mock/app.py` 是一个**可运行的桩服务**（基于 Python 标准库，无额外依赖）。保留它的原因有两个：

1. 没有后端环境时，任何人都能 `pytest -q` 直接跑通，便于复现问题；
2. 接口契约先于实现确定，前后端可以并行开发。

真实服务见 <https://github.com/WangXin-J/cloud-monitor>，接入方式见第四节。

---

## 一、快速开始

```powershell
cd cloud-monitor-qa
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

预期输出：

```
44 passed in 0.70s
```

`conftest.py` 会检测 `127.0.0.1:8009` 是否已有服务；没有则自动拉起 `mock/app.py`，用例结束自动关闭，无需手动起服务。

需要单独调试接口时：

```powershell
python mock/app.py 8009
curl http://127.0.0.1:8009/api/health
```

---

## 二、目录结构

```
cloud-monitor-qa/
├─ core/
│  ├─ client.py          # HTTP 客户端封装：超时、日志、耗时统计
│  ├─ data.py            # 测试数据工厂
│  └─ assertions.py      # 断言封装，失败时附带响应体快照
├─ tests/
│  ├─ conftest.py        # 夹具：服务生命周期、数据准备与清理
│  ├─ test_health.py     # 健康检查
│  ├─ test_metrics.py    # 指标接口（21 条）
│  ├─ test_alert_rules.py# 告警规则（19 条）
│  └─ test_contract.py   # 契约一致性（3 条）
├─ mock/app.py           # 桩服务
├─ junit/                # 告警规则单测（JUnit 5）
└─ .github/workflows/api-tests.yml
```

---

## 三、用例设计

| 模块 | 条数 | 覆盖点 |
|---|---|---|
| 健康检查 | 1 | 服务可用性 |
| 实时指标 | 4 | 正常返回、缺参、主机不存在、指标值物理范围 |
| 历史指标 | 17 | 默认分页、非法 metric（4 组）、时间倒序、size 越界（4 组）、page=0、越界页返回空、四种指标 |
| 告警规则 | 19 | 创建成功、必填校验（4 组）、非法 metric / operator、阈值越界（3 组）、阈值边界 0 和 100、重名、超长、列表回显、删除、删除幂等、删除不存在、事件查询 |
| 契约 | 3 | 错误响应 Content-Type、错误体结构统一、时间戳单位 |

三个设计取舍：

**1. 异常入参用例占近一半。** 线上缺陷多数来自异常输入，正常路径反而最不容易被破坏。

**2. 用例之间互不依赖。** 每条用例自己准备数据、自己清理（`created_rule` 夹具），避免「单跑通过、全量必挂」这类难以定位的问题。

**3. 断言带上下文。** 失败信息里包含请求方法、URL 和响应体片段，用来区分「用例写错了」和「服务返回错了」。

---

## 四、接入真实服务

**① 指向服务地址**

```powershell
$env:CM_BASE_URL="http://localhost:8080"
pytest -q
```

**② 对齐接口路径**

| 桩服务接口 | 对应业务 |
|---|---|
| `GET /api/metrics/current` | 实时指标查询 |
| `GET /api/metrics/history` | 历史指标分页查询 |
| `POST /api/alert/rules` | 创建告警规则 |
| `GET /api/alert/rules` | 规则列表 |
| `DELETE /api/alert/rules/{id}` | 删除规则 |

**③ 对齐错误码**

用例断言了 `{"code": "...", "message": "..."}` 这一结构（`INVALID_PARAM` / `HOST_NOT_FOUND` / `RULE_NOT_FOUND` / `DUPLICATE_NAME`）。若真实服务尚未统一错误体，应先在服务侧补齐再运行用例。

---

## 五、持续集成

工作流 `.github/workflows/api-tests.yml` 在 `push`、`pull_request` 时触发：

1. 安装 Python 3.11 与依赖
2. 执行 `pytest -q --junitxml=report.xml`
3. 上传 `report.xml` 作为构建产物

运行记录见 [Actions](https://github.com/WangXin-J/cloud-monitor-qa/actions)。

本地生成 HTML 报告：

```powershell
pip install pytest-html
pytest --html=report.html --self-contained-html
```

---

## 六、已知限制

- `mock/app.py` 按 RESTful 契约实现了主要分支，但不代表真实服务的全部行为；
- 当前用例覆盖功能与契约层面，**未覆盖并发与性能**，压测需单独设计；
- `junit/` 下的告警规则实现是用于演示边界条件测法的参考版本，接入实际工程时应替换为项目中的 `AlertRule` 类。
