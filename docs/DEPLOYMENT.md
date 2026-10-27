# 构建与部署

## 当前状态

本地 Next.js + FastAPI 应用，默认分别监听 127.0.0.1:3000、127.0.0.1:8000，未发布线上。必须同时运行两个服务。

## 本地生产运行

后端先按 README 安装依赖、配置管理员，运行 Uvicorn。前端在 frontend 执行：

```powershell
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test
pnpm build
pnpm start
```

dev 和 start 共用 3000 端口，启动其中一个即可。前端代理 /api/*，不应使用静态导出。

## 托管配置

需要支持 Node.js 20.9+ / Next.js 16 和 Python 3.11+ 的运行环境；SQLite 所在目录必须持久保存。当前实现面向单机共享资料库，没有分布式存储或多租户隔离。

生产 HTTPS 下设置后端 COOKIE_SECURE=true，将 ALLOWED_ORIGINS 设置为真实前端域名；前端 BACKEND_URL 指向内部 FastAPI 地址，修改后重新构建。后端不开放跨域 CORS，浏览器统一通过前端同源访问。

只在可信代理拓扑下另行启用代理头。默认 Uvicorn 使用 --no-proxy-headers，登录限流按连接 IP 和账号计数。备份 SQLite 应使用 SQLite backup API，或停止服务后保存完整数据库文件；在线直接复制主文件可能遗漏 WAL 中的数据。

## 发布验收

验证登录、三种权限、账号停用、改密、退出、文本持久化、移动布局和控制台。真实 AI、PDF / Word 解析与会话持久化仍未实现，界面保留演示标识。

只有用户明确请求发布或分享时才执行线上部署。
