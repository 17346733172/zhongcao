# 登录与权限验收

日期：2026-10-27。结果：通过。沿用已选第 3 张视觉方案的颜色、字体与品牌，扩展登录和账号页面。

## 自动验证

- `frontend: pnpm typecheck`：通过。
- `frontend: pnpm test`：3 项来源边界测试通过。
- `frontend: pnpm build`：通过，生成 /、/login、/account、/admin。
- `backend: .venv\Scripts\python.exe -m unittest discover -s tests -v`：14 项通过。
- 根目录 `启动后端.cmd --check` 与 `启动前端.cmd --check`：通过。

后端覆盖未登录、三种角色越权、Cookie 属性与令牌摘要、过期及伪造会话、退出撤销、CSRF 与外域请求、错误登录限流、重复账号与输入校验、密码修改 / 重置、角色与停用后的撤销、共享文本跨应用实例读取、UTF-8 字节大小、首次管理员配置，以及并发管理员变更时保留可用管理员。

当前 Starlette 测试客户端会提示 httpx 兼容路径弃用；现有测试成功运行，后续可迁移至 httpx2。未对生产网络、并发负载、所有浏览器版本或线上部署作验证。

## 浏览器流程

使用本机 Edge，桌面 1487 × 1058、手机 390 × 844、平板 768 × 1024。验收使用独立 SQLite 和随机临时密码，不创建实际项目管理员。

1. 未登录进入管理页会跳转登录，错误密码有真实反馈；管理员可登录。
2. 管理员通过页面创建编辑员和普通用户。
3. 编辑员上传文本后显示「已保存 · 共享」；刷新仍可查看，原文与摘录保持一致。
4. 普通用户可读取该文本，界面没有上传、移除和账号管理操作；直接调用管理账号和写资料 API 均返回 403；进入 /admin 返回知识库。
5. 管理员停用编辑员，编辑员原登录立即失效。
6. 重新启用后，编辑员可重新登录并移除资料；其他用户刷新看到资料移除。
7. 普通用户修改自己的密码后重新登录；退出后返回受保护页仍需登录。
8. 手机登录、资料抽屉、导航和管理员页面可用；桌面、手机、平板无横向溢出。抽屉支持 Escape 和键盘焦点。
9. 无未处理的浏览器页面异常。401 / 403 为上述负向权限检查的预期响应。

记录：[结构化结果](../design/auth-qa-result.json)。

截图已人工检查：

- [桌面登录](../design/login-desktop.png)、[手机登录](../design/login-mobile.png)
- [桌面账号管理](../design/admin-desktop.png)、[手机账号管理](../design/admin-mobile.png)
- [编辑员工作区](../design/editor-workspace.png)、[普通用户工作区](../design/viewer-workspace.png)、[手机工作区](../design/viewer-mobile.png)

## 复现浏览器验收

先安装前后端依赖并完成 `pnpm build`，停止已有 3000 / 8000 服务。根目录执行：

```powershell
New-Item -ItemType Directory -Force backend/.qa/browser
Set-Content backend/.qa/browser/package.json '{"name":"bencao-local-browser-qa","private":true}' -Encoding utf8
pnpm --dir backend/.qa/browser add playwright@1.56.0
node frontend/scripts/check-auth-browser.mjs
```

[验收脚本](../frontend/scripts/check-auth-browser.mjs) 自动启动隔离数据库的后端和生产前端，完成流程并关闭服务，更新截图。临时工具、数据库和日志留在忽略的 backend/.qa/，不会进入版本库。默认使用已安装的 Edge，可用 BROWSER_EXECUTABLE 环境变量指定其他 Chromium 浏览器路径。

## 当前边界

已实现账号、会话与共享文本持久化；所有登录用户共用中药基础资料库。AI、PDF / Word 解析、聊天持久化、个人资料隔离及线上部署仍待接入。
