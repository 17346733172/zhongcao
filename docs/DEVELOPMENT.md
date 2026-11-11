# 开发与验证

## 环境与启动

Python 3.11+、Node.js 20.9+、pnpm 11。根目录启动后端.cmd 建立 backend/.venv 并配置首个管理员；启动前端.cmd 运行前端。两个终端均保持开启。

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

## 开发约定

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

## 处方检查接口与本地识别

安装后端 requirements.txt（含官方 PyPI 源、LangGraph、RapidOCR、PDFium、python-docx 与 multipart；完整版本受 requirements-lock.txt 约束），然后重启后端。复用已有 DEEPSEEK_API_KEY / BASE_URL / MODEL，不新增图片云服务密钥。模型随 OCR 依赖提供；本机验证为 Python 3.14，依赖元数据保留 Python 3.11+ 范围。

- `GET /api/prescriptions/status`：需登录及 knowledge:read，返回服务是否配置、支持格式与大小限制，不返回密钥。
- `POST /api/prescriptions/prepare`：multipart，提交 `file` 或 `text` 二选一，可附 `instruction`（500 字以内）与 `dose_scope`（`per_dose / total / unknown`，省略保持逐味口径；界面按用户要求默认发送 per_dose）。文件最多 10 MB，文字 2 万字符，PDF 8 页，整体请求上限 12 MB。返回读取方式、原文、识别提醒、意图、待核对处方和已执行节点；非处方 / 多个版本返回澄清，不自动检查。只处理正文和表格；DOCX 内嵌图片会明确提醒未识别。
- `POST /api/prescriptions/check`：JSON `{prescription, confirmed: true}`，总请求上限 128 KB。最多 100 味药；`prescription.dose_scope` 为整方口径，per_dose / total 在执行规则前统一各行，unknown / 省略则保留逐味口径。报告返回归一化后的实际处方；数值与单位不作换算。用户确认数据后执行规则并返回分级 findings、依据、范围、规则版本和局限，不调用模型改方。新增 `conclusion` 包含 status / result / detail / finding_codes / note，status 为 passed、not_passed、needs_information，decision_reasons 列明具体系统依据；十八反 / 已登记十九畏及数据异常优先不通过，真实信息缺失待补充，其他阻断项不通过，无阻断项通过本次系统辅助审核。Finding.blocking 为 false 时仅为持续提醒，不代表已排除临床风险。新增 `sections` 为固定 3.1—3.5 五节：每节包含 number / title / paragraphs / items / ordered，每条内容包含 lead（加粗前缀）/ text / children / sources；页面与复制均使用此结构，原元数据字段保留兼容。`missing_information` 始终返回数组（无缺失时为空），每项含 field / label / prompt；field 为患者字段或 `medicines.<零基行号>.<字段>`，只用于定位已存在的核对控件，具体清单也写入 3.1 sections，复制无需另行拼接。
- 三种角色均可使用个人处方流程，仍不能越权写共享资料；所有写请求沿用 `X-CSRF-Protection: 1` 和 Origin 校验。错误反馈不回显输入。无数据库写入、无检查点持久化，禁用该流程远程追踪。每进程最多两个处方任务。

本地 OCR 不保证手写、低清图片与小数点准确；界面原图对照和人工确认不可跳过。前端上传识别等待最多 180 秒，关闭弹窗取消浏览器等待，已经发出的后端模型调用可能继续完成。基础标识遮盖不等于完整匿名化，真实文件应先脱敏。

规则、来源及验收见 [处方 Agent](PRESCRIPTION-AGENT.md)。共享知识库 PDF / Word 解析仍未接入，不能把处方解析等同于共享资料上传成功。

### 仿真平台上传

模块边界、字段示例、两种认证和错误处理集中见 [两个项目的后端对接](DECOCTION-INTEGRATION.md)。

本草后端通过 `DECOCTION_BASE_URL` 连接仿真平台。默认使用本机 `http://127.0.0.1:8080`，若仿真平台直接以 FastAPI 启动，请使用其实际端口，避免与本草的 8000 端口冲突。启用接口鉴权时，在本草 `backend/.env` 设置 `DECOCTION_API_KEY`，并重启本草后端。密钥仅用于后端 `X-API-Key` 请求头。

使用服务器部署的平台时，`DECOCTION_BASE_URL` 应指向该服务器的实际接口入口。处方保存在接收实例的数据库中，本机实例与服务器实例各自保存数据。若入口返回 `WWW-Authenticate: Basic`，在本草 `backend/.env` 同时设置 `DECOCTION_HTTP_USERNAME` 和 `DECOCTION_HTTP_PASSWORD`，使用 HTTPS 入口并重启本草后端。网关凭据与 API Key 分开配置，均仅在后端读取。

`POST /api/prescriptions/check` 额外返回当前报告的 `simulation_upload_id`。检查结果页点击上传才调用 `POST /api/prescriptions/simulation`，请求包含 `upload_id`、`doses` 和逐味 `medicines`，沿用登录、`knowledge:read` 和 CSRF 校验。后端向仿真平台的 `POST /api/v1/prescriptions` 发送生成的外部编号和匿名编号、总剂数及药材名称、每剂克数、煎法枚举。患者字段、原始材料及报告正文留在本草流程内。

平台接收后处方进入待人工审核。工艺时间及包装参数使用平台默认值；支持的煎法仅映射至对应工序，处方中附带的具体时长不作为仿真参数。失败时保留报告，同一报告重试沿用编号，平台按外部编号防止重复录入。

计数单位「片」上传为 `unit="piece"` 和 `quantity_per_dose`，不填写或猜测 `grams_per_dose`。每剂量直接保留片数，总量除以总剂数；支持半片等正小数。平台保存原始片数，审核通过前补充 `herb_grams_per_dose`（按药名记录每剂实测克数），按实际重量计算水量。克 / 毫克继续沿用原有 `grams_per_dose` 协议。旧平台拒绝计数协议时明确提示更新接收端，不伪装上传成功。

连接和响应中断最多尝试 3 次，单次连接等待 10 秒、读取等待 15 秒，写入和连接池等待各 5 秒；前端为整个上传流程保留 120 秒。校验或认证拒绝直接返回反馈。连接失败日志仅记录尝试次数和异常类型，便于识别 HTTPS 握手超时。首次请求已写入但响应丢失时，后续相同编号的重复响应按已录入处理。

## 自动验证

### 数据中心读取

数据中心与上传共用 `DECOCTION_BASE_URL`、`DECOCTION_API_KEY`、`DECOCTION_HTTP_USERNAME` / `DECOCTION_HTTP_PASSWORD`，无需新增依赖或环境变量。修改代码后重启本草后端；修改配置也需重启。平台必须提供 `GET /api/v1/simulation` 和 `GET /api/v1/prescriptions`；不直接读取另一个项目的数据库。

- `GET /api/data-center/snapshot`：需要 `knowledge:read`，读取平台完整快照并仅返回界面需要的统计、时钟、设备、报警和批次摘要。
- `GET /api/data-center/prescriptions?offset=0&limit=20&status=approved`：同样要求登录，平台分页透传；`status` 可省略或为 `pending_review / approved / rejected`，`offset >= 0`，`limit` 为 1–200。每页包含完整处方信息，不只限于本草上传的记录。

概览与设备每次读取结束后等待 15 秒再更新；处方在进入标签、筛选、翻页和手动刷新时读取。界面手动刷新同时更新当前处方页和快照。关闭取消等待及刷新计时。平台故障、认证失败、接口 / 格式不匹配返回清晰的 502 提示，不回显响应正文、地址或凭据。请求不跟随认证重定向，禁止使用服务器环境代理；不修改平台时钟、处方、设备或报警。

真实平台只读与浏览器隔离场景的验收见 [数据中心验收](DATA-CENTER-LIVE-QA.md)。

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
