# 开发与验证

2026-11-18 Agent语义调度：重启后端加载，前端无源码或构建变更，无新增依赖/环境变量。配置模型时Agent的每个问题均进入语义工具选择，取代旧关键词入口；首次知识问答也会增加一次工具选择请求。新增鉴权GET `/api/data-center/recent-batches?limit=5` 与测试执行progress，使用已有平台batches列表读取完整有界分页并投影工序计时，不修改平台。接口范围/失败语义与验收见 [运行查询验证](MCP-SEMANTIC-ROUTING-QA.md)。

2026-11-18 Agent回答展示：新增前端元信息/图表组件和MCP结果展示字段，需重启后端加载 `mcp_tools/presentation.py`。无新增依赖或环境变量；旧调用方可忽略 `toolCalls` 新字段、`charts` 和 `usage`。用量字段源自 [DeepSeek返回的usage](https://api-docs.deepseek.com/api/create-chat-completion/)，当前只累计模型工具选择请求，不含知识回答生成。界面验收使用隔离平台回执，不在真实平台执行写入。

2026-11-18 MCP：更新 `requirements.txt` 后重启后端，页面 AI Agent 即可调用五模块工具；前端无构建变更。外部 stdio 配置、独立环境变量示例、工具 schema 与验证命令见 [MCP 工具说明](MCP-TOOLS.md)。新增官方 SDK `mcp==1.30.0` 及固定传递依赖，沿用本草账号、CSRF、平台认证、代理与写入校验；不另设免登录 MCP HTTP 端口。知识专用 `/api/knowledge/query` 与规则运行问答 `/api/data-center/question` 同样需要登录和 `knowledge:read`，POST 限64 KiB。

## 环境与启动

2026-11-18 默认用时修改：当前仿真服务器已部署读取 / 保存接口，本草无需新增配置即可编辑并真实保存 13 类设备默认分钟值。已打开的测试方案若保留旧只读提示，点击「重新读取」重新确认能力；保存后用于后续创建的数据，处方显式工艺参数优先。部署备份、独立数据库测试和真实保存验证见[真实保存验收](DEVICE-DEFAULTS-ENABLE-QA.md)。下文服务器缺少接口的说明属于此前版本。

2026-11-17 读取恢复修复：`GET /api/simulation/device-defaults?refresh=true` 可强制重新确认平台能力；默认仅短期缓存真实 404（60 秒），旧平台优先复用共享快照。GET 传输错误可重试一次，单轮最多 40 秒，前端保留 45 秒等待；保存仍单次发送。响应新增 `stale / error`，回退旧值时不修改原 fetched_at。页面仅对读取故障每 15 秒恢复，写入冲突仍手动核对。无新增依赖或配置，本机后端需重启加载。

首次探测失败但有共享设备值时，返回 `supported=null / capability_pending=true`，明确修改能力待确认而非宣称接口不存在。共享值仍按原时间和 stale 状态显示，前端每 15 秒重新确认；只有收到真实 404 才认定旧平台，只有有效完整响应才启用保存。

2026-11-17 测试方案：本草新增 `GET /api/simulation/device-defaults` 与 `POST /api/simulation/device-defaults/{kind}`。全部需登录及 knowledge:read，保存沿用 CSRF / Origin；请求为 `{default_processing_seconds: 6..7200, expected_revision: 非负整数}`。写请求只提交一次，回执确认后刷新共享快照。旧仿真服务器无接口时 GET 回退读取 dashboard 并返回 supported=false，前端只读。接收端协议、配套补丁与待完成的 PostgreSQL 联调见[集成说明](../integrations/README.md)；不能通过修改本草本地值冒充平台保存成功。

2026-11-14新增仿真控制：部署后需重启本草后端，前端开发服务自动更新。复用现有`DECOCTION_*`配置，无新依赖或环境变量。`GET /api/simulation/status`直接读取平台dashboard时钟；`POST /api/simulation/scenarios`接收严格整数`{count: 1..50}`；`POST /api/simulation/start`固定向平台提交`speed: 1`；`POST /api/simulation/pause`无参数。全部需登录及knowledge:read，写入沿用CSRF / Origin保护。控制请求20秒总期限、前端25秒等待，写入只提交一次，不沿用处方上传的自动重试。超时可能已经生效，先查看平台状态和批次数量，再决定是否重试。

Python 3.11+、Node.js 20.9+、pnpm 11。根目录启动后端.cmd 建立 backend/.venv 并配置首个管理员；启动前端.cmd 运行前端。两个终端均保持开启。

依赖、管理员、本地模型和索引准备好后，日常运行可双击根目录 [启动本草.cmd](../启动本草.cmd)。该入口调用 [scripts/start-local.ps1](../scripts/start-local.ps1)，通过 Windows WMI 创建独立后台进程并复用原有两个启动脚本；关闭调用终端或开发工具后服务继续运行。默认不安装系统服务；未启用以下登录自启时，电脑重启后需重新运行。

可选的当前用户登录自启（在项目根目录运行，不需要管理员权限）：

```powershell
powershell.exe -NoProfile -File scripts/set-autostart.ps1
powershell.exe -NoProfile -File scripts/set-autostart.ps1 -Check
# 关闭登录自启，不影响当前已运行的服务
powershell.exe -NoProfile -File scripts/set-autostart.ps1 -Disable
```

[set-autostart.ps1](../scripts/set-autostart.ps1) 仅管理当前账号 Startup 目录内的 `Bencao-Local.lnk`，已有设置会复用；若同名快捷方式指向其他位置则报错，不覆盖或删除。[start-at-logon.ps1](../scripts/start-at-logon.ps1) 静默复用现有启动和就绪检查，将本轮启动结果写入 `tmp/local-servers/startup.log`，各服务日志仍在下面的原位置。自启发生在登录 Windows 后，不自动打开浏览器；模型预热通常需要 1–3 分钟，之后访问原来的 `http://127.0.0.1:3000/`。项目目录、依赖和模型必须保留，移动目录前关闭旧自启，移动后重新启用。此设置仅对本机当前账号生效，不随 Git 自动部署。

启动入口用互斥锁避免同时启动，已有服务或仍在预热的启动进程会复用。它最多等待 240 秒，核验 `8000/api/health`、`3000/login` 和 `3000/api/health` 后才提示就绪；超时不代表模型已停止，先检查日志再重试。日志保存在忽略目录 `tmp/local-servers/backend.log`、`frontend.log`。首次安装和首个管理员设置仍使用上面的交互式脚本。

仅检查运行状态（失败退出码为 1，不启动进程）：

```powershell
powershell.exe -NoProfile -File scripts/start-local.ps1 -Check
```

后端手动启动（backend 目录）：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m app.cli create-admin
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

前端（frontend 目录）：

```powershell
pnpm install --frozen-lockfile
pnpm dev
pnpm typecheck
pnpm test
pnpm build
```

访问 http://127.0.0.1:3000/login 。pnpm start 与 pnpm dev 使用同一端口，不要同时运行。

## 配置

- backend/.env.example → backend/.env：DATABASE_PATH、COOKIE_SECURE、ALLOWED_ORIGINS、DEEPSEEK_API_KEY、DEEPSEEK_BASE_URL、DEEPSEEK_MODEL；启动时自动读取，系统环境变量优先。相对数据库路径基于后端工作目录。
- frontend/.env.example → frontend/.env.local：BACKEND_URL，只在 Next.js 服务端使用。代理配置在构建时生成，生产修改地址后须重新构建。
- 无默认账号密码。app.cli create-admin 只在没有启用管理员时可用；后续从管理页面创建成员。
- 不将真实 .env、数据库、密码或日志提交到仓库。

仿真平台可单独设置后端 `DECOCTION_PROXY_URL`（HTTP / HTTPS 代理入口）。默认留空直连；若本机浏览器走已启用的代理、后端直连跨网服务持续超时，可填写相同的本机代理地址并重启后端。代理地址不接受内嵌账号、路径、查询参数或片段，不返回到前端。只影响仿真统计、处方、批次与上传；不会自动读取系统 / 环境代理，也不改变 DeepSeek 请求或 TLS 证书校验。代理服务须保持运行，入口端口变更后应同步此配置。根因与验证见[连接修复验收](DATA-CENTER-PROXY-QA.md)。

## 开发约定

数据中心时间统计入口为 `/api/data-center/statistics?days=1|7|30`，可附 `refresh=true` 强制同步。启动时为现有 SQLite 增加三张历史统计表，无需新增依赖或环境变量。只缓存统计所需事件字段；平台事件读取复用 `DECOCTION_*`，按真实日期与北京时间自然日统计，含今天且不等同过去24小时。35秒同步上限，60秒缓存 / 失败退避，失败时只显示上次真实同步结果。验证见[时间统计验收](DATA-CENTER-TIME-STATS-QA.md)。

自选日期使用 `/api/data-center/statistics?start_date=2026-11-06&end_date=2026-11-10`；两个日期都必填，不与 days 同传，结束日不得晚于北京时间今天，一次最多366天。返回 days 为实际包含的天数；同一份已同步历史可用于不同区间，无需重新下载全量事件。见[自选日期验收](DATA-CENTER-CUSTOM-RANGE-QA.md)。

页面组装、组件交互、API 请求和数据库逻辑分层。Python 使用 snake_case 和类型注解，前端沿用 kebab-case 文件名及现有组件规范。依赖运行版和测试版分开；Python 约束锁定至已验证版本。

客户端权限控制用于交互呈现，后端鉴权是最终边界。新增业务 API 必须依赖当前用户和对应权限，不接受客户端传来的身份作为授权依据。

demo-data.ts 仅保留知识库配置与空初始状态；检索逻辑在 knowledge-answer.ts，排除示例及未命中片段。AI 密钥只从后端环境读取，不将真实密钥加入源码或日志；会话和通用 PDF / Word 上传解析仍未接入。

## 本地向量 RAG

只使用今天的 Qwen + FAISS 向量检索，不使用关键词快速路径。可配置 RAG_QUERY_CACHE_SIZE、RAG_ANSWER_CACHE_SIZE 和 RAG_ANSWER_CACHE_SECONDS（见配置示例）。Server-Timing 与后端 chat timings 日志显示分阶段耗时，不含问题 / 原文 / 密钥。详见 [性能验收](RAG-PERFORMANCE-QA.md)。

默认 `RAG_WARMUP=true`：启动阶段准备索引、加载并预热模型，日志显示 `Local vector RAG ready` 后才对外提供 API。不要在准备期间重复启动。CPU 默认 `EMBEDDING_CPU_STORAGE=bf16`，保留 Qwen 原始 BF16 权重，逐层转为 FP32 计算，降低常驻内存；`fp32` 用于对照。禁用预热会把首次初始化留给首条向量请求，初始化开销不会消失。模型加载日志只记录导入、分词器、权重和总时长。

2026-11-01 最新页面行为：移除「原文检索」开关，前端默认且始终发送 use_knowledge=true；自动加载资料，默认显示检索原文和 AI 回答。下文 use_knowledge=false 仅说明服务端兼容 API，页面已无普通 AI 切换入口。

默认按 [RAG 说明](RAG.md) 使用 code/data 中的 Markdown、Qwen3 本地模型和 FAISS；首次安装后须下载模型并构建索引。三方依赖由后端统一安装和锁定，启动脚本会检查。数据、模型缓存和索引的相对路径都以 code/ 为基准。实际模型与 API 验证见 [RAG 验收](RAG-QA.md)。

下面关于“关键词、浏览器摘录”的说明为历史记录；现行部署不支持 RAG_ENABLED=false 旧入口。默认向量模式使用同一次服务端召回的原文返回给浏览器；DeepSeek 传输、追问、引用与权限边界保持一致。

## DeepSeek 配置与问答接口

在 backend/.env 的 DEEPSEEK_API_KEY 后填入本机密钥，保存后重启后端。保持 .env 在 Git 忽略列表中；不要发送密钥到聊天、浏览器代码或提交记录。默认地址 https://api.deepseek.com，默认模型 deepseek-flash。地址支持带 /v1 的兼容路径；正式服务要求 HTTPS，HTTP 仅允许回环地址用于测试。系统环境变量优先于 .env。更换配置需重启后端，页面刷新后重新检查状态。

- GET /api/ai/status：需要 knowledge:read，返回 provider、configured（仅表示已填写密钥）、model，不返回密钥。
- POST /api/chat：需要 knowledge:read 和 X-CSRF-Protection: 1，接受 {"question":"问题","use_knowledge":false,"history":[{"question":"上一轮问题","answer":"上一轮摘要"}]}。use_knowledge 默认 false，仅接受 JSON 布尔值；question 长度 1–2000 字；history 可省略，最多 5 轮，每轮 question 1–500 字、answer 最多 1000 字。请求体上限 64 KB；客户端不能指定角色、资料、模型或密钥。
- use_knowledge=false：接口在读取基础文档和 documents 表之前进入 answer_general，只发送当前问题与普通 AI 同模式历史，不执行关键词检索、文档主题解析或知识库语义理解。使用独立提示词和仅含 title / sections（title / content）的严格响应格式，返回 sources=[]，无 origin、文档编号或资料标签。不要求知识库命中；缺少密钥、异常格式和模型失败均报真实错误，不回退到知识库。此分支仅用于内部兼容；当前页面始终自动加载资料并发送 true，没有普通 AI 切换入口。
- use_knowledge=true：进入以下原有知识库流程；前端仅发送知识库模式最近 5 轮摘要，普通 AI 与知识库模式的历史互不混用。
- conversation_context.py 根据当前问题和受限历史解析省略主题，再检索正式基础文档及 SQLite 中的共享文本；明确新药材优先，数字等无关输入不复用旧主题，缺主题或单数指代多个主题时返回 mode=clarification、空正文 / 来源。
- 后端读取正式基础文档与 SQLite 中的共享文本，按药材章节或关键词选择最多 3 个正相关片段，每个最多发送 3000 字符。功效 / 用量等问题只提供相关字段及原文注意事项；饮片加工类问题补检炮制总论中的相关原文。常规未命中自然语言可先进入下述语义理解；重检无资料返回 mode=no_match、空正文和空引用，不调用回答生成。
- question_understanding.py：规则及关键词没有命中的自然语言问题，向同一模型单独发送当前问题、受限历史及服务端最近主题（不发送原文），得到 follow_up / standalone / clarify / unrelated 的严格 JSON。最多一次、512 tokens，10 秒网络阶段超时；拒绝多余字段及缺失 query，追问主题须与最近主题一致；歧义返回 clarification，不能把语义解析当作证据。中文新话题可重新整理后重检，数字 / 代码式无意义输入不调用模型。页面说明「我理解你是在问：…」，保留用户原始问题。语义阶段和生成阶段共用并发名额。
- 使用 httpx 调用 /chat/completions，JSON 输出、关闭 thinking、非流式，最多输出 2048 tokens。单进程最多同时处理 4 个模型请求；连接超时 10 秒、网络读写等阶段超时 30 秒。
- 输出经严格 schema、origin 和引用编号校验。document 段要求至少一个有效引用；ai_supplement 段要求空 citations，前端显示「AI 补充，非文档原文」，不显示文档引用。只有实际被引用的文档才返回 sources；sourceIndex 在补充段中省略，sourceIndices=[]。实际原文、资料名和来源索引由服务端附加，补充只来自模型自身一般知识，并未联网核实。异常 / 截断输出返回错误，前端不把它保存成回答，也不自动降级为假回答。资料内容作为不可信参考文本处理。
- 前端普通 AI 请求最长等待 45 秒，向量知识库模式最长等待 180 秒以容纳本地模型首次加载；新建 / 切换会话会终止浏览器等待，避免旧回答写入新会话。已经发出的上游调用可能继续完成并产生费用。

知识库模式（use_knowledge=true）向配置的云服务发送问题及相关片段，优先依据资料，相关资料未覆盖的内容允许用模型一般知识单独补充；自然语言首次未命中可以先调用一次语义整理，再按整理后的完整问题重检；仍无相关片段时返回未找到，不调用回答生成。附加原文在浏览器直接摘录，不额外调用模型。两种模式分别结合当前会话的同模式最近 5 轮承接，前端通过 resolvedQuestion 保留连续省略的主题；历史只辅助理解，不作为事实或引用来源，每轮重检原文。附加原文按 AI 整理的完整问题（未整理时使用当前输入）检索。兼容模式关键词检索的召回范围有限；默认已接入本地向量检索，流式回答与会话持久化仍需后续实现。官方配置参考：[接入说明](https://api-docs.deepseek.com/quick_start/agent_integrations/)、[Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion/)、[JSON 输出](https://api-docs.deepseek.com/guides/json_mode/)。

## 处方检查接口与多模态解析

图片和扫描 PDF 使用既有 `DEEPSEEK_API_KEY / BASE_URL / MODEL` 配置的视觉模型。目前本机为 DeepSeek 官方接口的 `deepseek-flash`；其他部署必须确认所配模型支持图像输入。无需新增密钥。原图和扫描页会发送至云端，上传前须自行遮盖身份信息；本机不自动遮盖图像中的姓名或号码。

`backend/app/prescriptions/files.py` 校验并准备图像，`vision.py` 一次模型请求完成意图分类、文字转录和结构化提取，图节点为 `read_upload → parse_multimodal → confirm_data`。TXT、MD、DOCX 和原生文本 PDF 保留 `read_upload → recognize_intent → extract_prescription → confirm_data`。混合 PDF 保留原生文字，并只将缺少可读文本的页面渲染为图像，一并提交一次解析。

图片限制为单帧、最多 1600 万像素，读取 EXIF 方向后转换为 RGB JPEG（质量 95，移除元数据），最长边不超过 8192 像素。扫描 PDF 页面渲染最长边不超过 2400 像素；最多 8 页、编码后图像合计不超过 40 MiB。模型输出受严格 schema、文本长度及药物行一致性约束；`source.verification=model_transcription` 明确表示模型转录，不能作为独立图像核验。接口不返回内部图像编码；原文件不入库、不启用 tracing。

处方日志记录 `read_upload`、`multimodal_parse`（或文字路径的意图 / 提取）及 `Prescription prepare total`，不包括 HTTP 文件传输。只记录阶段与耗时，不含处方正文、图像编码、文件名或密钥。接口不接受图片、超时或返回无效字段时明确报错，保留前端文件供重试或手动录入，不回退至本地 OCR。模型单次最长等待 90 秒。验证见[多模态解析验收](MULTIMODAL-PRESCRIPTION-QA.md)。

安装后端 requirements.txt（官方 PyPI 源，含 LangGraph、Pillow、PDFium、python-docx 与 multipart；完整版本受 requirements-lock.txt 约束），然后重启后端。本地 RapidOCR、OpenVINO 直接依赖与 OCR 预热已移除；旧环境安装的包可以保留，但处方流程不再加载，`OCR_WARMUP` / `OCR_BACKEND` 不再生效。本机验证为 Python 3.14，依赖元数据保留 Python 3.11+ 范围。

- `GET /api/prescriptions/status`：需登录及 knowledge:read，返回服务是否配置、支持格式与大小限制，不返回密钥；为兼容保留 `ocr` 字段，其值已改为「DeepSeek 多模态解析（云端）」，不再触发本地预热。
- `POST /api/prescriptions/prepare`：multipart，提交 `file` 或 `text` 二选一，可附 `instruction`（500 字以内）与 `dose_scope`（`per_dose / total / unknown`，省略保持逐味口径；界面按用户要求默认发送 per_dose）。文件最多 10 MB，文字 2 万字符，PDF 8 页，整体请求上限 12 MB。返回读取方式、原文、识别提醒、意图、待核对处方和已执行节点；非处方 / 多个版本返回澄清，不自动检查。只处理正文和表格；DOCX 内嵌图片会明确提醒未识别。
- `POST /api/prescriptions/check`：JSON `{prescription, confirmed: true}`，总请求上限 128 KB。最多 100 味药；`prescription.dose_scope` 为整方口径，per_dose / total 在执行规则前统一各行，unknown / 省略则保留逐味口径。报告返回归一化后的实际处方；数值与单位不作换算。用户确认数据后执行规则并返回分级 findings、依据、范围、规则版本和局限，不调用模型改方。新增 `conclusion` 包含 status / result / detail / finding_codes / note，status 为 passed、not_passed、needs_information，decision_reasons 列明具体系统依据；十八反 / 已登记十九畏及数据异常优先不通过，真实信息缺失待补充，其他阻断项不通过，无阻断项通过本次系统辅助审核。Finding.blocking 为 false 时仅为持续提醒，不代表已排除临床风险。新增 `sections` 为固定 3.1—3.5 五节：每节包含 number / title / paragraphs / items / ordered，每条内容包含 lead（加粗前缀）/ text / children / sources；页面与复制均使用此结构，原元数据字段保留兼容。`missing_information` 始终返回数组（无缺失时为空），每项含 field / label / prompt；field 为患者字段或 `medicines.<零基行号>.<字段>`，只用于定位已存在的核对控件，具体清单也写入 3.1 sections，复制无需另行拼接。
- 三种角色均可使用个人处方流程，仍不能越权写共享资料；所有写请求沿用 `X-CSRF-Protection: 1` 和 Origin 校验。错误反馈不回显输入。无数据库写入、无检查点持久化，禁用该流程远程追踪。每进程最多两个处方任务。

视觉模型不保证手写、低清图片、小数点或单位准确；模型转录与提取字段一致也可能同时读错，原图 / 原始 PDF 对照和人工确认不可跳过。前端上传识别等待最多 180 秒，关闭弹窗取消浏览器等待，已经发出的后端模型调用可能继续完成。文字的基础标识遮盖不等于完整匿名化，真实文件应先脱敏。

规则、来源及验收见 [处方 Agent](PRESCRIPTION-AGENT.md)。共享知识库 PDF / Word 解析仍未接入，不能把处方解析等同于共享资料上传成功。

### 仿真平台上传

模块边界、字段示例、两种认证和错误处理集中见 [两个项目的后端对接](DECOCTION-INTEGRATION.md)。

本草后端通过 `DECOCTION_BASE_URL` 连接仿真平台。默认使用本机 `http://127.0.0.1:8080`，若仿真平台直接以 FastAPI 启动，请使用其实际端口，避免与本草的 8000 端口冲突。启用接口鉴权时，在本草 `backend/.env` 设置 `DECOCTION_API_KEY`，并重启本草后端。密钥仅用于后端 `X-API-Key` 请求头。

使用服务器部署的平台时，`DECOCTION_BASE_URL` 应指向该服务器的实际接口入口。处方保存在接收实例的数据库中，本机实例与服务器实例各自保存数据。若入口返回 `WWW-Authenticate: Basic`，在本草 `backend/.env` 同时设置 `DECOCTION_HTTP_USERNAME` 和 `DECOCTION_HTTP_PASSWORD`，使用 HTTPS 入口并重启本草后端。网关凭据与 API Key 分开配置，均仅在后端读取。

`POST /api/prescriptions/check` 额外返回当前报告的 `simulation_upload_id`。检查结果页点击上传才调用 `POST /api/prescriptions/simulation`，请求包含 `upload_id`、`doses` 和逐味 `medicines`，沿用登录、`knowledge:read` 和 CSRF 校验。后端向仿真平台的 `POST /api/v1/prescriptions` 发送生成的外部编号和匿名编号、总剂数及药材名称、每剂克数、煎法枚举。患者字段、原始材料及报告正文留在本草流程内。

平台接收后处方进入待人工审核。工艺时间及包装参数使用平台默认值；支持的煎法仅映射至对应工序，处方中附带的具体时长不作为仿真参数。失败时保留报告，同一报告重试沿用编号，平台按外部编号防止重复录入。

计数单位「枚」上传为 `unit="item"`，「片」上传为 `unit="piece"`，均使用 `quantity_per_dose`，不填写或猜测 `grams_per_dose`。每剂量保留原数量，总量除以总剂数；支持正小数。平台分别保存枚数、片数和原单位，审核通过前补充 `herb_grams_per_dose`（按药名记录每剂实测克数），按实际重量计算水量。克 / 毫克继续沿用原有 `grams_per_dose` 协议。旧平台拒绝计数协议时明确提示更新接收端，不伪装上传成功。

连接和响应中断最多尝试 3 次，单次连接等待 10 秒、读取等待 15 秒，写入和连接池等待各 5 秒；前端为整个上传流程保留 120 秒。校验或认证拒绝直接返回反馈。连接失败日志仅记录尝试次数和异常类型，便于识别 HTTPS 握手超时。首次请求已写入但响应丢失时，后续相同编号的重复响应按已录入处理。

## 自动验证

### 聊天运行数据查询

`POST /api/chat` 沿用登录、`knowledge:read` 和 CSRF 保护。页面 `use_knowledge=true` 时，先由 `data_center_chat.py` 识别常见锅 / 设备数量、使用 / 空闲 / 故障及报警 / 概况问题；命中后从共享 `SnapshotReader` 的状态构造回答，不读取药材资料或调用模型。`use_knowledge=false` 的内部普通 AI 分支保持独立。

结果沿用原回答结构，增加 `mode=data_center`、`dataCenter` 目标筛选和用于追问的 `resolvedQuestion`，`sources` 为空。有有效近时数据直接回答；没有数据或缓存过期 / 更新失败时可等后台刷新最多 8 秒，然后明确返回旧数据标记或不可确认说明。标题数量按设备实际状态统计，使用中表示设备占用，不保证每台都正在加热。

历史 `ChatTurn` 新增可选 `channel`（`knowledge / data_center`，默认 knowledge）。页面运行回合仅传主题，answer 为空；后端也会隔离最近运行回合，避免旧数字进入模型或将设备话题当作药材追问。知识回答在线程执行，后台刷新保持异步。知识库加载和模型未配置不阻止运行查询；输入框附件入口已改为独立「处方检查」，不依赖知识库资料加载。

现支持常见中文问法，未接入任意设备控制、故障推断或通用自然语言数据库查询。比如「铁锅可以煎药吗」「工作原理」仍走知识分支；缺少故障原因时不猜原因。实现与实际验证见[数据中心问答](DATA-CENTER-CHAT-QA.md)。

### 数据中心读取

数据中心与上传共用 `DECOCTION_BASE_URL`、`DECOCTION_API_KEY`、`DECOCTION_HTTP_USERNAME` / `DECOCTION_HTTP_PASSWORD` 及可选的 `DECOCTION_PROXY_URL`，无需新增依赖。修改代码后重启本草后端；修改配置也需重启。平台须提供 `GET /api/v1/dashboard`、`/batches`、`/batches/{id}`、`/alarms` 和 `/prescriptions`；不直接读取另一个项目的数据库。

- `GET /api/data-center/snapshot`：需要 `knowledge:read`，立即返回 `{data, fetched_at, refreshing, stale, error}`。`data` 是最近一次成功读取的真实快照，无记录时为 null；`fetched_at` 是成功读取平台的时间，重复读缓存不会修改。`?refresh=true` 只唤醒共享后台任务，不等待网络请求。
- `GET /api/data-center/batches/{id}`：需要登录，展开处方时按需读取历史批次摘要；ID 限定为 1–128 个字母、数字、下划线或短横线。
- `GET /api/data-center/completed-batches?offset=0&limit=20`：需登录和 `knowledge:read`，固定读取当前配置平台的 `status=completed` 批次分页，`offset >= 0`、`limit` 为 1–200，返回 `items / total / offset / limit / fetched_at`。包含关联处方编号与追溯码；非已完成状态或异常分页返回脱敏 502。历史标签每页 20 批，完成读取后间隔 15 秒刷新，退出标签取消。沿用已有网络超时、认证、代理与两次只读尝试；无新依赖或配置，部署后需重启本草后端。
- `GET /api/data-center/prescriptions?offset=0&limit=20&status=approved`：同样要求登录，平台分页透传；`status` 可省略或为 `pending_review / approved / rejected`，`offset >= 0`，`limit` 为 1–200。每页包含完整处方信息，不只限于本草上传的记录。

概览后台在单轮内复用 HTTP 连接读取轻量统计、活跃批次和分页报警，本轮结束关闭客户端。传输失败时先关闭失效客户端，再用新客户端重试，防止代理握手失败累积占满连接池。最大连接数 4、池等待 2 秒、清理等待最多 2 秒；网络整轮限定 45 秒，结束后等待 15 秒再更新。首次需要快照时启动共享任务，应用退出时取消；关闭弹窗停止浏览器轮询，不取消其他用户共享的后台任务。前端读取本机状态最多等待 5 秒，后台刷新期间每秒查看一次状态，空闲时每 15 秒查看。平台失败信息在 `error` 中返回，保留旧 `data` 与原时间并标注过期；处方 / 批次读取失败仍返回脱敏 502。日志以每轮结果和耗时区分真实更新成功 / 失败，不将本机状态接口 200 当成平台更新成功。

最近快照保存在 SQLite 旁的 `<数据库文件名>.simulation-cache.json`，默认位于被忽略的 `backend/data/`。只保存已校验的统计、设备、报警和活跃批次摘要，不保存网关凭据、原始处方或报告；按平台地址校验缓存来源，损坏或来源不同的缓存不使用。页面说明该缓存的实际时间，长期离线不假装实时更新。请求不跟随认证重定向，禁止使用服务器环境代理；不修改平台时钟、处方、设备或报警。

最新验收见[缓存与后台刷新](DATA-CENTER-CACHE-QA.md)；首次真实平台只读与浏览器隔离场景见[数据中心验收](DATA-CENTER-LIVE-QA.md)。

前端 typecheck 检查类型，test 使用 Node 测试运行器检查来源隔离、追问摘要、默认 AI 问答及附加原文开关的请求边界，build 执行生产构建。默认 AI 问答及历次回答方式的桌面 / 手机浏览器结果见 [回答方式验收](ANSWER-OPTIONS-QA.md)。

后端（backend 目录）：

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试使用临时 SQLite 和随机测试密码，覆盖未登录、三种角色、CSRF、错误登录限流、会话过期 / 撤销、密码变更、重复账号、非法输入、UTF-8 大小与重启后资料读取。DeepSeek 测试使用模拟上游响应，覆盖数字无意义输入不调用、语义理解与重检、模型配置边界、多来源引用、错误编号、字段聚焦、加工章节召回、补充来源隔离、异常 / 截断输出和脱敏错误；真实服务及浏览器记录见 [DEEPSEEK-QA.md](DEEPSEEK-QA.md) 和 [FOLLOW-UP-QA.md](FOLLOW-UP-QA.md)。

浏览器验收命令与证据见 [AUTH-QA.md](AUTH-QA.md)。旧版知识库视觉记录见根目录 design-qa.md，其中仅本地文件能力的描述属于 2026-10-26 版本。


## 更新内置基础文档

用户提供的《中药基础知识（详解版）.docx》保存在 backend/resources/herbal-reference.docx，阅读数据为同目录 herbal-reference.json。两个文件部署时一并保留。原始 Word 的字节内容不作修改，正文按章节、段落与表格导入；通用 Word 上传解析仍未接入。

需替换指定文档时，在根目录运行（使用已安装的 Python 3.11+，脚本仅依赖标准库）：

```powershell
python backend/scripts/import_reference_document.py 'D:\资料\中药基础知识（详解版）.docx'
```

导入器遇到图片、脚注、尾注、修订、自动编号或合并单元格等尚未支持的结构时会停止，避免静默丢失内容。更新后运行后端测试并检查桌面与手机的章节、表格和原文下载。API 在每次请求时读取资源文件；首次增加接口后需重启已运行的后端服务。
