# 数据中心入口验收

日期：2026-11-10。结果：通过。

左侧知识库分组在「中药资料与处方」下方新增同级「数据中心」入口，沿用现有侧栏样式。点击打开「内容待配置」弹窗，具体内容和业务接口等待用户提供。

## 自动检查

- `frontend: pnpm typecheck` 通过。
- `frontend: pnpm test` 31 项通过。
- `frontend: pnpm build` 通过；焦点约束调整后的最终构建通过。
- `git diff --check` 通过。

## 浏览器核验

使用本机 Microsoft Edge，在当前本地前端服务上核验。账号、资料和 AI 状态由浏览器级 API 替身提供，界面明确显示「界面验收账号」；没有读写实际账号、资料或处方，也未调用模型与仿真平台。

- 1440 × 900、390 × 900、320 × 900：入口顺序正确，弹窗处于视口内，页面无横向溢出。
- 打开后聚焦关闭按钮，Tab / Shift+Tab 保持在弹窗内，背景不能获得焦点。
- Escape、关闭按钮和点击遮罩均可关闭；桌面焦点返回数据中心入口，手机返回导航按钮。
- 手机打开弹窗时收起导航；聊天草稿完整保留，原「中药资料与处方」入口仍可正常打开和关闭。
- 无未处理的浏览器页面异常。截图已检查；未执行远程部署。

截图：[桌面入口](../design/data-center-qa/desktop-entry.png)、[桌面弹窗](../design/data-center-qa/1440-dialog.png)、[390px 弹窗](../design/data-center-qa/390-dialog.png)、[320px 弹窗](../design/data-center-qa/320-dialog.png)。完整检查结果见 [result.json](../design/data-center-qa/result.json)。
