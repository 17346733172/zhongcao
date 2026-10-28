# 知识库资料入口验收

日期：2026-10-28。

右上角按钮与右侧抽屉统一为「知识库资料」，书籍图标沿用已有图标体系；移除抽屉内重复的处方入口及回调 / 样式。左侧「处方检查」保留，用户通过它进入独立上传和审核流程。普通用户仍可查看共享资料，编辑员与管理员仍可上传和移除。

验证结果：`pnpm typecheck`、前端 22 项回归与独立源码副本 `next build --webpack` 成功。Edge 使用真实 Next.js 3115 → FastAPI 8115 代理、临时 SQLite 和随机测试密码，未模拟 API 响应或调用模型：

- 管理员键盘打开资料抽屉，上传虚构 UTF-8 文本，查看原文，刷新后资料仍在，原文检索可引用该文本；抽屉不再存在处方入口。
- 普通用户通过同名入口查看共享资料和原文，没有上传 / 移除控件，仍能从左侧打开处方检查。
- 编辑员可移除临时测试资料，管理员刷新后可见对应变化。
- 左侧处方检查保留文件 / 图片选择、手动录入、实际后端审核结论；关闭后问答草稿保留。
- 390 / 320px：资料图标的可访问名称正确，资料抽屉仅包含共享资料功能，移动导航能打开处方上传，页面无横向溢出。
- 无页面异常或业务 API 5xx。本轮未修改后端业务逻辑，未重复运行完整后端单元测试。日常前端 3000 服务返回 200。

证据：[结构化结果](../design/knowledge-entry-qa/result.json)、[桌面入口](../design/knowledge-entry-qa/desktop-main.png)、[共享资料抽屉](../design/knowledge-entry-qa/desktop-knowledge-drawer.png)、[普通用户抽屉](../design/knowledge-entry-qa/viewer-knowledge-drawer.png)、[320px 资料抽屉](../design/knowledge-entry-qa/mobile-320-drawer.png)、[320px 处方入口](../design/knowledge-entry-qa/mobile-320-prescription.png)。
