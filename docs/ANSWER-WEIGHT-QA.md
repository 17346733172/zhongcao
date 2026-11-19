# 聊天回答常规字重验收

日期：2026-11-18。

按用户截图取消回答加粗，使用 `chat-layout.css` 的 `--answer-font-weight: 400` 统一维护总标题、分节标题、Markdown小标题、strong/b、表头和引用编号。正文沿用400；保留字号、颜色、间距，以及标题/强调/表格语义和原文引用。

- `pnpm typecheck` 和现有 `pnpm test` 33项通过。
- 浏览器1440、390、320px分别验证MCP测试方案回答及生成Markdown回答，共6项通过。实际计算字重均为400，覆盖截图中的h2/h3，以及Markdown小标题、strong、th、正文和引用按钮。
- Markdown强调元素及表头仍存在；点击引用可打开对应原文，Escape正常关闭。无页面错误和横向溢出。
- 已查看桌面MCP回答与320pxMarkdown截图，视觉为常规字重。

证据：[计算字重结果](../design/answer-weight-qa/results.json)、[桌面回答](../design/answer-weight-qa/mcp-1440.png)、[320px回答](../design/answer-weight-qa/markdown-320.png)。浏览器使用明确标识的模拟排版账号与响应，不修改真实平台数据。

隔离生产构建通过：使用独立目录 `tmp/answer-weight-build-20261118` 和已验证适合依赖链接的 `pnpm build --webpack`。首次编译完成后被框架升级提示中断，重试相同命令完成，未修改依赖。本次没有后端代码变更，未重跑后端测试。
