# 五模块 MCP 与 AI Agent

2026-11-18。截图中的五个模块已封装为标准 MCP 工具。页面 AI Agent 使用官方 SDK 的内存 MCP 连接，外部 Agent 使用 stdio；两种连接调用同一套工具及本草 HTTP API，不直接读取另一个项目的数据库。

## 工具

| 工具名 | 对应模块 | 参数与能力 |
| --- | --- | --- |
| `herbal_reference` | 中药基础资料 | `action=read` 按 block 分页阅读（offset/limit）；`search` 按 query 检索内置原文；`ask` 按 query 运行原有知识库回答，保留原文引用及最多5轮 history。read/search 无需模型，ask 复用原 RAG / DeepSeek。 |
| `data_center` | 数据中心 | `snapshot` 读取设备/报警快照；`question` 回答既有设备、锅号与利用率问题；`statistics` 按 days=1/7/30 或成对 start_date/end_date 统计；`prescriptions` 按 status/offset/limit 分页；`batch` 按 batch_id 读取详情。 |
| `operations_overview` | 运行总览 | 返回共享快照的时钟状态、累计指标、批次分布及设备分类数量/状态；可传 refresh。 |
| `test_execution` | 测试执行 | `running` 只列进行中批次与使用中设备；`completed` 完成批次分页；`progress` 按 limit=1..20 读取最近批次工序、等待原因及实际处理/配置秒数，通常读5条；`status` 直接读取启停状态；`create` 生成 count=1..50 个匿名演示批次；`start/pause` 启停当前仿真。 |
| `test_plans` | 测试方案 | `read` 读取13类设备默认用时和 revision；`save` 保存 kind、minutes=0.1..120、expected_revision。药锅 pot 没有固定用时。 |

完整 schema 由 MCP `tools/list` 返回，禁止额外字段。数据读取保留 `fetched_at` / `synced_at`、`stale`、`error`、空数据和历史缺口；refresh 只通知共享快照刷新，不代表远程刷新已经完成。保存用时仍只影响后续数据，处方显式工艺参数优先，已有批次不重算。未实现测试判定、报告导出、单任务停止或物理设备控制。

## 页面 AI Agent

安装更新后的后端依赖并重启后端；前端无需重新构建。仍使用已有 DeepSeek 配置，模型/网关须支持 Tool Calls。已配置模型时所有Agent问题统一先做语义工具选择，不再由关键词决定是否进入模型，也不再默认回退药材检索。运行数据无需知识库原文；只有药材/方剂知识问题选择资料工具。模型或平台失败返回实际错误；意图不清时澄清，不伪装成资料未命中。没有模型配置时，仅既有规则明确识别的运行查询可继续只读，其他Agent问题返回503。

可直接发送：

- `陈皮的功效`：中药基础资料，保留原文引用。
- `我现在工作有几个锅`：语义选择数据中心工具，工具内复用既有设备数量规则。
- `帮我看看最近几个方子用时，都卡在哪一步`、`这几张单怎么还没好`、`最近的处方做到哪了`：选择测试执行的progress，读取平台批次工序，不查询知识库原文。
- `查看运行总览`、`数据中心近7天统计`、`查看已完成的历史批次`。
- `生成2个仿真演示批次`、`开始仿真`、`暂停仿真`。
- `帮我下3个测试任务`、`下发三个任务`、`安排3项测试作业`：测试任务对应仿真演示批次，按明确数量创建，不自动开始仿真。
- `下3个测试方子`、`下三份测试处方`、`下发两张模拟药方`：测试/仿真/模拟/演示限定的方子、处方、药方同样指匿名演示批次。写入须通过独立的当前指令与数量核对；普通方子不能授予批次创建权限。查询方子时按上下文选择运行数据或方剂知识，不由“方子”一词强制查原文。
- `查看测试方案的默认用时`、`把包装默认用时改成2分钟`。

回答说明已调用的 MCP 模块；接口额外返回 `toolCalls: [{name, title, action}]`。工具选择最多3步、每步1个调用，修改成功后立即结束本轮。运行结果由已校验工具数据格式化，不采用模型自由生成的统计数字或成功声明。药材问答保留原有生成及来源校验流程。普通 AI 兼容模式 `use_knowledge=false` 不调用这些工具。

progress读取后直接按校验字段展示，不再要求模型自由总结。最近记录从平台完整分页集合按created_at、sequence倒序选取；一次最多核验1000条，分页变化/重复或超过范围时明确失败，不把首屏旧记录冒称最近。缺少创建时间时说明无法确认最近顺序。实际处理用时为工序elapsed_seconds累计值，不含排队/暂停，当前工序duration_seconds为该批次配置值；缺少实际计时不按零或默认值填补，未提供等待起止时不能判断等了多久或长期卡死。

页面写入只接受当前问题中明确的一项操作及其参数。生成数量支持阿拉伯数字、全角数字及常用中文数字（含两、十、二十等），仍须为1–50的确定整数；修改分钟数使用阿拉伯数字。保存须明确一个设备种类，并在本轮先读取可写版本。否定、假设、询问操作方法、参数不一致或陈旧修订号不会触发修改。含多项修改的需求请分轮发送。模型不支持工具、无有效参数或缺少信息时返回实际错误/澄清；资料、历史或工具文本不能授权写入。

测试方子识别的截图原话、普通处方边界和真实模型页面验收见 [专项验证](MCP-TEST-PRESCRIPTION-QA.md)。

最新统一语义调度与运行工序查询验收见 [运行查询验证](MCP-SEMANTIC-ROUTING-QA.md)，替代此前以关键词决定是否调用Agent的行为说明。

## 外部 Agent 连接

在项目根目录安装依赖：

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

1. 启动本草后端（默认 `http://127.0.0.1:8000`）。
2. 将 [backend/.env.mcp.example](../backend/.env.mcp.example) 复制为 `backend/.env.mcp`，填写现有本草账号和密码。没有默认账号；建议使用已有普通用户或创建一个专门的普通用户账号。真实文件已被 `.gitignore` 忽略。
3. 把 [mcp-config.example.json](../backend/mcp-config.example.json) 的 `bencao` 配置合入外部 Agent 的 MCP 配置，按实际项目位置调整绝对路径。`PYTHONPATH` 也供不支持 cwd 的客户端定位 Python 模块。不要把真实密码填进提交的 JSON。
4. 重新连接后，通过 `tools/list` 应发现上述五个工具。

也可由 MCP 客户端以如下命令启动（stdio 会等待 JSON-RPC，不能当作交互命令行使用）：

```powershell
Set-Location D:\本草\backend
.\.venv\Scripts\python.exe -m app.mcp_tools --env-file D:\本草\backend\.env.mcp
```

环境变量仅供 MCP 进程读取，**不是模型参数**：

| 变量 | 用途 |
| --- | --- |
| `BENCAO_MCP_API_URL` | 本草 API 入口，默认 http://127.0.0.1:8000；远程必须 HTTPS，不接受内嵌凭据、路径和查询参数。 |
| `BENCAO_MCP_USERNAME` | 已存在、启用的本草账号。 |
| `BENCAO_MCP_PASSWORD` | 该账号密码。 |

首次实际调用时登录，之后使用 HttpOnly 会话；会话失效/撤销后重新连接，不自动重新登录或重试原操作。仅列出工具不请求业务数据。凭据不返回模型；不在 stdout 写运行日志，stdout 专用于 MCP。保持本草 API 可达；本实现没有额外开放公网 HTTP MCP 服务端口。

外部写调用必须提供 `confirmed=true`，表示 Agent 已取得用户对本次操作的明确授权；外部 Agent 负责用户确认交互。本草仍逐请求校验登录及权限，写请求保留 CSRF 头、版本冲突、并发锁、平台回执确认与单次发送。例如：

```json
{"name":"test_execution","arguments":{"action":"create","count":2,"confirmed":true}}
```

```json
{"name":"test_plans","arguments":{"action":"read"}}
```

用 read 的实际修订号替换下面的 `12` 后，才能保存：

```json
{"name":"test_plans","arguments":{"action":"save","kind":"packer","minutes":2,"expected_revision":12,"confirmed":true}}
```

超时/连接中断可能已触及平台，先读取实际状态，不能自动重发；`isError=true` 不等于修改一定没有生效。测试方案保存冲突后重新读取并核对，不自动覆盖。

## 实现与验证

- `backend/app/mcp_tools/`：严格输入模型、五工具注册、鉴权 API 适配、stdio 入口、内置 Agent 选择及结果格式化。
- `POST /api/knowledge/query`：复用原知识库流程，避免 MCP 回调 `/api/chat` 递归。
- `POST /api/data-center/question`：复用既有规则运行问答。两个接口均保留登录、knowledge:read、CSRF、64 KiB 请求上限及脱敏校验错误。
- 固定官方 SDK `mcp==1.30.0`（1.x 维护线），在现有 FastAPI/Pydantic 约束下安装；不混用2.x API。协议依据见 [SDK 1.x](https://py.sdk.modelcontextprotocol.io/v1/)、[MCP tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)、[DeepSeek Tool Calls](https://api-docs.deepseek.com/guides/tool_calls/)。

自动测试命令（backend 目录）：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_mcp_tools.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

验收范围及实际结果见 [MCP 验收](MCP-TOOLS-QA.md)。
