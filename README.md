# 本草知问 · 中药知识库问答

面向整理中药资料并据此提问的用户。沿用已选第 3 张视觉方案，提供 **Python / FastAPI 后端、真实登录、角色权限和 DeepSeek 资料问答**。

## 当前功能

- 账号密码登录、退出、个人改密；登录会话默认有效 8 小时。
- 管理员创建账号、分配角色、停用 / 启用账号、重置密码。无公开注册，无默认密码。
- MD / TXT 文本保存到 SQLite 共享知识库，刷新和服务重启后仍可读取。
- 正式中药基础文档与共享文本的关键词检索；配置 DeepSeek 后优先根据检索资料回答；资料之外的一般知识单独标为「AI 补充，非文档原文」，不挂文档引用，也可切回原文摘录。未命中不调用模型，不返回无关片段或示例引用。
- 当前页历史会话、原文查看、复制；桌面和手机适配。生成失败保留问题，切换会话取消旧请求。
- 点击左侧「中药基础资料」阅读用户提供的《中药基础知识（详解版）》全文，保留章节、段落与 7 张表格，支持章节定位和 Word 原文件下载；保留当前对话与草稿。正文与下载均需登录。

| 角色 | 查看资料与提问 | 添加 / 移除资料 | 创建账号与分配权限 |
| --- | --- | --- | --- |
| 普通用户 viewer | 是 | 否 | 否 |
| 编辑员 editor | 是 | 是 | 否 |
| 管理员 admin | 是 | 是 | 是 |

权限由 FastAPI 每次请求校验。角色调整、账号停用和密码重置会撤销该账号的所有旧会话；修改自己的密码后也需要重新登录。

**当前使用关键词检索 + DeepSeek 生成回答的初版 RAG。** 向量语义检索、通用 PDF / Word 上传解析、会话持久化、流式回答和线上部署仍待接入。已保存文本供本系统所有登录用户查看，暂不区分个人知识库或租户。

## 前后端分离

- `frontend/`：Next.js / React / TypeScript，负责登录、知识库和账号管理界面，独立安装依赖和启动。
- `backend/`：Python / FastAPI，负责认证、权限校验、账号和资料 API 及 SQLite，独立安装依赖和启动。
- 前后端通过 HTTP API 通信；本地由 Next.js 将 `/api/*` 同源代理到 FastAPI，业务逻辑和数据库访问集中在后端。前端通过服务端 `BACKEND_URL` 配置后端地址。

## 本地运行

环境：Python 3.11+、Node.js 20.9+、pnpm 11。

1. 双击根目录 **启动后端.cmd**。首次运行会建立独立虚拟环境、安装依赖，并提示设置管理员账号与密码（至少 10 位，输入时不显示）。保持终端开启。
2. 双击 **启动前端.cmd**，保持终端开启。
3. 打开 [登录页面](http://127.0.0.1:3000/login)，使用刚设置的账号登录。从左下角「账号管理」创建其他账号并分配角色。

两个脚本均支持 `--check` 检查运行环境。后端接口文档：[Swagger UI](http://127.0.0.1:8000/docs)。写接口需要 `X-CSRF-Protection: 1` 请求头；浏览器客户端已自动携带。

手动启动后端：

```powershell
cd D:\本草\backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m app.cli create-admin
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

另一终端启动前端：

```powershell
cd D:\本草\frontend
pnpm install --frozen-lockfile
pnpm dev
```

可将 backend/.env.example 复制为 backend/.env 修改数据库位置、允许来源及 Cookie 配置；启动时自动读取，已有系统环境变量优先。frontend/.env.example 可复制为 frontend/.env.local 修改服务端 `BACKEND_URL`，修改后须重启开发服务或重新构建。不要将密码和实际 .env 提交到 Git。

## 配置 DeepSeek

将 backend/.env.example 复制为 backend/.env，在本机填写 DEEPSEEK_API_KEY；不要在聊天或源码中发送密钥。默认 DEEPSEEK_BASE_URL=https://api.deepseek.com、DEEPSEEK_MODEL=deepseek-flash，均可由后端配置。保存后重启后端，刷新页面；配置存在时默认选择「AI 回答」，未配置时可使用「原文检索」。

密钥仅在后端读取。AI 模式会把当前问题和最多 3 个检索片段发送给所配置的 DeepSeek 服务，每个片段最多 3000 字符。后端只接受问题，从登录用户有权读取的共享知识库检索，并校验回答中引用的来源编号。文档段必须有有效引用；AI 补充段必须无文档引用，复制时保留类别。AI 补充来自模型自身知识，未联网核实；引用及标签不能代替事实和医学准确性检查。

配置与接口细节见 [开发说明](docs/DEVELOPMENT.md)，验证记录见 [DeepSeek 接入验收](docs/DEEPSEEK-QA.md) 和 [混合回答验收](docs/HYBRID-ANSWER-QA.md)。

## 验证

在 frontend 运行 `pnpm typecheck`、`pnpm test`、`pnpm build`。`pnpm start` 运行构建后的前端，不能和 dev 同时占用 3000 端口。

在 backend 运行：

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

前后端联调结果见 [接口检查记录](docs/API-QA.md)；浏览器验收与证据见 [登录与权限验收](docs/AUTH-QA.md)。开发与配置细节见 [开发说明](docs/DEVELOPMENT.md)。

## 项目目录

```text
本草/
├── README.md、AGENTS.md、DESIGN.md、TODO.md、CHANGELOG.md
├── 启动前端.cmd、启动后端.cmd
├── docs/                       # 产品、架构、开发与验收
├── design/                     # 参考图与界面截图
├── backend/
│   ├── app/                    # FastAPI、SQLite、认证、账号与资料接口
│   ├── tests/                  # 接口与权限测试
│   ├── requirements*.txt       # 运行、测试依赖与锁定版本
│   └── data/                   # 本地数据库（不提交）
└── frontend/
    ├── src/app/                # 知识库 /、登录 /login、账号 /account、管理 /admin
    ├── src/components/         # 页面交互与组件
    ├── src/lib/                # API、类型、演示适配
    └── scripts/                # 原文边界与浏览器验收
```

## 资料使用边界

单个文本文件最多 10 MB，采用 UTF-8 编码。空文件、超限、无权限和保存失败有明确反馈。PDF / Word 显示「未上传 · 待接入解析服务」，不会伪造成功。

内置基础资料由指定 Word 原文件一次性导入，独立于右侧上传列表；通用 Word 上传解析仍待接入；内置资料支持阅读、下载和关键词原文检索。更新内置资料的方法见 [开发说明](docs/DEVELOPMENT.md)。

原文检索模式直接摘录关键词命中的正文；AI 回答模式通过后端再次检索并调用 DeepSeek 按问题归纳；有相关资料但信息不足时允许单独补充一般知识，不使用聊天历史推断当前问题。功效等明确字段问题会聚焦对应内容，炮制 / 饮片问题会一并查找相关总论章节。当前关键词匹配尚不等同于向量语义检索。首页不预置模拟文件或陈皮回答，检索结果只引用真实资料。回归记录见 [检索修复验收](docs/RETRIEVAL-QA.md)。聊天记录只在当前页面内保留，退出或刷新后清除。

## 文档

- [协作规范](AGENTS.md)、[设计规范](DESIGN.md)、[开发计划](TODO.md)、[更新记录](CHANGELOG.md)
- [产品范围](docs/PROJECT-SPEC.md)、[架构](docs/ARCHITECTURE.md)、[组件规范](docs/COMPONENT-GUIDELINES.md)
- [页面结构](docs/PAGE-STRUCTURE.md)、[开发流程](docs/DEVELOPMENT.md)、[部署](docs/DEPLOYMENT.md)、[Registry](docs/REGISTRY.md)
