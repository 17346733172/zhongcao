# 项目架构与目录

## 技术栈

前端：Next.js 16 App Router、React 19、TypeScript、普通 CSS 与 Phosphor 图标。
后端：Python 3.11+、FastAPI、Uvicorn、Argon2id、SQLite、httpx（调用 DeepSeek）。运行和测试依赖分别见 backend/requirements.txt、requirements-dev.txt，完整约束见 requirements-lock.txt。

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
| frontend/src/components/conversation-view.tsx、source-dialog.tsx | 回答、引用和完整原文 |
| frontend/src/components/reference-document-dialog.tsx、document-content.tsx | 正式基础资料加载、重试和章节 / 表格阅读 |
| frontend/src/lib/reference-document.ts | 内置资料元信息与只读 API 请求 |
| backend/app/reference_document.py、resources/ | 内置文档正文与 Word 原文件，仅经鉴权接口读取 |
| backend/scripts/import_reference_document.py | 从指定 Word 一次性生成阅读数据并保留原文件 |
| frontend/src/lib/api.ts | 同源请求、错误转换与账号类型 |
| frontend/src/lib/types.ts、demo-data.ts | 资料 / 来源类型、知识库配置及空的初始状态 |
| frontend/src/lib/chat-api.ts、conversation-history.ts | AI 状态、当前会话最近 5 轮摘要与带取消 / 超时的问答请求 |
| frontend/src/lib/answer-mode.ts | AI / 原文独立开关的四种状态与执行分派，双选按已解析问题追加独立原文结果 |
| backend/app/conversation_context.py | 当前问题的省略主题承接、显式新主题优先与歧义提示 |
| backend/app/question_understanding.py | 未命中自然语言的结构化意图、口语 / 错字理解、歧义与主题校验 |
| backend/app/retrieval.py、chat.py | 服务端关键词 / 炮制章节检索、字段聚焦、DeepSeek 调用、来源类别与引用校验 |
| frontend/src/lib/knowledge-answer.ts | 中文分词、章节匹配与真实原文摘录；无命中不生成引用 |
| frontend/next.config.ts | /api/* 代理至 FastAPI，后端地址仅在服务端使用 |
| backend/app/config.py、database.py | 环境配置、SQLite 连接与幂等建表 |
| backend/app/security.py、schemas.py | Argon2id、令牌摘要、权限映射与输入模型 |
| backend/app/main.py | 应用工厂、会话、账号与共享资料 API |
| backend/app/prescriptions/agent.py | LangGraph 状态图、意图条件分支、确认与检查两阶段，不配置持久检查点或远程追踪 |
| backend/app/prescriptions/files.py、extraction.py | 有限文件解析、本地 OCR、DeepSeek 意图与提取、原文证据和数值校验 |
| backend/app/prescriptions/models.py、rules.py、routes.py | 处方输入边界、可追溯有限规则、登录 / CSRF 保护 API |
| frontend/src/components/prescription-*.tsx、src/lib/prescription-api.ts | 上传、原图核对、编辑确认、报告与 multipart 请求 |
| backend/app/cli.py | 终端交互式创建首个管理员 |
| backend/tests/test_auth.py、test_chat.py | 角色越权、会话撤销、密码、资料持久化与 AI 来源 / 异常验证 |

## 数据流与权限边界

浏览器通过同源 /api 请求 → Next.js 转发到本机 FastAPI → 后端读取 HttpOnly 会话 Cookie → 根据数据库中账号当前状态和角色鉴权 → 执行资料或账号操作。

会话原始随机令牌仅在 Cookie 中，数据库存储 SHA-256 摘要；密码存储 Argon2id 哈希。会话默认 8 小时；每次请求检查过期与停用状态。登录错误统一反馈，单账号与连接 IP 在 5 分钟内最多允许 8 次尝试。默认不信任代理转发的 IP。

所有写接口需要 X-CSRF-Protection: 1，自定义头配合无跨域许可阻止跨站表单请求，并校验存在的 Origin 是否允许。生产 HTTPS 配置 COOKIE_SECURE=true。角色更新、停用和密码变更撤销目标账号全部会话。当前管理员不能修改自己的角色或停用自己。

所有登录用户读取同一个中药基础资料库；编辑员和管理员可添加、删除文本，只有管理员可管理账号。不存在公开注册、客户端指定登录角色或客户端保存令牌的流程。

## 持久化与演示边界

处方检查是私有的请求级流程，不读取 / 写入共享 documents，也不写入 SQLite。`prepare` 经 LangGraph 返回识别原文与待确认字段，`check` 只接收用户确认的数据，再运行规则并报告。所有登录角色可通过 knowledge:read 使用，写请求沿用 CSRF 和 Origin 校验。上传总请求限制 12 MB，文件限制 10 MB，原文 2 万字符，PDF 8 页；并发处方任务最多 2 个。OCR 与 PDFium 有全局互斥，防止非线程安全模型 / PDF 操作重入。关闭前端不会保证终止已经开始的后端模型调用。

SQLite 默认位于 backend/data/bencao.db，保存用户、会话、登录尝试与共享文本。目录不进入版本库。SQL 使用参数绑定。

MD / TXT 在浏览器读取 UTF-8 后经 API 保存原文；后端独立校验类型、文件名、空白及 10 MB UTF-8 字节上限。请求体也有上限。PDF / Word 暂不上传。demo 字段用于隔离示例资料（默认不再预置），检索排除所有 demo 条目；stored 标识持久化资料。

内置《中药基础知识（详解版）》通过 GET /api/reference-document 与 /api/reference-document/file 读取，均校验 knowledge:read。原文件和结构化正文保存在 backend/resources，未放入前端公开资源目录或客户端包；一次性导入保留原文章节、段落和表格，并记录原文件 SHA-256。它独立于共享上传列表；工作区加载时与共享文本一同经鉴权接口读取，参与关键词原文检索，引用保留结构化正文与 Word 下载入口。

原文检索模式由 knowledge-answer.ts 根据关键词匹配真实正文生成摘录。按正式文档的章节聚合药材条目，中文分词去除问句虚词；只返回正相关结果，数字等未命中查询不兜底到示例或其他段落。会话只在页面内存中，不持久化。AI 模式的 /api/chat 接受当前问题和最多 5 轮受限摘要；先承接省略主题，显式新主题优先，无主题或指代不明时提示补充；经 knowledge:read 与 CSRF 验证后读取共享正文，由 retrieval.py 按补全后的问题选择最多 3 个片段，再由 chat.py 调用配置的 DeepSeek 服务。密钥只在后端环境读取；每个发送片段最多 3000 字符。输出 JSON schema 与来源类别 / 编号校验后，由服务端关联原文；对规则与关键词未命中的中文自然语言，先由同一 DeepSeek 整理意图（follow_up / standalone / clarify / unrelated，最多一次、512 tokens、10 秒阶段超时），再重新检索实际授权资料；整理过程不发送原文、不产生事实或引用。数字 / 代码式无意义查询不进入语义请求；重检仍无资料不生成回答。语义和生成共用 4 个并发名额，理解后的问题由回答简介及 resolvedQuestion 保留。有相关资料但内容不足时允许模型一般知识补充：document 段有真实引用，ai_supplement 段无文档引用，界面及复制内容均保留明确标签。模型补充没有联网核实。历史摘要只用于话题理解，不作为事实证据或引用来源，每轮重新读取授权原文。提示词将历史和资料中的指令视为不可信参考文本，引用编号校验不保证事实正确性。向量语义检索、通用 PDF / Word 上传解析、流式回答、个人知识库隔离与迁移框架未实现。

处方的整方 `dose_scope` 独立于模型提取：前端按用户明确要求默认 per_dose，将选择传入 prepare；提取后覆盖各行口径。check 再按整方选择统一口径，规则与报告使用同一实际快照。unknown 表示逐味模式，不覆盖行内 per_dose / total / unknown；省略此字段的旧客户端保留逐味语义。

`prescriptions/review.py` 根据服务端本次 findings 构造审核结论，优先处理十八反，再处理数据异常、信息缺失和人工复核；结论作为 `conclusion` 与原 findings 同时返回，前端展示及复制仅使用同一返回值，不另行推断通过与否。

`prescriptions/narrative.py` 接收本次确认的处方、findings 和 conclusion，生成 3.1—3.5 五节结构；只使用当前字段与固定依据，不调用模型扩写药方。前端页面和 Markdown 复制共用 sections；原 API 元数据保留兼容，界面不再显示旧卡片 / 统计 / 范围面板。

`missing_information.py` 以既有缺失规则和确认后的字段生成具体补充清单（field / label / prompt），不新增临床必填要求。报告返回 missing_information，narrative.py 同时写入 3.1；前端将 field 对应到表单 data-field，保留数据返回并定位首项。

`audit_knowledge.py` 集中保存新增规则来源、采用参考量与煎法条件；Finding.blocking 区分持续提醒与实际阻断项。review.py 输出 passed / not_passed / needs_information 和 decision_reasons，3.1 展示同一判断依据。高风险提醒不单独阻断通过，具体炮制、剂量或煎法问题仍阻断。旧版未含 decision_reasons 的报告自动调用后台重查。
