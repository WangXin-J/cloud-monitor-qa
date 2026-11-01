# cloud-monitor 接口自动化测试

![api-tests](https://github.com/WangXin-J/cloud-monitor-qa/actions/workflows/api-tests.yml/badge.svg)

给云主机监控系统写的接口自动化套件，用来证明一件事：**这个项目我不只是把它开发出来了，我知道该怎么验证它是对的。**

- 框架：Pytest + Requests，分层结构（client / data / assertions / cases）
- 用例：**44 条**（含参数化展开），覆盖正常路径、参数校验、边界值、幂等性、契约一致性
- 自带演示服务：`mock/app.py`，没有真实服务也能直接跑出结果
- CI：GitHub Actions，push 自动执行

> 徽章地址里的 `WangXin-J/cloud-monitor-qa` 需要和你的仓库实际路径一致，建完仓库如果名字不一样，改这一行即可。

---

## 一、5 分钟跑通

```powershell
cd cloud-monitor-qa
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

看到类似输出就算成功：

```
44 passed in 3.21s
```

> `pytest` 会自动在 `127.0.0.1:8009` 拉起 `mock/app.py`，用例跑完自动关掉，不需要你手动起服务。

想自己起服务看接口：

```powershell
python mock/app.py 8009
# 另一个窗口
curl http://127.0.0.1:8009/api/health
```

---

## 二、目录结构

```
cloud-monitor-qa/
├─ core/
│  ├─ client.py          # HTTP 客户端封装：超时、日志、耗时
│  ├─ data.py            # 测试数据工厂，改字段只改这里
│  └─ assertions.py      # 断言封装，失败时带响应体快照
├─ tests/
│  ├─ conftest.py        # 夹具：自动起 mock、建/删规则、client 生命周期
│  ├─ test_health.py     # 健康检查
│  ├─ test_metrics.py    # 指标接口（21 条）
│  ├─ test_alert_rules.py# 告警规则（19 条）
│  └─ test_contract.py   # 契约一致性（3 条）
├─ mock/app.py           # 演示服务（标准库实现，零依赖）
├─ junit/                # 可选：告警规则单测示例（Java 项目用）
├─ requirements.txt
├─ pytest.ini
└─ .github/workflows/api-tests.yml
```

---

## 三、接你自己的真实服务（改 3 处）

这套用例现在是照着 `mock/app.py` 的接口写的。换成你真实的 cloud-monitor：

**① 指向你的服务**

```powershell
$env:CM_BASE_URL="http://localhost:8080"
pytest -q
```

**② 对齐接口路径和字段**（`tests/` 里搜这些就能找到）

| 演示服务的接口 | 你项目里对应的接口 |
|---|---|
| `GET /api/metrics/current` | 实时指标查询 |
| `GET /api/metrics/history` | 历史指标分页查询 |
| `POST /api/alert/rules` | 创建告警规则 |
| `GET /api/alert/rules` | 规则列表 |
| `DELETE /api/alert/rules/{id}` | 删除规则 |

**③ 对齐错误码约定**

用例断言了 `{"code": "...", "message": "..."}` 这个结构（`INVALID_PARAM` / `HOST_NOT_FOUND` / `RULE_NOT_FOUND` / `DUPLICATE_NAME`）。
如果你的服务没做统一错误体，那正好——**这是一个真实缺陷，先在项目里补上，再回来跑用例**。补的过程本身就是很好的面试素材。

> 改完记得把 `mock/` 目录删掉（或保留，作为本地开发的桩服务）。简历上一旦写"对接真实服务"，仓库里就别留着 mock 当主被测对象。

---

## 四、用例分布

| 模块 | 条数 | 覆盖点 |
|---|---|---|
| 健康检查 | 1 | 服务可用性 |
| 实时指标 | 4 | 正常返回、缺参、主机不存在、指标值物理范围 |
| 历史指标 | 17 | 默认分页、缺参、非法 metric（4 组）、时间倒序、size 越界（4 组）、page=0、越界页返回空、四种指标 |
| 告警规则 | 19 | 创建成功、必填校验（4 组）、非法 metric/operator、阈值越界（3 组）、阈值边界 0 和 100、重名、超长、列表回显、删除、删除幂等、删除不存在、事件查询 |
| 契约 | 3 | 错误响应 Content-Type、错误体结构统一、时间戳新鲜度（防秒/毫秒单位写错） |

**设计上的两个刻意选择：**

1. **异常入参用例占了近一半**。线上缺陷八成来自异常输入，正常路径反而是最不容易坏的。
2. **用例之间互不依赖**。每条用例自己建数据、自己清理（`created_rule` 夹具），避免"跑单个能过、跑全量必挂"这种最恶心的问题。

---

## 五、产出报告和图

最简版（截图用这个就够）：

```powershell
pytest -q --tb=short
```

想看漂亮点的 HTML：

```powershell
pip install pytest-html
pytest --html=report.html --self-contained-html
```

想上 Allure（简历上更好看，但要装 Java）：

```powershell
pip install allure-pytest
pytest --alluredir=allure-results
allure serve allure-results
```

建议 README 里放三张图：**绿色通过截图**、**一条用例失败时的报错截图**（证明断言信息有用）、**GitHub Actions 运行记录截图**。

---

## 六、简历怎么写（按你实际做到的程度选，别越级）

**保守版**（只跑了用例）：

> 基于 Pytest + Requests 为 cloud-monitor 搭建接口自动化测试，设计 44 条用例覆盖参数校验、边界值与幂等性场景，异常入参用例占比 50%

**标准版**（跑了用例 + 接了 CI，推荐）：

> 基于 Pytest + Requests 为 cloud-monitor 搭建接口自动化测试，44 条用例覆盖参数校验、边界值与幂等性；接入 GitHub Actions 实现 push 自动回归，替代手工验证，回归耗时从约 30 分钟降至 2 分钟内

**进阶版**（再加了压测，需要你真的跑出数据）：

> 在上述基础上使用 JMeter 对 WebSocket 推送链路做并发压测，200 并发下 P95 延迟 XX ms、错误率 0%，并据此修正了原简历中缺少测量依据的延迟指标

⚠️ 三条硬性提醒：

1. **数字必须是你跑出来的**。44 条是这份代码的条数，你改完接口后条数会变，用 `pytest --collect-only -q` 数一下再填。
2. **"回归耗时 30 分钟降至 2 分钟"要能说清 30 分钟是怎么算的**（手工点 10 个接口 × 每个 3 分钟）。说不清就换成定性描述。
3. 面试官大概率会让你**当场打开仓库**。README、commit 记录、Actions 绿勾，这三样比描述重要。

---

## 七、面试会被问的 8 个问题

| 问题 | 答题要点 |
|---|---|
| 为什么用 Pytest 而不是 Postman？ | Postman 适合调试和少量回归；用例上规模后需要分层、数据驱动、断言复用、CI 集成，代码化才有优势 |
| 用例怎么设计的？ | 先定接口契约（正常/异常/边界），再用等价类 + 边界值展开。举一个例子：`size` 参数合法区间 1..100，用例取 0、-1、101、1000 |
| 断言为什么单独封装？ | 失败时要能立刻区分是"代码写错了"还是"服务返回错了"，所以断言里带 URL 和响应体片段 |
| 用例之间怎么保证互不影响？ | `created_rule` 夹具每条用例现建现删；不用全局共享数据 |
| 失败了怎么定位？ | 看日志里的 method + url + 耗时，再看断言里的响应体快照；必要时抓包 |
| CI 怎么跑的？ | push/PR 触发，装依赖 → `pytest -q`；conftest 自动拉起被测服务，失败时上传报告 |
| 这套东西怎么维护？ | 接口变了只改 `core/data.py` 和对应测试文件；公共逻辑在 `core/`，改一处生效 |
| 你发现过什么 bug？ | **必须准备一个具体故事**：现象 → 复现 → 定位 → 根因 → 修复 → 补了哪条用例 |

最后一条最重要。没有 bug 故事的自动化测试，在面试官眼里只是"跑通了脚本"。
建议你现在去真实服务上跑一遍，大概率能挖出 1–2 个：错误码不统一、分页 size 没做上限、删除不存在返回 500、时间戳单位不统一。

---

## 八、已知限制

- 这套代码是**按可运行标准写的，但没有在真实 Python 环境里跑过**（生成环境没有 Python）。你本地第一次执行可能遇到路径/依赖问题，把报错发给我即可。
- `mock/app.py` 是为了让用例能跑而写的**桩服务**，行为按合理契约设计，不代表你真实服务的行为。
- `junit/` 下的 Java 单测是**示例**，用来演示边界该怎么测，需要替换成你自己的 `AlertRule` 类再编译。
