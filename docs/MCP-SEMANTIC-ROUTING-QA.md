# Agent语义调度与运行工序查询验证

日期：2026-11-18。

用户原话“帮我看看最近几个方子用时 都卡在哪一步？”再次落入herbal_reference.ask。原因是旧入口只有匹配模块关键词才让模型选工具，其余问题默认药材检索；此前补创建别名没有解决运行查询的整体入口问题。

## 最终行为

- 配置模型时，Agent请求统一进入五工具语义选择，已移除MODULE_QUESTION/PLANNER_QUESTION与默认知识工具回退。按当前问题和上下文选择，不要求模块名；运行数据查询无需资料原文。
- 模型或工具失败保持实际错误，意图不明确则澄清。没有模型配置时，仅既有规则明确识别的运行查询可以继续只读，其他Agent请求503。普通AI兼容模式保持原边界。
- 知识工具仅处理药材/方剂知识；其ask参数绑定用户原问题与完整历史，原RAG生成、引用校验和运行历史隔离保留。写入授权仍由独立的当前指令与精确参数校验，模型选择不授予写权限。
- test_execution新增progress动作，经鉴权GET `/api/data-center/recent-batches` 读取最近批次。一次最多完整核验1000条，校验分页总数、数量与重复ID，再按created_at/sequence倒序选择1–20条。超过范围或分页变化明确失败；缺少创建时间说明无法确认最近顺序。
- 工序投影独立于原共享快照，包含current_stage、steps中的elapsed_seconds/duration_seconds/device_id与等待原因。回答直接按已校验字段汇总等待工序及实际处理分钟数，单列该批次配置分钟数，不用默认时长冒充实际耗时。实际处理不含排队/暂停；计时缺失不能填零，当前等待不能证明长期卡死。
- progress读取后直接结束，不再额外请求模型自由总结。具体设备数量优先选择data_center/question，整体概况使用operations_overview；工具选择请求设置temperature=0。

## 自动回归

- `backend`：`.venv\Scripts\python.exe -m unittest discover -s tests -v`，245项通过。
- 最终工具说明、等待汇总和一次完成逻辑收尾后：`.venv\Scripts\python.exe -m unittest discover -s tests -p test_mcp_tools.py -v`，30项通过。
- 覆盖无旧关键词的运行表达进入语义选择、原问题传递、失败/无模型不回退资料、知识引用、最近记录跨201条分页排序、分页变化/超1000条拒绝、无创建时间/无计时未知状态、进度查询不写入，以及此前写入数量/否定/方法询问等校验。
- 原知识测试在明确的工具选择模型边界之后继续验证真实问答链路；RAG专用接口和规则问答测试保留鉴权/历史隔离。单元测试不替代下述真实模型验证。
- 本轮无前端源码或依赖变化，未重复前端类型检查和生产构建。

## 真实模型与页面

真实DeepSeek工具选择、现有Next.js页面、8127端口独立FastAPI与临时SQLite；平台读写采用隔离回执，药材内容采用隔离资料结果。未在真实平台创建批次、启停或保存默认用时，未重复验证真实RAG内容质量。

| 窗口 | 输入/场景 | 确认结果 |
| --- | --- | --- |
| 1440px | 帮我看看最近几个方子用时 都卡在哪一步？ | test_execution/progress，读取5条上限，实际返回3条；等待包装设备、累计实际处理2分钟与配置5分钟分别展示 |
| 1440px | 这几张单怎么还没好 | 同上，未查资料或执行写入 |
| 1440px | 最近的处方做到哪了 | 同上 |
| 1440px | 下3个测试方子 | test_execution/create，数量3，未自动开始 |
| 1440px | 我现在工作有几个锅 | data_center/question，按实际快照的2台使用中锅回答 |
| 1440px | 把包装默认用时改成2分钟 | test_plans/read后save，按读取修订号确认隔离保存 |
| 1440px | 陈皮的功效 | herbal_reference/ask，保留并可打开引用 |
| 390px | 截图原话，再切换陈皮功效 | 分别progress与herbal_reference，2项通过 |
| 320px | 截图原话，再切换陈皮功效 | 分别progress与herbal_reference，2项通过 |

最终11项通过，无页面错误或横向溢出。完整复测曾发现设备数量问题被模型选成总览，已收紧两工具的职责与选择提示，并保持原断言完成最终复测。桌面/320px工序截图已查看，常规字重、单主栏滚动和输入区保持可用。

证据：[最终结果](../design/mcp-semantic-routing-qa/results.json)、[桌面工序查询](../design/mcp-semantic-routing-qa/1440-test_execution-1.png)、[320px工序查询](../design/mcp-semantic-routing-qa/320-test_execution-10.png)。

## 当前平台与本机服务

只读调用当前配置平台的batches列表核验：85条全部提供created_at与steps字段，结构校验成功；仅输出字段覆盖数量，没有记录处方正文或凭据。不修改另一个项目的源码、数据库或服务。

本草8000端口后端已核实并重载，保留原数据库、账号、配置和平台数据。Qwen/FAISS预热完成，8000后端与3000前端代理的`/api/health`均为ok；OpenAPI包含新路由，经3000代理匿名访问recent-batches返回401。界面可重新发送截图原话。
