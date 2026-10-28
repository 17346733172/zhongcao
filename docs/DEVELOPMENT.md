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

## DeepSeek 配置与问答接口

在 backend/.env 的 DEEPSEEK_API_KEY 后填入本机密钥，保存后重启后端。保持 .env 在 Git 忽略列表中；不要发送密钥到聊天、浏览器代码或提交记录。默认地址 https://api.deepseek.com，默认模型 deepseek-flash。地址支持带 /v1 的兼容路径；正式服务要求 HTTPS，HTTP 仅允许回环地址用于测试。系统环境变量优先于 .env。更换配置需重启后端，页面刷新后重新检查状态。

- GET /api/ai/status：需要 knowledge:read，返回 provider、configured（仅表示已填写密钥）、model，不返回密钥。
- POST /api/chat：需要 knowledge:read 和 X-CSRF-Protection: 1，接受 {"question":"问题","history":[{"question":"上一轮问题","answer":"上一轮摘要"}]}。question 长度 1–2000 字；history 可省略，最多 5 轮，每轮 question 1–500 字、answer 最多 1000 字。请求体上限 64 KB；客户端不能指定角色、资料、模型或密钥。
- conversation_context.py 根据当前问题和受限历史解析省略主题，再检索正式基础文档及 SQLite 中的共享文本；明确新药材优先，数字等无关输入不复用旧主题，缺主题或单数指代多个主题时返回 mode=clarification、空正文 / 来源。
- 后端读取正式基础文档与 SQLite 中的共享文本，按药材章节或关键词选择最多 3 个正相关片段，每个最多发送 3000 字符。功效 / 用量等问题只提供相关字段及原文注意事项；饮片加工类问题补检炮制总论中的相关原文。常规未命中自然语言可先进入下述语义理解；重检无资料返回 mode=no_match、空正文和空引用，不调用回答生成。
- question_understanding.py：规则及关键词没有命中的自然语言问题，向同一模型单独发送当前问题、受限历史及服务端最近主题（不发送原文），得到 follow_up / standalone / clarify / unrelated 的严格 JSON。最多一次、512 tokens，10 秒网络阶段超时；拒绝多余字段及缺失 query，追问主题须与最近主题一致；歧义返回 clarification，不能把语义解析当作证据。中文新话题可重新整理后重检，数字 / 代码式无意义输入不调用模型。页面说明「我理解你是在问：…」，保留用户原始问题。语义阶段和生成阶段共用并发名额。
- 使用 httpx 调用 /chat/completions，JSON 输出、关闭 thinking、非流式，最多输出 2048 tokens。单进程最多同时处理 4 个模型请求；连接超时 10 秒、网络读写等阶段超时 30 秒。
- 输出经严格 schema、origin 和引用编号校验。document 段要求至少一个有效引用；ai_supplement 段要求空 citations，前端显示「AI 补充，非文档原文」，不显示文档引用。只有实际被引用的文档才返回 sources；sourceIndex 在补充段中省略，sourceIndices=[]。实际原文、资料名和来源索引由服务端附加，补充只来自模型自身一般知识，并未联网核实。异常 / 截断输出返回错误，前端不把它保存成回答，也不自动降级为假回答。资料内容作为不可信参考文本处理。
- 前端 AI 请求最长等待 45 秒；新建 / 切换会话会终止浏览器等待，避免旧回答写入新会话。已经发出的上游调用可能继续完成并产生费用。

AI 模式向配置的云服务发送问题及相关片段，优先依据资料，相关资料未覆盖的内容允许用模型一般知识单独补充；自然语言首次未命中可以先调用一次语义整理，再按整理后的完整问题重检；仍无相关片段时返回未找到，不调用回答生成。原文检索模式在浏览器直接摘录，不调用模型。AI 问题结合当前会话最近 5 轮承接，前端通过 resolvedQuestion 保留连续省略的主题；历史只辅助理解，不作为事实或引用来源，每轮重检原文。原文检索模式仍独立检索。基础关键词检索的召回范围有限，向量检索、流式回答与会话持久化仍需后续实现。官方配置参考：[接入说明](https://api-docs.deepseek.com/quick_start/agent_integrations/)、[Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion/)、[JSON 输出](https://api-docs.deepseek.com/guides/json_mode/)。

## 自动验证

前端 typecheck 检查类型，test 使用 Node 测试运行器检查来源隔离、追问摘要及 AI / 原文独立开关的组合与请求边界，build 执行生产构建。独立开关的桌面 / 手机浏览器结果见 [回答方式验收](ANSWER-OPTIONS-QA.md)。

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
