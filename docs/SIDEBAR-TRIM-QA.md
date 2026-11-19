# 侧栏精简验收

日期：2026-11-18。

按用户截图移除整个「设备与系统」分组，以及「设备配置」「系统设置」两个入口；删除两项图标导入。仅修改 `Sidebar` 的导航配置，桌面与手机共用此变更。

验证结果：

- `pnpm typecheck` 通过，现有 `pnpm test` 33项通过。
- 浏览器1440、390、320px共3项通过：功能导航严格为7个入口，分组只有测试和智能；移除的标题和按钮未进入页面DOM，不占位或参与键盘焦点。
- 运行总览、AI Agent、测试执行、测试方案切换及弹窗关闭正常；聊天草稿保留，无页面横向溢出，无pageerror。使用标明模拟账号的隔离API响应，不操作仿真平台。
- 已查看桌面和320px手机截图，移除后的导航布局与用户要求一致。

证据：[结果](../design/sidebar-trim-qa/results.json)、[桌面](../design/sidebar-trim-qa/navigation-1440.png)、[390px](../design/sidebar-trim-qa/navigation-390.png)、[320px](../design/sidebar-trim-qa/navigation-320.png)。

生产构建使用 `tmp/sidebar-trim-build-20261118` 隔离目录，复用现有依赖。首次默认Turbopack受目录外node_modules链接解析限制未完成；改用当前Next.js支持的 `pnpm build --webpack` 后构建通过，未修改产品构建配置。

本次没有后端业务变更，未重跑后端测试。
