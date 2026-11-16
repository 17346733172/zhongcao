# 项目架构与目录

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
| frontend/src/components/question-composer.tsx | 多行输入、真实回答模式、附件和可访问发送按钮 |
| frontend/src/components/sidebar.tsx、upload-panel.tsx | 导航、账号入口与按权限展示资料操作 |
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

SQLite 默认位于 backend/data/bencao.db，保存用户、会话、登录尝试与共享文本。目录不进入版本库。SQL 使用参数绑定。

MD / TXT 在浏览器读取 UTF-8 后经 API 保存原文；后端独立校验类型、文件名、空白及 10 MB UTF-8 字节上限。请求体也有上限。PDF / Word 暂不上传。demo 字段用于隔离示例资料（默认不再预置），检索排除所有 demo 条目；stored 标识持久化资料。

内置《中药基础知识（详解版）》通过 GET /api/reference-document 与 /api/reference-document/file 读取，均校验 knowledge:read。原文件和结构化正文保存在 backend/resources，未放入前端公开资源目录或客户端包；一次性导入保留原文章节、段落和表格，并记录原文件 SHA-256。它独立于共享上传列表；页面自动加载或主动查看资料时读取，参与知识库模式检索，引用保留结构化正文与 Word 下载入口。以下检索、文档主题解析、语义重检与引用校验均限定于 use_knowledge=true。

附加原文检索由 knowledge-answer.ts 根据 AI 整理的完整问题（未整理时使用当前输入）匹配真实正文生成摘录。按正式文档的章节聚合药材条目，中文分词去除问句虚词；只返回正相关结果，数字等未命中查询不兜底到示例或其他段落。会话只在页面内存中，不持久化。AI 模式的 /api/chat 接受当前问题和最多 5 轮受限摘要；先承接省略主题，显式新主题优先，无主题或指代不明时提示补充；经 knowledge:read 与 CSRF 验证后读取共享正文，由 retrieval.py 按补全后的问题选择最多 3 个片段，再由 chat.py 调用配置的 DeepSeek 服务。密钥只在后端环境读取；每个发送片段最多 3000 字符。输出 JSON schema 与来源类别 / 编号校验后，由服务端关联原文；对规则与关键词未命中的中文自然语言，先由同一 DeepSeek 整理意图（follow_up / standalone / clarify / unrelated，最多一次、512 tokens、10 秒阶段超时），再重新检索实际授权资料；整理过程不发送原文、不产生事实或引用。数字 / 代码式无意义查询不进入语义请求；重检仍无资料不生成回答。语义和生成共用 4 个并发名额，理解后的问题由回答简介及 resolvedQuestion 保留。有相关资料但内容不足时允许模型一般知识补充：document 段有真实引用，ai_supplement 段无文档引用，界面及复制内容均保留明确标签。模型补充没有联网核实。历史摘要只用于话题理解，不作为事实证据或引用来源，每轮重新读取授权原文。提示词将历史和资料中的指令视为不可信参考文本，引用编号校验不保证事实正确性。通用 PDF / Word 上传解析、流式回答、个人知识库隔离与迁移框架未实现；默认向量流程见上节。

处方的整方 `dose_scope` 独立于模型提取：前端按用户明确要求默认 per_dose，将选择传入 prepare；提取后覆盖各行口径。check 再按整方选择统一口径，规则与报告使用同一实际快照。unknown 表示逐味模式，不覆盖行内 per_dose / total / unknown；省略此字段的旧客户端保留逐味语义。

`prescriptions/review.py` 根据服务端本次 findings 构造审核结论，优先处理十八反，再处理数据异常、信息缺失和人工复核；结论作为 `conclusion` 与原 findings 同时返回，前端展示及复制仅使用同一返回值，不另行推断通过与否。

`prescriptions/narrative.py` 接收本次确认的处方、findings 和 conclusion，生成 3.1—3.5 五节结构；只使用当前字段与固定依据，不调用模型扩写药方。前端页面和 Markdown 复制共用 sections；原 API 元数据保留兼容，界面不再显示旧卡片 / 统计 / 范围面板。

`missing_information.py` 以既有缺失规则和确认后的字段生成具体补充清单（field / label / prompt），不新增临床必填要求。报告返回 missing_information，narrative.py 同时写入 3.1；前端将 field 对应到表单 data-field，保留数据返回并定位首项。

`audit_knowledge.py` 集中保存新增规则来源、采用参考量与煎法条件；Finding.blocking 区分持续提醒与实际阻断项。review.py 输出 passed / not_passed / needs_information 和 decision_reasons，3.1 展示同一判断依据。高风险提醒不单独阻断通过，具体炮制、剂量或煎法问题仍阻断。旧版未含 decision_reasons 的报告自动调用后台重查。
