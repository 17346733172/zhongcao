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
| frontend/src/app/globals.css、workspace.css、auth.css | 设计变量、知识库布局与登录 / 管理布局 |
| frontend/src/components/authenticated.tsx | 会话检查、退出、账号导航和页面权限门禁 |
| frontend/src/components/login-form.tsx | 登录表单、错误和忙碌反馈 |
| frontend/src/components/user-management.tsx | 创建账号、角色、停用和重置密码 |
| frontend/src/components/account-settings.tsx | 当前账号信息与改密 |
| frontend/src/components/knowledge-workspace.tsx | 资料加载、问答模式 / 请求取消与文件状态编排 |
| frontend/src/components/sidebar.tsx、upload-panel.tsx | 导航、账号入口与按权限展示资料操作 |
| frontend/src/components/conversation-view.tsx、source-dialog.tsx | 回答、引用和完整原文 |
| frontend/src/components/reference-document-dialog.tsx、document-content.tsx | 正式基础资料加载、重试和章节 / 表格阅读 |
| frontend/src/lib/reference-document.ts | 内置资料元信息与只读 API 请求 |
| backend/app/reference_document.py、resources/ | 内置文档正文与 Word 原文件，仅经鉴权接口读取 |
| backend/scripts/import_reference_document.py | 从指定 Word 一次性生成阅读数据并保留原文件 |
| frontend/src/lib/api.ts | 同源请求、错误转换与账号类型 |
| frontend/src/lib/types.ts、demo-data.ts | 资料 / 来源类型、知识库配置及空的初始状态 |
| frontend/src/lib/chat-api.ts | AI 状态与带取消 / 超时的问答请求 |
| backend/app/retrieval.py、chat.py | 服务端关键词 / 炮制章节检索、字段聚焦、DeepSeek 调用、来源类别与引用校验 |
| frontend/src/lib/knowledge-answer.ts | 中文分词、章节匹配与真实原文摘录；无命中不生成引用 |
| frontend/next.config.ts | /api/* 代理至 FastAPI，后端地址仅在服务端使用 |
| backend/app/config.py、database.py | 环境配置、SQLite 连接与幂等建表 |
| backend/app/security.py、schemas.py | Argon2id、令牌摘要、权限映射与输入模型 |
| backend/app/main.py | 应用工厂、会话、账号与共享资料 API |
| backend/app/cli.py | 终端交互式创建首个管理员 |
| backend/tests/test_auth.py、test_chat.py | 角色越权、会话撤销、密码、资料持久化与 AI 来源 / 异常验证 |

## 数据流与权限边界

浏览器通过同源 /api 请求 → Next.js 转发到本机 FastAPI → 后端读取 HttpOnly 会话 Cookie → 根据数据库中账号当前状态和角色鉴权 → 执行资料或账号操作。

会话原始随机令牌仅在 Cookie 中，数据库存储 SHA-256 摘要；密码存储 Argon2id 哈希。会话默认 8 小时；每次请求检查过期与停用状态。登录错误统一反馈，单账号与连接 IP 在 5 分钟内最多允许 8 次尝试。默认不信任代理转发的 IP。

所有写接口需要 X-CSRF-Protection: 1，自定义头配合无跨域许可阻止跨站表单请求，并校验存在的 Origin 是否允许。生产 HTTPS 配置 COOKIE_SECURE=true。角色更新、停用和密码变更撤销目标账号全部会话。当前管理员不能修改自己的角色或停用自己。

所有登录用户读取同一个中药基础资料库；编辑员和管理员可添加、删除文本，只有管理员可管理账号。不存在公开注册、客户端指定登录角色或客户端保存令牌的流程。

## 持久化与演示边界

SQLite 默认位于 backend/data/bencao.db，保存用户、会话、登录尝试与共享文本。目录不进入版本库。SQL 使用参数绑定。

MD / TXT 在浏览器读取 UTF-8 后经 API 保存原文；后端独立校验类型、文件名、空白及 10 MB UTF-8 字节上限。请求体也有上限。PDF / Word 暂不上传。demo 字段用于隔离示例资料（默认不再预置），检索排除所有 demo 条目；stored 标识持久化资料。

内置《中药基础知识（详解版）》通过 GET /api/reference-document 与 /api/reference-document/file 读取，均校验 knowledge:read。原文件和结构化正文保存在 backend/resources，未放入前端公开资源目录或客户端包；一次性导入保留原文章节、段落和表格，并记录原文件 SHA-256。它独立于共享上传列表；工作区加载时与共享文本一同经鉴权接口读取，参与关键词原文检索，引用保留结构化正文与 Word 下载入口。

原文检索模式由 knowledge-answer.ts 根据关键词匹配真实正文生成摘录。按正式文档的章节聚合药材条目，中文分词去除问句虚词；只返回正相关结果，数字等未命中查询不兜底到示例或其他段落。会话只在页面内存中，不持久化。AI 模式的 /api/chat 只接受当前问题，经 knowledge:read 与 CSRF 验证后读取共享正文，由 retrieval.py 按关键词与章节选择最多 3 个片段，再由 chat.py 调用配置的 DeepSeek 服务。密钥只在后端环境读取；每个发送片段最多 3000 字符。输出 JSON schema 与来源类别 / 编号校验后，由服务端关联原文；未命中不请求模型。有相关资料但内容不足时允许模型一般知识补充：document 段有真实引用，ai_supplement 段无文档引用，界面及复制内容均保留明确标签。模型补充没有联网核实。提示词将资料中的指令视为不可信参考文本，引用编号校验不保证事实正确性。向量语义检索、通用 PDF / Word 上传解析、流式回答、个人知识库隔离与迁移框架未实现。
