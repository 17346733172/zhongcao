# 测试方子识别验证

后续更新：本记录保留此前关键词修复过程。入口现已改为统一语义工具选择，命令词规则仅用于写入授权；运行语境下的方子/处方直接查平台，不要求原文。当前行为与验证以 [语义调度验收](MCP-SEMANTIC-ROUTING-QA.md) 为准。

日期：2026-11-18。

截图中的“下3个测试方子”没有进入工具选择：模块入口只识别任务/作业/批次，直接落入 `herbal_reference.ask`。创建数量校验另用独立的任务名规则，即使只补入口关键词，也仍可能被写入校验拒绝。

## 修改

`mcp_tools/commands.py` 提供共用的 `EXECUTION_SUBJECT`，模块分流和明确数量解析均使用同一表达式。任务/作业/批次保持原语义；方子/处方/药方只有带测试、仿真、模拟或演示限定时才能作为演示批次对象。同步模型提示、五工具清单中的测试执行描述，支持个/项/条/批/份/张/副量词，保留当前用户明确指令、1–50整数数量、单次提交和不自动启动等限制。

## 自动验证

- `backend` 运行 `.venv\Scripts\python.exe -m unittest discover -s tests -p test_mcp_tools.py -v`：25项通过。
- `backend` 运行 `.venv\Scripts\python.exe -m unittest discover -s tests -v`：240项通过。
- 覆盖截图原话、测试处方/模拟药方/演示方子、中文和全角数字；否定、方法询问、假设、示例、小数、负数、数量范围、超范围、零、模型数量不一致和多次创建均不写入。缺少数量或仅查询的测试方子问题进入调度澄清，不回退药材检索。
- 普通“下3个方子”“生成三份处方”“下3个药方”“陈皮方子的功效”“测试陈皮方子的药理作用”仍走知识问答，不能授权仿真批次创建。
- 本轮未修改前端源码，未重复类型检查或生产构建。

## 真实模型与页面

现有Next.js页面，真实DeepSeek Tool Calls，8127端口独立FastAPI实例与临时SQLite。仿真平台读取/写入使用隔离回执，药材回答使用隔离资料结果，不在真实平台生成批次，不验证临床处方生成或RAG内容质量。

| 窗口宽度 | 输入 | 结果 |
| --- | --- | --- |
| 1440px | 下3个测试方子 | test_execution/create，数量3 |
| 1440px | 帮我下三份测试处方 | test_execution/create，数量3 |
| 1440px | 下发3张模拟药方 | test_execution/create，数量3 |
| 1440px | 下3个方子 | herbal_reference/ask |
| 390px | 下3个测试方子 | test_execution/create，数量3 |
| 320px | 下3个测试方子 | test_execution/create，数量3 |

六项均通过，无页面错误或横向溢出，创建后没有调用start。桌面和320px截图已查看，工具标签、实际回执、常规字重与输入区显示正常。

证据：[结果记录](../design/mcp-test-prescription-qa/results.json)、[桌面截图](../design/mcp-test-prescription-qa/1440-test_execution-1.png)、[320px截图](../design/mcp-test-prescription-qa/320-test_execution-6.png)。

## 本机加载

已核实并重载本项目的8000端口后端，保留原数据库、账号、密钥配置与仿真平台数据。本地Qwen/FAISS预热完成、应用启动成功；8000后端与3000前端代理的`/api/health`均返回`status=ok`。
