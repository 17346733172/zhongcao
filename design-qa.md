# 本草知问 · 聊天排版视觉验收

日期：2026-10-28。

## 最新补充：界面字体统一

按用户最后一张[页脚字体参考](design/reference-ui-typography.png)更新账号区、知识库 / 历史对话标签、顶部资料标题、上传按钮、AI 标识与底部说明。工作区采用本地 DM Sans 配合系统中文无衬线回退，主标签桌面 18px、手机 16px，辅助文字 14px，指定界面文字均为 400 常规字重。字体更新以本节为准，下方 Arial 字体记录属于上一版排版验收。

- `pnpm typecheck` 通过，`pnpm test` 17 项通过；独立源码副本执行 `pnpm build --webpack` 通过，包含 public/fonts 本地字体资源。
- Edge 在生产 Next.js 3108 → FastAPI 8108 代理和临时 SQLite 账号下核验，未模拟业务 API，未调用模型。检查 11 处计算样式；平台字形诊断确认英文为本地 DM Sans 9pt（字体内部名称），中文为 Microsoft YaHei UI。400 / 500 / 700 三个字体文件均返回 200，无外部字体请求。
- 1440 × 900 桌面、768 × 1024 平板、390 × 844 和 320 × 844 手机布局无横向溢出；手机导航文字可读，底部说明自然换行，发送按钮完整可见。
- 上传抽屉打开 / Escape 关闭、账号入口往返、原文检索发送与回答通过；无页面异常和业务 API 5xx。
- 已打开并目视检查[桌面](design/ui-typography-qa/desktop.png)、[320px 手机](design/ui-typography-qa/mobile-320.png)和[手机导航](design/ui-typography-qa/mobile-390-navigation.png)。细节见[侧栏](design/ui-typography-qa/desktop-sidebar.png)、[顶部](design/ui-typography-qa/desktop-header.png)、[底部说明](design/ui-typography-qa/desktop-notice.png)，[结构化结果](design/ui-typography-qa/result.json)。

本轮字体修改无剩余待办；其他操作系统中文回退与所有浏览器版本未逐一验证。

final result: passed

## 参考、状态与证据

- Source visual truth：[用户提供的 DeepSeek 排版截图](design/reference-chat-layout.png)，1919 × 908。
- Implementation：[本地项目](http://127.0.0.1:3000/)，截图 [桌面首页](design/chat-layout-qa/desktop-welcome.png)，1919 × 908。
- 对比状态：浅色、已登录、空会话欢迎页；用户要求主要参照格式和字体。参考图已有个人历史，本项目测试初始为空，未伪造历史。
- CSS viewport：1919 × 908，deviceScaleFactor=1，输出同尺寸，无密度换算。完整对照图仅上下拼接，两张图不缩放；局部对照使用同尺寸实际区域。
- 完整对照：[comparison-full.png](design/chat-layout-qa/comparison-full.png)。字体 / 欢迎语 / 输入框细节：[comparison-detail.png](design/chat-layout-qa/comparison-detail.png)。两者均已打开并进行视觉比较。
- 其他状态：[桌面回答](design/chat-layout-qa/desktop-answer.png)、[手机首页](design/chat-layout-qa/mobile-welcome.png)、[手机回答](design/chat-layout-qa/mobile-answer.png)、[平板](design/chat-layout-qa/tablet-welcome.png)、[320px 窄屏](design/chat-layout-qa/small-mobile-welcome.png)。

## Findings

没有剩余可操作的 P0 / P1 / P2 视觉问题。

- 主区和侧栏比例、灰白底色、居中欢迎语、宽圆角输入框及无衬线层级与用户指定方向一致。桌面左栏实测 330px，输入框宽 970px、高 156.375px，左上位置约 (639.5,390.7)；参考框约 (637,380)，高度约 155px。
- 与参考图保持的产品差异：本草知问品牌 / 书本图标、知识库入口、上传入口、真实 AI / 原文模式、账号权限和来源标签。没有复制商标、个人历史、头像或桌面宠物；没有添加尚未实现的深度思考 / 联网搜索按钮。
- 手机没有对应参考源图，按相同字体和组件语言适配，不宣称手机逐像素复刻。320 / 390 / 768px 均没有横向溢出，发送与模式控件可见。

## 比较与修正历史

1. 按用户新参考替换原三栏、宋体标题、浅蓝回答大面板，改为两栏、统一无衬线和白底正文。
2. 实现中发现资料改为 dialog 后，原抽屉焦点逻辑会将自身误判为嵌套弹窗而跳过约束；修正为只在原文弹窗存在时跳过。浏览器复测通过 Tab 循环、Escape 关闭与草稿保留。
3. 首次自动字体断言将 sans-serif 中的 serif 子串误认为衬线字体，已修正验收脚本；没有为绕过断言修改产品字体。最终完整和局部图已复核，并另用浏览器平台字形诊断确认当前中文回退栈使用 Microsoft YaHei。
4. 最终生产构建、9 组浏览器检查及同尺寸视觉比较通过。没有在最终视觉比较后修改页面代码。

## 五项视觉检查

- 字体：工作区采用 Arial / PingFang SC / Microsoft YaHei / Noto Sans SC / 系统 sans-serif；品牌、欢迎语、标题与正文统一无衬线，不加载外部字体。欢迎语 30px / 700，回答主标题 27px / 700，正文桌面 17px、手机 16px，行高 1.9，窄屏换行可读。
- 间距 / 布局：左侧浅灰导航、白色主区、970px 内容列和 28px 圆角输入框。空会话居中，发问后输入框位于主区底部，内容独立滚动；问题靠右、引用与回答正文对齐。
- 颜色：主色 #4D6BFE、正文 #24262B、标题 #17191F、侧栏 #F8F9FB；真实来源与 AI 补充保持不同文字标签。集中令牌位于 chat-layout.css，仅覆盖工作区。
- 资源：沿用 Phosphor 图标，无额外图片依赖、占位图或手工绘制商标。参考中的头像和桌面宠物不属于本项目页面格式范围。
- 文案：保留本草知问、实际知识库与权限、真实回答模式、来源和服务配置状态。未显示虚假的上传成功或未实现的模型能力。

## 验证结果

- `pnpm typecheck` 通过，`pnpm test` 17 项通过。
- 独立源码副本 `next build --webpack` 成功，通过 Next.js 3107 → FastAPI 8107 真实代理验收，临时 SQLite / 随机测试账号，无 API 模拟；真实 DeepSeek 完成一轮陈皮回答。
- 浏览器 9 组检查通过：[结果](design/chat-layout-qa/result.json)。包括欢迎页、侧栏收起 / 展开、文档保留草稿、资料抽屉焦点与上传 / 查看 / 移除、真实回答与引用对齐、手机导航 / 抽屉 / 键盘发送、768px 平板与320px窄屏。
- 无浏览器 pageerror，无业务 API 5xx。上传移除的短暂成功提示出现在部分流程截图中，属于真实操作反馈。
- 本地 3000 页面与后端代理健康检查通过，前后端已保持运行。

## Follow-up Polish

- P3：输入框纵向位置相对参考约低 11px；当前保留稍宽松的欢迎语行高及真实服务说明，不影响主要比例或交互。
- 未逐一验证其他操作系统字体回退、屏幕阅读器和所有浏览器版本。

## Implementation Checklist

- [x] 更新 DESIGN 并保存新参考。
- [x] 保留实际业务入口、来源标识和手机核心操作。
- [x] 打开完整 / 局部对照及桌面、手机、平板截图。
- [x] 生产构建、回归及浏览器验收通过。

final result: passed
