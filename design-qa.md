# 本草知问 · 聊天排版视觉验收

## 最新验收：DeepSeek 回答排版（2026-10-31）

范围：按用户第一张 DeepSeek 图调整现有回答的字体与排版，保留本草知问的真实业务、回答组织、复制、引用和来源类别。没有复制 DeepSeek 的深度思考、联网搜索或编辑问题功能。

- Source visual truth：[用户 DeepSeek 截图](design/answer-typography-qa/reference-deepseek.png)，1144 × 802；[用户当前页面截图](design/answer-typography-qa/reference-before.png)，1445 × 720。
- Implementation：[本机页面](http://127.0.0.1:3000/)，[回答区截图](design/answer-typography-qa/answer-comparison.png)，1144 × 804；对照捕获 CSS viewport 为 915 × 718，deviceScaleFactor=1.25，截取实际 .chat-body，不缩放字形。参考图未提供原始 CSS viewport / DPR，依据可见字形尺寸选择 1.25 密度；不宣称整页逐像素等同。
- State：浅色、已登录、侧栏收起、用户问题「陈皮」、知识库回答。浏览器受控 API 模拟数据使用参考图中的两个分节文本；模拟数据未写入真实知识库。模型回答采用现有 title / sections，不人为重建参考图的开场概述；全图仅比较本次涉及的回答字体与排版，问题编辑区、输入工具和来源标识属于现有产品差异。
- Full-view comparison：[完整同图对照](design/answer-typography-qa/comparison-full.png)。Focused comparison：[分节局部同图对照](design/answer-typography-qa/comparison-detail.png)，参考截取 948 × 166，实现截取 1001 × 165，均保留原像素密度；局部用于检查标题、正文、加粗和行距，未拉伸到相同宽度。两张对照均已打开复核。

### Findings 与修正历史

1. 首轮 [P2]：24px 分节标题略大。调整为桌面 22px / 700、手机 20px / 700，重新生产构建及浏览器捕获后，标题视觉尺度与参考接近；局部对照高度 165px 对参考 166px，剩余宽度差异见 P3。
2. 字体确认：对相同中文生成 Arial + Microsoft YaHei、Microsoft YaHei UI、SimSun 和 SimHei 样张，与参考对照后采用 Arial / Microsoft YaHei。CDP 平台字形确认中文实际为 Microsoft YaHei、英文为 Arial。前一次对照使用缩放截图，最终已替换为浏览器原生 1.25 密度捕获，未使用插值放大字形。
3. 最终没有剩余可操作的 P0 / P1 / P2 问题。来源小标签保留于标题旁，AI 补充继续单独标识；这属于资料真实性要求，不按 DeepSeek 图移除。

### 五项视觉检查

- 字体：正文为 16px / 28px、#0F1115，桌面分节标题 22px / 700、手机 20px / 700，加粗使用真实 strong，列表使用 ul / ol / li。普通与知识库模式使用同一回答正文样式；状态提示与原文说明保留辅助字号。
- 间距 / 布局：阅读列与输入框最大宽度 800px，分节间距 32px、段落间距 16px；段落、列表和多行内容自然换行。320 / 390px 无页面横向溢出，长表格在可聚焦的自身区域滚动。
- 颜色：黑色正文、白底、灰色列表标记和辅助来源标签；引用沿用既有蓝色，AI 补充沿用已有浅米色标签，语义保持明确。
- 图片 / 资源：此次参考区没有需新建的位图资产；保留现有 Phosphor 图标、系统字体与本地界面字体，无新外部字体加载或手绘替代素材。
- 文案 / 内容：排版不改变资料含义。模型提示允许按需加粗、列表和空行；原文仍显示原字面文本。复制保留 Markdown 与来源类别，引用只使用后端关联的 sources。模拟截图用于排版核验，不当作真实医学回答或来源证据。

### 验证

- `pnpm typecheck`、29 项前端回归、98 项后端回归通过；最终源码副本 `pnpm build --webpack` 通过。
- Edge + 独立生产 Next.js 3121，1440 / 390 / 320 CSS px、deviceScaleFactor=1.25，共 6 组浏览器检查通过，见[结果与实际字体](design/answer-typography-qa/result.json)。包含加粗、列表、分段、编号、引用块、表格、复制、键盘引用与焦点返回、资料卡片去重、HTML 不执行，无 pageerror。
- [桌面](design/answer-typography-qa/answer-1440.png)、[390px](design/answer-typography-qa/answer-390.png)、[320px](design/answer-typography-qa/answer-320.png)、[窄屏表格](design/answer-typography-qa/rich-320.png)已捕获；已目视复核最终完整 / 局部对照及窄屏正文 / 表格。
- 当前 3000 页面另做一次模拟 API 冒烟，确认正文 16px / 28px、标题 22px、加粗与列表已实际加载，[截图](design/answer-typography-qa/active-1440.png)；前后端代理健康。后端已重启加载最新提示。没有额外调用真实模型；样式不会将旧纯文本答案自动改写为列表。

### Follow-up Polish

- P3：参考截图的实际内容列与裁剪范围无法精确还原，现有 800px 阅读列的部分换行与截图略有差别，段落仍为同样三行；保留本项目统一输入 / 回答列。
- 未验证其他操作系统的字体回退和真实模型每次选择的排版结构；不宣称拿到了 DeepSeek 的专有字体配置。

### Implementation Checklist

- [x] 保存用户参考，更新 DESIGN 和集中样式变量。
- [x] 保留复制、真实引用、来源类别与原文展示，新增安全 Markdown 渲染。
- [x] 修正标题偏大后重新构建、捕获，并在同图中比较完整和局部证据。
- [x] 桌面 / 手机、当前本机页面与前后端检查通过。

final result: passed

---

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
