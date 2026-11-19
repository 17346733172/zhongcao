# 项目架构与目录

2026-11-19（AI 整理回答，最新）：`format_answer` 改为异步节点，先通过现有 `finish` 组装可核对结果与元数据，再由 `mcp_tools/synthesis.py` 使用既有 `RAG.llm.request_json` 在工作线程调用 DeepSeek 整理正文。输入仅含当前问题及本轮工具结果的标题、来源 / 时间说明和正文，不传会话 Cookie、配置凭据或旧轮回答。仅替换 `sections`，引用、工具记录、数据时间、过期标记、跳转及图表由后端保留。结构、长度和新增数字 / 编号校验失败或模型异常时保留工具结果并提示，不重新执行图的工具节点。该检查不是语义事实校验，模型措辞仍需核对。知识库 ask 已有 AI 生成与引用校验，直接复用；未配置模型的规则分支不增加外部请求。用量仍只统计工具选择，不含整理及知识生成。

2026-11-19（聊天 LangGraph，最新）：`mcp_tools/workflow.py` 使用已固定的 LangGraph `1.2.18` 构建并复用六节点 StateGraph：prepare_tools、select_tool、authorize_tool、execute_tool、format_answer、clarify。条件边控制澄清、重复读取结束、先读后保存和最多三次模型选择；执行失败直接退出，节点不配置重试策略。请求级 `AgentContext` 携带 FastMCP Client、配置及服务函数，图状态仅保存本轮消息、步骤、结果、调用记录和实际用量；不使用 checkpointer / store，不开启远程 LangSmith 追踪。`agent.py` 保留模型请求、写入授权、结果格式化和 HTTP / Client 生命周期，移除原有手写三步循环，以异步 `ainvoke` 执行状态图，递归上限16。无模型的明确规则只读查询同样经过图的校验、执行和格式化路径；普通 AI 兼容路径保持独立。

2026-11-19（会话持久化，最新）：新增 `conversations / conversation_messages` 两张 SQLite 表，使用账号与会话组合键及消息唯一键隔离记录。`conversations.py` 提供摘要列表、完整会话读取和幂等追加接口，沿用登录、knowledge:read、CSRF、no-store 和 8 MiB 写入边界。`use-conversation-history.ts` 负责初始恢复、按需读取、保存及失败重试；`KnowledgeWorkspace` 保留请求取消与上下文边界。账号改变时重挂载工作区并终止旧回答，不把旧账号消息存给新账号。下文早期仅页面内存的说明为历史记录。

2026-11-19（整体第三套）：新增 `workbench-tokens.css` 集中设计令牌，`workbench-theme.css` 作为既有流程样式后的视觉映射层，复用 Next.js、React 和 Phosphor。`ConversationSessions` 只派生真实时间分组与排序，`AccountNavigation` 增加现有图标及显示包装，登录与metadata文案与现状同步；无后端、鉴权、网络协议、持久化或依赖变化。

2026-11-19（会话窗口）：`ConversationSessions` 仅展示历史及新建入口；`KnowledgeWorkspace` 复用现有 `conversations / activeId` 状态，切换通过 `changeConversation` 取消请求和重置当前输入。桌面为独立网格列，窄屏为原生 modal dialog，主问答滚动机制保留。没有新增会话持久化、后端 API 或存储。

2026-11-18（统一语义调度，最新）：`/api/chat` 在配置模型时无关键词门槛地进入MCP工具选择，移除MODULE_QUESTION/PLANNER_QUESTION及默认herbal_reference回退。只有选择知识工具才执行原RAG，知识/规则问答参数绑定当前原问题与完整历史。`commands.EXECUTION_SUBJECT` 仅用于独立写入数量授权，不再路由读取。无模型时只保留明确规则运行查询，其他Agent请求503；选择/执行失败不改为知识检索。`test_execution/progress` 经鉴权GET `/api/data-center/recent-batches` 读取批次，最多核验1000条完整分页后按创建时间倒序选取，保留单独的BatchProgress工序投影，不扩大常规快照；实际处理秒数、配置秒数与等待原因由formatter直接展示。规则不授予模型额外写入权限。

2026-11-18（统一页面滚动）：`page-scroll.css` 统一主栏纵向滚动，聊天与总览不再建立第二个纵向滚动容器。`KnowledgeWorkspace.mainScrollRef` 负责新回答定位，按主页面保存/恢复scrollTop，ResizeObserver测量标题和输入区高度，为正文/图表定位留白。固定导航和输入控件不参与该留白，关闭导航/弹窗使用preventScroll恢复焦点，避免改变阅读位置。弹窗与导航打开时main为inert并锁定背景滚动；业务请求边界不变。

2026-11-18（Agent回答展示）：`mcp_tools/presentation.py` 从已校验的成功结果派生调用摘要、实际耗时、数据时间与图表，`agent.finish` 保留最新同名图表并避免修改原知识回答缓存。`request_decision` 只透传合法的上游Token计数，按请求累计并标明 `scope=tool_selection`，不包含知识生成用量。前端 `answer-header.tsx` 展示元信息，`answer-charts.tsx` 校验并绘制图表及可展开数据表，`conversation-view.tsx` 继续负责正文、引用和复制，样式集中于 `agent-answer.css`；旧回答缺失新字段时兼容展示，不补造记录。

2026-11-18（任务口语修复）：聊天路由覆盖“任务/作业”，送至同一 MCP 工具选择流程；`mcp_tools/commands.py` 统一全角/空白规范化和明确创建数量提取，供路由与写入授权使用。任务与仿真批次语义同时写入 Agent 提示与工具描述，避免“下3个测试任务”误入药材检索；实际数量仍与当前指令核对，不从模型或历史猜测，不自动开始仿真。

2026-11-19（MCP，最新）：`app/mcp_tools/` 使用独立 FastMCP `4.2.2` 包，以自定义 `Tool` 保留五模块的扁平 schema、严格 Pydantic 参数与脱敏错误，注册到 `FastMCP` 服务，页面通过 `Client(server, timeout=190)` 在内存中调用。使用 `ToolResult` 和客户端的 `structured_content / is_error` 处理结果，不再直接使用 SDK 的低层 Server 或内存会话辅助函数。`BencaoClient` 使用当前页面转发的会话 Cookie，经 `httpx.ASGITransport` 在进程内访问既有鉴权 API，不接收独立账号或服务地址。`/api/knowledge/query` 复用原知识库流程，`/api/data-center/question` 复用规则运行问答，避免回调 `/api/chat` 递归。模块问题由 DeepSeek Tool Calls 最多选择3步，写入须核对当前用户明确指令，保存先读取可写版本，成功写入后停止；运行回答由工具数据格式化，不采用模型生成的数字。普通 AI 兼容路径独立保留。详见 [MCP 工具](MCP-TOOLS.md)。此条替代此前聊天不执行任何仿真写入的范围，不涉及物理设备控制。

2026-11-18（默认用时真实保存）：当前仿真服务器已部署接收端 GET / POST 默认用时接口，本草沿用既有 `device_defaults.py`、数据层和编辑页即可真实保存。服务器补丁保留内存缓存、检查点及拆分状态表，在既有状态元信息中保存配置和独立修订号，变更事件同事务提交；已有批次步骤不重算。独立 PostgreSQL 63 项及本草相关 17 项回归通过，详见[真实保存验收](DEVICE-DEFAULTS-ENABLE-QA.md)。此条替代下文服务器缺少修改接口的历史状态。

2026-11-17（默认用时读取恢复，最新）：`device_defaults.py` 对 GET 传输失败最多重试一次，整轮限定 40 秒；确认旧平台后优先使用共享快照设备和原 fetched_at，过期快照在独立读取也失败时显式标为 stale / error。404 能力结果仅缓存 60 秒，`refresh=true` 绕过缓存重新探测；未知能力的网络失败不判成旧版。前端仅在读失败 / 过期时每 15 秒重新读取，保持草稿和时间语义，不自动重复写入。

探测未成功但共享值有效时，返回 nullable supported 和 capability_pending，保留值并单独说明能力待确认，自动再次探测；不会把网络失败转换成永久只读结论。

2026-11-17（测试方案默认用时，最新）：`test-plans-page.tsx` 复用设备分类卡片元信息，`use-device-defaults.ts` 管理读取、草稿、版本、保存回执及关闭锁定，API 集中于 `device-defaults-api.ts`，样式集中 `test-plans.css`。后端 `device_defaults.py` 提供独立的读取 / 保存适配，复用 DECOCTION 认证、代理与单次写请求；旧平台回退读取 dashboard 默认值并返回 supported=false，不在本草存储覆盖值。`integrations/simulator-device-defaults.patch` 是接收端待部署补丁，未改动关联平台仓库；无新增依赖或环境变量。

2026-11-17（已完成历史批次，最新）：`GET /api/data-center/completed-batches` 复用 `read_simulation`、DECOCTION 配置与 `knowledge:read` 鉴权，固定向平台 `/batches` 传递 `status=completed` 及分页，校验状态与分页并附成功读取时间，不扩大活跃快照。`use-completed-batches.ts` 在历史标签挂载时读取、每轮结束后 15 秒更新，离开时取消；同页失败保留数据，翻页失败不将旧页当作新页。`CompletedBatchRecords` 展示列表与累计统计各自时间；标签数量消费现有共享快照，无新增依赖或环境变量。

2026-11-17（实时批次记录，最新）：新增 `running-batch-records.tsx` 消费共享 `DataCenterSnapshotReader`，仅派生 `status=running` 的批次，使用快照已有的 `prescription_id` 展示关联处方编号，不额外读取处方明细。`TestExecutionPage` 在实时记录和测试记录标签复用该组件，刷新继续调用原 reader；原空表仅保留历史批次部分。样式集中于 `test-execution.css`，无新增后端、轮询、依赖或环境变量。此条替代下文测试记录占位的说明。

2026-11-17（任务区域 02 设备，最新）：将原 `active-pots-task.tsx` 统一为 `active-devices-task.tsx`，`ActiveDevicesTask` 用 `group=pots / other` 分别展示使用中的煎药锅和非煎药锅设备；`TestExecutionPage` 组装区域 01 / 02，删除区域 02 占位。两区消费同一个 `DataCenterSnapshotReader`，保留批次 / 报警关联、刷新和状态反馈，无新增轮询、接口、依赖或环境变量。此条替代下文组件名称和区域 02 占位的说明。

2026-11-17（任务区域 01 药锅，最新）：`active-pots-task.tsx` 消费工作区传入的共享 `DataCenterSnapshotReader`，筛选 `kind=pot / status=busy` 并按批次 ID 关联同一快照的工序与报警；不写入平台或建立独立请求。`TestExecutionPage` 组装区域 01 与原区域 02，占位记录保留。工作区在运行总览、数据中心或测试执行打开时启用唯一快照 reader；从 AI Agent 打开测试执行同样启用，关闭后按现有页面需求停止轮询。样式集中于 `test-execution.css`，无新增依赖、后端接口或环境变量。此条替代下文测试执行仅展示占位的说明。

2026-11-17（数据中心移除重复总览，最新）：`DataCenterDialog` 删除运行总览导入、第四个标签和条件渲染；`DataCenterTarget.tab` 恢复 overview / devices / prescriptions。独立总览主页面与共享快照 reader 保留，不改变原三项索引和聊天定位。 此条替代下文数据中心保留四标签的历史说明。

2026-11-17（运行总览主页面，最新）：`KnowledgeWorkspace.mainPage` 管理 operations / ai-agent，默认 operations；运行总览直接渲染现有 `OperationsOverview`，问答保持挂载并用 hidden 切换，保留会话、草稿及阅读位置。`use-data-center-snapshot.ts` 从原数据中心抽出快照读取、刷新、取消和轮询，工作区在总览可见或数据中心打开时启用；同一 reader 传给数据中心，避免重复轮询。重复渲染的总览标题由 useId 隔离。此条替代此前默认 AI Agent 和总览快捷入口打开弹窗的说明。

2026-11-16（运行总览快捷入口，最新）：`DataCenterTarget.tab` 增加 `operations`，侧栏经 `KnowledgeWorkspace.openDataCenter` 复用 `DataCenterDialog` 并初始化到第四个标签。标签变化回传工作区，同步侧栏高亮；共用原快照和刷新。 此条替代下文侧栏移除运行总览的历史说明。

2026-11-16（AI Agent 入口，最新）：`KnowledgeWorkspace.openModule` 将 `ai-agent` 映射到现有主区，其他模块继续使用 `WorkspaceModuleDialog`。基础资料、数据中心和模块弹窗均关闭时，侧栏选中 AI Agent；不重新挂载问答组件、不清除会话或草稿。`Sidebar` 对该入口使用 `aria-current="page" / aria-controls="main-content"`，仅其他模块保留弹窗语义。

2026-11-16（资料入口拆分，最新）：`LibraryToolsDialog` 只管理基础资料容器和键盘焦点，删除资料 / 处方标签、切换状态及 `PrescriptionDialog` 嵌入。侧栏与弹窗改名「中药基础资料」。`PrescriptionDialog` 仅保留独立弹窗模式，由输入框按钮打开；资料读取、章节定位和下载继续复用 `ReferenceDocumentDialog / SourceDialog`。

2026-11-16：`QuestionComposer` 的附件入口改为所有登录用户可用的「处方检查」，由 `KnowledgeWorkspace` 打开现有独立 `PrescriptionDialog`，不依赖共享资料加载。删除 `UploadPanel`、共享资料前端上传 / 移除逻辑与抽屉状态 / 样式；资料读取继续用于问答，后端 API 与已保存资料保留。独立弹窗关闭后恢复新按钮焦点。

2026-11-14（仿真控制接通，最新）：新增`simulation_operations.py`，提供独立的`/api/simulation/status`及`scenarios / start / pause`写接口。复用DECOCTION配置、登录与CSRF，不改变数据中心只读接口；控制状态直接读取轻量dashboard，不依赖旧快照。写请求单次发送、校验回执、进程内串行防重，写入后通知数据中心刷新。前端`simulation-api.ts`负责协议，`use-simulation-controls.ts`负责请求、竞态隔离与反馈，弹窗负责展示。

2026-11-14（时间显示，最新）：按用户反馈移除新建弹窗的整个实时时钟区域，清理对应定时器、监听、状态与样式。仅保留现有平台快照的底部「数据读取时间」，快照读取和状态反馈继续复用原流程；没有后端或业务控制变更。

2026-11-14（新建测试任务）：`KnowledgeWorkspace` 管理上层弹窗的开关，测试执行页头的新建按钮打开 `new-test-task-dialog.tsx`；弹窗与原测试执行dialog为兄弟节点，由原生模态机制隔离焦点，关闭返回新建按钮。数量与反馈仅保存在本次弹窗，运行状态复用现有只读快照，样式集中在 `new-test-task.css`；没有新增控制接口或后端修改。

2026-11-14（测试执行）：`test-execution-page.tsx` 负责截图指定的布局、三个标签和空状态，不包含测试业务数据或接口请求；样式集中于 `test-execution.css`。通过现有 `WorkspaceModuleDialog` 的内容、页头和样式插槽呈现，其余栏目继续使用原占位弹窗。没有新增后端、依赖或环境变量。

2026-11-14：`operations-overview.tsx` 由 `DataCenterDialog` 在第四个「运行总览」标签中呈现，直接消费该弹窗已有的 SnapshotState，不再独立轮询；刷新共用顶部按钮。`operations-device-categories.tsx` 负责14类设备说明和状态汇总，设备列表在同标签展开，样式集中在 `operations-overview.css`。侧栏不再显示运行总览；测试执行提供布局页，其余五个栏目继续使用占位弹窗。设备投影可选保留 `default_processing_seconds`，兼容旧快照；没有新增控制接口、依赖或环境变量。

2026-11-13：`data_center_utilization.py` 负责利用率口径与日期能力限制，复用共享设备快照。累计利用率使用平台字段，多个设备取算术平均；占用率是busy台数除以所选设备数，指标词不作为busy筛选。指定日期请求保留规范主题与设备ID，明确缺少完整时段记录，累计 / 当前只作参考；无额外平台调用、表或依赖。

2026-11-13：`data_center_chat.py` 将锅号视为设备编号，识别显式pot编号或带设备编号标签的ID，按快照设备ID精确匹配。编号追问继承设备类型 / 状态，具体编号保存在规范主题中；查询仍不调用模型，设备控制命令保持只读拒绝。回答目标通过可选deviceId传到前端设备筛选，不改变平台ID或新增远程接口。

2026-11-13：统计接口可选 `start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`，与 days 参数互斥，默认仍为近7天。共享范围校验在平台读取前执行，包含起止日期且最多366天；SQL 使用北京时间开始日零点为下界、结束日次日零点为排除上界，并限定到真实同步时间。自定义只改变本地汇总范围，不改变增量同步、来源隔离或持久化结构。

2026-11-13：`simulation_statistics.py` 与 `statistics_models.py` 独立提供历史统计，通过已配置代理 / 网关只读分页拉取五种业务事件，按平台 `real_time` 转北京时间自然日汇总；不使用仿真累计秒数。SQLite 保存来源摘要、事件 ID / 类型 / 时间 / 数量及游标；全部类型成功后一起提交，来源隔离，首事件标识变化后重建。`/api/data-center/statistics?days=1|7|30` 复用 knowledge:read 鉴权，合并同时请求，60秒缓存 / 失败退避，单轮35秒上限，客户端单轮使用并在传输错误后重建。统计同步与当前快照任务独立，失败不影响现有设备概览。

2026-11-01 展示更新：ConversationView 每轮只渲染 message.answer，不再渲染独立 originalAnswer；兼容保留返回数据，AI 引用继续使用 answer.sources 打开完整原文，检索和回答生成流程不变。

## 技术栈

前端：Next.js 16 App Router、React 19、TypeScript、普通 CSS 与 Phosphor 图标。
后端：Python 3.11+、FastAPI、Uvicorn、Argon2id、SQLite、httpx（调用 DeepSeek 与煎药平台）。运行和测试依赖分别见 backend/requirements.txt、requirements-dev.txt，完整约束见 requirements-lock.txt。

## 模块

| 位置 | 职责 |
| --- | --- |
| frontend/src/app/page.tsx | 登录保护后的知识库入口 |
| frontend/src/app/login/page.tsx | 登录入口 |
| frontend/src/app/admin/page.tsx | 管理员账号管理入口 |
| frontend/src/app/account/page.tsx | 个人账号与改密入口 |
| frontend/src/app/globals.css、workspace.css、chat-layout.css、auth.css | 设计变量、知识库布局与登录 / 管理布局 |
| frontend/src/components/authenticated.tsx | 会话检查、退出、账号导航和页面权限门禁 |
| frontend/src/components/login-form.tsx | 登录表单、错误和忙碌反馈 |
| frontend/src/components/user-management.tsx | 创建账号、角色、停用和重置密码 |
| frontend/src/components/account-settings.tsx | 当前账号信息与改密 |
| frontend/src/components/knowledge-workspace.tsx | 资料加载、问答模式 / 请求取消与文件状态编排 |
| frontend/src/components/question-composer.tsx | 多行输入、处方检查快捷入口和可访问发送按钮 |
| frontend/src/components/sidebar.tsx | 导航、账号与资料 / 处方工具入口 |
| frontend/src/components/conversation-view.tsx、source-dialog.tsx | 回答、按 Message.showSources 展示引用和完整原文；该标志记录发送时的原文开关 |
| frontend/src/components/reference-document-dialog.tsx、document-content.tsx | 正式基础资料加载、重试和章节 / 表格阅读 |
| frontend/src/lib/reference-document.ts | 内置资料元信息与只读 API 请求 |
| backend/app/reference_document.py、resources/ | 内置文档正文与 Word 原文件，仅经鉴权接口读取 |
| backend/scripts/import_reference_document.py | 从指定 Word 一次性生成阅读数据并保留原文件 |
| frontend/src/lib/api.ts | 同源请求、错误转换与账号类型 |
| frontend/src/lib/types.ts、demo-data.ts | 资料 / 来源类型、知识库配置及空的初始状态 |
| frontend/src/lib/chat-api.ts、conversation-history.ts | AI 状态、当前会话最近 5 轮摘要与带取消 / 超时的问答请求 |
| frontend/src/lib/answer-mode.ts | 页面固定原文 + AI，按同次服务端召回追加独立原文结果；普通 AI 分支仅内部兼容 |
| backend/app/conversation_context.py | 当前问题的省略主题承接、显式新主题优先与歧义提示 |
| backend/app/question_understanding.py | 未命中自然语言的结构化意图、口语 / 错字理解、歧义与主题校验 |
| backend/app/retrieval.py、chat.py | 服务端关键词 / 炮制章节检索、字段聚焦、DeepSeek 调用、来源类别与引用校验 |
| frontend/src/lib/knowledge-answer.ts | 中文分词、章节匹配与真实原文摘录；无命中不生成引用 |
| frontend/next.config.ts | /api/* 代理至 FastAPI，后端地址仅在服务端使用 |
| backend/app/config.py、database.py | 环境配置、SQLite 连接与幂等建表 |
| backend/app/config.py 的 DECOCTION_PROXY_URL | 可选显式代理，供全部仿真 HTTP 请求统一使用；不全局读取系统代理 |
| backend/app/security.py、schemas.py | Argon2id、令牌摘要、权限映射与输入模型 |
| backend/app/main.py | 应用工厂、会话、账号与共享资料 API |
| backend/app/prescriptions/agent.py | LangGraph 状态图、意图条件分支、确认与检查两阶段，不配置持久检查点或远程追踪 |
| backend/app/mcp_tools/workflow.py、agent.py | 聊天 LangGraph 状态图与请求服务；独立运行时上下文、有界工具循环、授权及单次写入，FastMCP 内部执行 |
| backend/app/prescriptions/files.py、extraction.py | 有限文件读取、图像规范化 / PDF 渲染、文字意图与提取、药物行证据和数值校验 |
| backend/app/prescriptions/vision.py | 单次 DeepSeek 视觉请求完成分类、模型转录和处方字段提取；严格结构校验，标明转录不等于独立图像核验 |
| backend/app/prescriptions/models.py、rules.py、routes.py | 处方输入边界、可追溯有限规则、登录 / CSRF 保护 API |
| backend/app/integrations/decoction.py | 煎药平台字段转换、认证、同编号重试和回执确认 |
| backend/app/data_center.py、data_center_models.py | 登录保护的快照状态、处方分页与按需批次读取，以及响应模型 |
| backend/app/data_center_chat.py | 运行问题识别、同主题追问、快照状态统计和来源时间；不调用模型或执行平台写操作 |
| backend/app/simulation_snapshot.py | 共享后台轻量刷新、单轮连接范围与失败重建、整轮超时、真实快照缓存与实际时间 |
| frontend/src/components/data-center-dialog.tsx、data-center-panels.tsx、src/lib/data-center-api.ts | 简约数据中心、设备与报警筛选、处方分页 / 详情和只读请求 |
| frontend/src/components/prescription-*.tsx、src/lib/prescription-api.ts | 上传、原图核对、编辑确认、报告与 multipart 请求 |
| backend/app/cli.py | 终端交互式创建首个管理员 |
| backend/tests/test_auth.py、test_chat.py | 角色越权、会话撤销、密码、资料持久化与 AI 来源 / 异常验证 |

## 本地向量 RAG（2026-11-01）

性能调整：只用今天接入的 Qwen + FAISS 向量检索，不启用旧关键词快速路径。查询向量用有界内存 LRU；已校验回答另设按账号隔离的短时缓存，并以完整原文哈希等输入使变更失效。口语省略先理解再检索，嵌入不保留 KV 缓存。POST /api/chat 用 Server-Timing 和仅含耗时的日志区分资料加载、上下文、检索、理解与生成。

默认 `RAG_ENABLED=true`。`code/RAG/utils.py` 负责 Markdown 加载、分块、索引指纹与增量更新，`Embeddings.py` 负责本地 Qwen3 嵌入，`faiss_db.py` 负责归一化 FAISS 与 JSON 持久化，`prompt.py` / `llm.py` 分别保存真实提示词与 DeepSeek 传输。`backend/app/rag.py` 将其适配到原有权限、追问、来源与引用结构。`code/data` 保存指定 PDF 的 Markdown、原件及来源校验记录；模型位于 code/models，生成索引位于 code/db。

知识库模式读取 Markdown 与 SQLite 当前授权共享文本，向量召回后复用现有引用校验；不重复索引同源 DOCX。回答带 retrievalMethod=vector、retrievedSources，前端直接使用同次召回原文，不再由浏览器关键词重检。普通 AI 在读资料和初始化模型前分支。无正文变化复用索引，资料变化复用未变片段向量并重建当前快照；不使用 pickle。详见 [RAG](RAG.md)。

以下关键词召回说明仅作为历史记录；现行部署不支持 `RAG_ENABLED=false` 旧入口，资料问答使用 code/RAG。

## 数据流与权限边界

`POST /api/chat` 在原文 / AI 模式中先识别运行数据问题，命中后复用应用唯一 `SnapshotReader`，无需加载中药文档、检索或调用 DeepSeek。非运行问题继续在线程中执行既有同步知识回答，避免阻塞后台刷新事件循环。历史新增可选 `channel=data_center`，运行回合只携带主题，不携带统计正文；中药回答不继承最近设备话题及其前面的旧药材主题。

浏览器通过同源 /api 请求 → Next.js 转发到本机 FastAPI → 后端读取 HttpOnly 会话 Cookie → 根据数据库中账号当前状态和角色鉴权 → 执行资料或账号操作。

页面固定发送 use_knowledge=true，界面没有模式开关；每轮 showSources=true。服务端保留严格布尔字段 use_knowledge（接口省略时默认 false）用于旧调用兼容。下述普通 AI 分支及按模式隔离仅为兼容行为。false 在读取任何知识库之前进入 ChatService.answer_general，只调用模型处理当前问题及同模式历史；true 才加载基础文档与 documents 表并进入原有 ChatService.answer。新页面每轮 showSources=true；摘要只保留最近五轮知识库问答，内部仍能过滤旧普通 AI 记录。普通 AI 的返回段落没有 origin 或来源索引，sources 始终为空。两条分支共用模型请求错误处理和并发限额。

会话原始随机令牌仅在 Cookie 中，数据库存储 SHA-256 摘要；密码存储 Argon2id 哈希。会话默认 8 小时；每次请求检查过期与停用状态。登录错误统一反馈，单账号与连接 IP 在 5 分钟内最多允许 8 次尝试。默认不信任代理转发的 IP。

所有写接口需要 X-CSRF-Protection: 1，自定义头配合无跨域许可阻止跨站表单请求，并校验存在的 Origin 是否允许。生产 HTTPS 配置 COOKIE_SECURE=true。角色更新、停用和密码变更撤销目标账号全部会话。当前管理员不能修改自己的角色或停用自己。

所有登录用户读取同一个中药基础资料库；编辑员和管理员可添加、删除文本，只有管理员可管理账号。不存在公开注册、客户端指定登录角色或客户端保存令牌的流程。

## 持久化与演示边界

用户手动上传处方时，由独立适配模块调用煎药平台 HTTP API。平台保存匿名处方并进入待审核状态，后续审核与批次事务由平台后端执行。两项目的接口、字段与配置见 [后端对接说明](DECOCTION-INTEGRATION.md)。

处方检查是私有的请求级流程，不读取 / 写入共享 documents，也不写入 SQLite。`prepare` 经 LangGraph 返回读取原文或标注为模型转录的文字及待确认字段，`check` 只接收用户确认的数据，再运行规则并报告。图片与扫描 PDF 页发送到配置的 DeepSeek 云端模型，一次完成分类、转录与提取；原生文字沿用两阶段文本流程。内部图像编码不返回前端，原始图片 / PDF 以浏览器对象 URL 对照。所有登录角色可通过 knowledge:read 使用，写请求沿用 CSRF 和 Origin 校验。上传总请求限制 12 MB，文件限制 10 MB，文字 2 万字符，PDF 8 页；并发处方任务最多 2 个。PDFium 仍有全局互斥；本地 OCR 及其初始化、预热已移除。关闭前端不会保证终止已经开始的后端模型调用。

SQLite 默认位于 backend/data/bencao.db，保存用户、登录会话、聊天历史、登录尝试与共享文本。目录不进入版本库。SQL 使用参数绑定。

MD / TXT 在浏览器读取 UTF-8 后经 API 保存原文；后端独立校验类型、文件名、空白及 10 MB UTF-8 字节上限。请求体也有上限。PDF / Word 暂不上传。demo 字段用于隔离示例资料（默认不再预置），检索排除所有 demo 条目；stored 标识持久化资料。

内置《中药基础知识（详解版）》通过 GET /api/reference-document 与 /api/reference-document/file 读取，均校验 knowledge:read。原文件和结构化正文保存在 backend/resources，未放入前端公开资源目录或客户端包；一次性导入保留原文章节、段落和表格，并记录原文件 SHA-256。它独立于共享上传列表；页面自动加载或主动查看资料时读取，参与知识库模式检索，引用保留结构化正文与 Word 下载入口。以下检索、文档主题解析、语义重检与引用校验均限定于 use_knowledge=true。

附加原文检索由 knowledge-answer.ts 根据 AI 整理的完整问题（未整理时使用当前输入）匹配真实正文生成摘录。按正式文档的章节聚合药材条目，中文分词去除问句虚词；只返回正相关结果，数字等未命中查询不兜底到示例或其他段落。聊天历史按账号持久保存到 SQLite，追问摘要仍只取当前会话最近五轮。AI 模式的 /api/chat 接受当前问题和最多 5 轮受限摘要；先承接省略主题，显式新主题优先，无主题或指代不明时提示补充；经 knowledge:read 与 CSRF 验证后读取共享正文，由 retrieval.py 按补全后的问题选择最多 3 个片段，再由 chat.py 调用配置的 DeepSeek 服务。密钥只在后端环境读取；每个发送片段最多 3000 字符。输出 JSON schema 与来源类别 / 编号校验后，由服务端关联原文；对规则与关键词未命中的中文自然语言，先由同一 DeepSeek 整理意图（follow_up / standalone / clarify / unrelated，最多一次、512 tokens、10 秒阶段超时），再重新检索实际授权资料；整理过程不发送原文、不产生事实或引用。数字 / 代码式无意义查询不进入语义请求；重检仍无资料不生成回答。语义和生成共用 4 个并发名额，理解后的问题由回答简介及 resolvedQuestion 保留。有相关资料但内容不足时允许模型一般知识补充：document 段有真实引用，ai_supplement 段无文档引用，界面及复制内容均保留明确标签。模型补充没有联网核实。历史摘要只用于话题理解，不作为事实证据或引用来源，每轮重新读取授权原文。提示词将历史和资料中的指令视为不可信参考文本，引用编号校验不保证事实正确性。通用 PDF / Word 上传解析、流式回答、个人知识库隔离与迁移框架未实现；默认向量流程见上节。

处方的整方 `dose_scope` 独立于模型提取：前端按用户明确要求默认 per_dose，将选择传入 prepare；提取后覆盖各行口径。check 再按整方选择统一口径，规则与报告使用同一实际快照。unknown 表示逐味模式，不覆盖行内 per_dose / total / unknown；省略此字段的旧客户端保留逐味语义。

`prescriptions/review.py` 根据服务端本次 findings 构造审核结论，优先处理十八反，再处理数据异常、信息缺失和人工复核；结论作为 `conclusion` 与原 findings 同时返回，前端展示及复制仅使用同一返回值，不另行推断通过与否。

`prescriptions/narrative.py` 接收本次确认的处方、findings 和 conclusion，生成 3.1—3.5 五节结构；只使用当前字段与固定依据，不调用模型扩写药方。前端页面和 Markdown 复制共用 sections；原 API 元数据保留兼容，界面不再显示旧卡片 / 统计 / 范围面板。

`missing_information.py` 以既有缺失规则和确认后的字段生成具体补充清单（field / label / prompt），不新增临床必填要求。报告返回 missing_information，narrative.py 同时写入 3.1；前端将 field 对应到表单 data-field，保留数据返回并定位首项。

`audit_knowledge.py` 集中保存新增规则来源、采用参考量与煎法条件；Finding.blocking 区分持续提醒与实际阻断项。review.py 输出 passed / not_passed / needs_information 和 decision_reasons，3.1 展示同一判断依据。高风险提醒不单独阻断通过，具体炮制、剂量或煎法问题仍阻断。旧版未含 decision_reasons 的报告自动调用后台重查。
