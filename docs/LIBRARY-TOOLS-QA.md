# 资料与处方入口合并验收

日期：2026-11-10。结果：通过。

左侧只保留「中药资料与处方」，点击打开同一弹窗，以「基础资料 / 处方检查」切换。默认显示基础资料，标签切换保留阅读位置、处方输入和报告；关闭整个弹窗清除本次处方并取消浏览器请求。

## 自动检查

- `frontend: pnpm typecheck` 通过。
- `frontend: pnpm test` 31 项通过。
- `frontend: pnpm build` 通过；最终焦点修复后再次构建通过。
- `git diff --check` 通过。

## Chrome 验收

使用本机 Google Chrome 和独立 FastAPI / SQLite 测试账号，浏览器将 API 请求转发到隔离后端；未修改实际账号、资料或处方数据。模型密钥在测试进程中设为空，不调用云端模型或向仿真平台上传。屏幕上的处方及账号仅为界面验收数据。

- 桌面 1440 × 900：侧栏仅一个入口；真实基础资料加载、Word 下载接口与章节阅读正常；手动录入、确认检查返回真实五节报告。
- 标签切换后粘贴文字、年龄、药名和报告仍在，资料阅读滚动位置保留，聊天草稿不变。关闭后再打开默认回到基础资料，处方内容清空。
- 左右方向键、Home / End 切换标签；Tab / Shift+Tab 约束在当前弹窗，Escape 关闭。桌面焦点返回入口，手机返回导航按钮。
- 手机 390 / 320 × 844：资料加载和章节定位正常，上传与手动录入可用；表格仅在自身容器内横向滚动，页面和弹窗没有横向溢出。
- 无未处理的浏览器页面异常。

截图已查看：[桌面入口](../design/library-tools-qa/desktop-entry.png)、[资料阅读](../design/library-tools-qa/desktop-reference.png)、[检查报告](../design/library-tools-qa/desktop-report.png)、[320px 资料](../design/library-tools-qa/mobile-320-reference.png)、[320px 上传](../design/library-tools-qa/mobile-320-prescription.png)、[320px 核对](../design/library-tools-qa/mobile-320-confirm.png)。完整结果见 [result.json](../design/library-tools-qa/result.json)。

本次未重复调用图片 OCR / DeepSeek 识别，也未执行远程部署。
