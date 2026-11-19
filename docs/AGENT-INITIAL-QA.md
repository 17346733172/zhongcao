# AI Agent 初始页布局验收

日期：2026-11-19。

按用户选定的[左侧参考](../design/agent-initial-qa/reference.png)调整 AI Agent 初始状态：采用网格内容区及底部白色输入栏，移除[原初始页](../design/agent-initial-qa/before.png)居中的欢迎标题和悬浮输入卡片。参考图处于已回答状态，本次将其布局用于空会话，不复制其他产品的功能导航、制造设备示例及业务数据；本草已有导航、页头、处方检查与服务说明继续保留。

## 修改

- `ConversationView` 不再渲染欢迎大标题，为辅助技术保留空会话操作说明。
- `chat-body` 在空会话和回答状态使用同一网格样式，移除居中布局条件。输入区在底部通栏显示，文本框高 74px，按钮采用紧凑矩形，手机操作区换行。
- 输入区高度始终由 ResizeObserver 读取，初始与回答状态不切换观察逻辑。保留主栏统一滚动、阅读位置、弹窗背景锁定与此前外层滚动修复。

## 浏览器验证

使用本机 Chrome 隔离上下文及明确标记的模拟账号 / API 响应，没有调用真实模型、提交处方或写入仿真平台。六种窗口全部通过：1280×858、1830×900、1440×1000、390×844、320×844、1280×600，deviceScaleFactor=1。

- 初始页没有可见欢迎大标题，空内容区填满可用高度，输入区底边与视口底边对齐；文本框高 74px，无横向溢出，无需初始滚动。
- 空内容禁用发送，输入后可发送，Shift+Enter 换行且不请求回答；打开 / 关闭处方检查后保留草稿。
- 两轮各 65 段回答及图表可以完整阅读，只有 `.main-panel` 纵向滚动；附加页面元素与键盘聚焦不产生整页额外滚动。
- 总览 / Agent 切换保留草稿和阅读位置；引用弹窗、图表数据展开、登录和账号页自然滚动正常，无 pageerror。

[完整验证结果](../design/agent-initial-qa/results.json)。已打开查看[完整同图对照](../design/agent-initial-qa/comparison-full.png)、[输入栏同图对照](../design/agent-initial-qa/comparison-footer.png)及[320px 初始页](../design/agent-initial-qa/initial-320-844.png)，视觉检查详见根目录 [design-qa.md](../design-qa.md)。

`pnpm typecheck` 和 `pnpm test` 的 36 项前端回归通过；隔离目录的 `pnpm build --webpack` 通过。为降低本机内存压力，仅在构建副本设置 `experimental.cpus=1`，项目配置未变。首次构建因已有的 Next.js 16.4.3 安全提示退出，重试后完成，依赖未升级；安全升级继续保留在 TODO。真实前后端与 API 代理健康检查通过。没有后端代码变化，未重跑后端测试。
