# 新建弹窗排版与实时钟验收

日期：2026-11-14。

## 最新调整：移除整块时间区域

按用户最新反馈删除操作栏内的完整实时时钟区域，保留底部「数据读取时间」。同时清理时钟状态、定时器、监听及样式。

`pnpm typecheck`通过；本地开发页面以只读模拟接口在1440 / 836 / 320px核验通过，控件保持40px、无横向溢出、无浏览器运行错误，关闭后原标签及草稿保留。已查看桌面与手机截图：[桌面](../design/new-test-task-remove-clock-qa/popup-1440.png)、[手机](../design/new-test-task-remove-clock-qa/popup-320.png)、[核验结果](../design/new-test-task-remove-clock-qa/results.json)。本次小范围删除未重跑完整生产构建及无关业务测试；下方为此前排版与实时钟的历史验收。

按用户反馈修正新建测试任务弹窗的拥挤排布，并移除其中的累计运行时长，替换为带日期、每秒更新的当前北京时间。

## 修改与验证

- 标题和关闭独立一行；浅灰操作栏将数量 / 生成与启停分组，时间单独分区。数量输入和三个按钮均为40px，统一圆角、边框与间距；中等宽度时间换至下方，手机以网格排列。
- 时钟由浏览器当前时刻按Asia/Shanghai格式化，每秒更新，重新可见时校正。与仿真累计时钟、暂停状态和快照获取解耦；关闭后清理定时器，不每秒请求平台。保留原生time及dateTime，关闭每秒屏幕阅读器播报。
- `frontend` 中 `pnpm typecheck` 通过；最终源码在既有隔离副本以单线程 / 单工作进程执行`pnpm build`通过，包含TypeScript和六个静态页面生成。正式Next配置未改。
- 最终生产版3219端口，1591 / 1024 / 836 / 390 / 320px五种宽度均通过。浏览器时区设置为America/New_York，实际界面仍显示完整北京时间且正常跳秒。
- 仿真运行、暂停以及快照读取失败时均验证时间继续变化；界面不再出现「累计运行」字段。运行状态仍读取只读快照，不受时间显示更改影响。
- 自动检查四个控件高度均为40px，桌面顶边一致；手机开始 / 暂停等高等宽。页面、弹窗和操作栏均无整体横向溢出。
- 原有默认5、1–50整数校验、失败重试、Escape、Tab / Shift+Tab、返回新建按钮、父页标签和聊天草稿均通过；无浏览器运行错误。接口方法只有GET。

## 证据与范围

- [用户报告的问题局部](../design/new-test-task-layout-qa/reported-layout.png)
- [完整同图对照](../design/new-test-task-layout-qa/comparison-full.png)
- [操作栏同图对照](../design/new-test-task-layout-qa/comparison-toolbar.png)
- [桌面弹窗](../design/new-test-task-layout-qa/popup-1591.png)
- [手机弹窗](../design/new-test-task-layout-qa/popup-320.png)
- [五种宽度结果](../design/new-test-task-layout-qa/result.json)

同图对照及窄屏截图已查看，最新视觉检查见[design-qa.md](../design-qa.md)。用户图为问题局部，本次按新要求修正分区与时间语义，不将其作为需要逐像素复制的目标。

浏览器使用隔离账号与快照响应，未联系仿真平台、调用模型或执行写操作。临时生产服务已关闭；未更改后端、依赖或环境变量配置。本轮未重复执行与此次局部界面无关的聊天单元回归和后端测试。
