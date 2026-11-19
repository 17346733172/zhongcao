# 数据中心移除重复运行总览验收

日期：2026-11-17。

移除数据中心第四个「运行总览」标签、重复内容和专用样式，恢复「概览 / 设备与异常 / 全部处方」三个标签。独立运行总览主页面、侧栏入口及共享快照继续使用，原三个标签的索引和聊天定位保持原样。

- `frontend` 的 `pnpm typecheck`、`pnpm test` 通过，33项前端回归全部通过；`tmp/data-center-three-tabs-build-*` 隔离副本的 `pnpm build` 通过。
- 开发服务和隔离生产构建均通过1440 / 390 / 320px浏览器核验：数据中心恰有三个标签且没有运行总览内容；原设备列表和处方空状态可用，左右键三项循环、Home / End首尾定位正常。
- 数据中心默认概览，共用已有快照读取；刷新同步更新数据中心和独立主页面。Escape关闭回到运行总览主页面，14类设备及AI Agent草稿保留，手机导航和布局正常，无整体横向溢出或页面脚本错误。
- 桌面及320px截图已查看，临时生产预览已关闭。

[桌面三标签](../design/data-center-three-tabs-qa/center-1440.png)、[390px三标签](../design/data-center-three-tabs-qa/center-390.png)、[320px三标签](../design/data-center-three-tabs-qa/center-320.png)、[生产浏览器结果](../design/data-center-three-tabs-qa/result.json)。

浏览器使用模拟账号和隔离接口，布局样本取自此前仿真快照；历史统计在测试中明确返回未接入提示，未访问真实平台、云端模型或写入业务数据。本轮未修改后端，未重跑后端测试和真实平台联调，无新增依赖或环境变量。
