# 本草知问 · 中药知识库问答

面向整理中药资料并据此提问的用户。沿用已选第 3 张视觉方案，新增 **Python / FastAPI 后端、真实登录和角色权限**。

## 当前功能

- 账号密码登录、退出、个人改密；登录会话默认有效 8 小时。
- 管理员创建账号、分配角色、停用 / 启用账号、重置密码。无公开注册，无默认密码。
- MD / TXT 文本保存到 SQLite 共享知识库，刷新和服务重启后仍可读取。
- 知识库、历史会话、问答演示、引用与原文查看、复制；桌面和手机适配。

| 角色 | 查看资料与提问 | 添加 / 移除资料 | 创建账号与分配权限 |
| --- | --- | --- | --- |
| 普通用户 viewer | 是 | 否 | 否 |
| 编辑员 editor | 是 | 是 | 否 |
| 管理员 admin | 是 | 是 | 是 |

权限由 FastAPI 每次请求校验。角色调整、账号停用和密码重置会撤销该账号的所有旧会话；修改自己的密码后也需要重新登录。

**当前仍未接入真实 AI、PDF / Word 解析、会话持久化和线上部署。** 问答为原文摘录或明确标识的演示回答。已保存文本供本系统所有登录用户查看，暂不区分个人知识库或租户。

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

## 验证

在 frontend 运行 `pnpm typecheck`、`pnpm test`、`pnpm build`。`pnpm start` 运行构建后的前端，不能和 dev 同时占用 3000 端口。

在 backend 运行：

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

浏览器验收与证据见 [登录与权限验收](docs/AUTH-QA.md)。开发与配置细节见 [开发说明](docs/DEVELOPMENT.md)。

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

本地摘录逻辑尚不等同于语义检索或大模型回答。示例内容单独标识，真实文本不会混入示例来源。聊天记录只在当前页面内保留，退出或刷新后清除。

## 文档

- [协作规范](AGENTS.md)、[设计规范](DESIGN.md)、[开发计划](TODO.md)、[更新记录](CHANGELOG.md)
- [产品范围](docs/PROJECT-SPEC.md)、[架构](docs/ARCHITECTURE.md)、[组件规范](docs/COMPONENT-GUIDELINES.md)
- [页面结构](docs/PAGE-STRUCTURE.md)、[开发流程](docs/DEVELOPMENT.md)、[部署](docs/DEPLOYMENT.md)、[Registry](docs/REGISTRY.md)
