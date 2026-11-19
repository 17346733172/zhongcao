# 第三套整体前端 · 当前验收状态

日期：2026-11-19。

final result: blocked

代码及静态检查已落实，当前视觉验收未执行。用户明确选择「先完成代码和静态检查，浏览器验收稍后进行」，本轮依此不启动隔离Chrome，不将构建或旧截图作为视觉验收通过。

- Source visual truth: [选定第三张效果图](design/workbench-v3/reference.png)，1487×1058px，已打开检查；可见素材为标准书本 / 机器人 / 导航图标，继续使用Phosphor，无新位图资产需求。
- Implementation: 当前前端代码；无本轮浏览器实现截图。
- Planned comparison viewport: 1440×1024 CSS px，deviceScaleFactor=1，源图后续需等比规范化；本轮未进行密度归一或截图对比。
- Planned state: AI Agent、历史会话和运行查询回答；示例数据须明确标注，正式页面使用原真实接口。
- Full-view comparison evidence: 缺少实现截图，未执行。
- Focused region comparison evidence: 导航 / 会话、工具记录 / 回答表格、底部输入区均待捕获。

**Findings**
- 字体 / 排版：已在代码统一无衬线与400字重回答；实际字体回退、换行及截断未核验。
- 间距 / 布局：已设置224px导航 / 272px会话、紧凑控件、既有响应式规则；实际比例、滚动与手机溢出未核验。
- 颜色 / 令牌：38个主题变量可解析，五组关键文字色对比度均超过4.5:1；实际渲染与所有状态仍待核验。
- 图像 / 资产：标准UI图标使用已有Phosphor；没有替换成自绘图或把效果图当网页背景。实际图标尺寸与位置未对照。
- 文案 / 内容：不注入效果图中的演示历史或运行数字，更新登录 / metadata旧文案；真实状态和长文本需浏览器核验。

**Comparison history**
- 尚无渲染对比轮次，不判定任何像素保真问题已修复或通过。

**Implementation checklist**
- [x] 当前代码、类型检查、40项前端回归、最终隔离生产构建、设计令牌和关键配色静态检查。
- [ ] 桌面 / 手机截图、核心入口 / 焦点 / 滚动交互。
- [ ] 将同状态截图与选定源图放在同一对照图中，复核字体、间距、颜色、资产和文案并修正P0/P1/P2。
- [ ] 对照通过后更新final result为passed。

[详细实现与静态检查记录](docs/WORKBENCH-V3-QA.md)。以下为本轮之前的历史记录，不是第三套主题的验收证据。

---

# 本草知问 · 视觉验收

## 最新验收：AI Agent 初始页（2026-11-19）

- Source visual truth：[用户左侧参考](design/agent-initial-qa/reference.png)，1280×914px；顶部 7px 与底部 Windows 任务栏不属于目标页面，完整对照取原生 1280×858px 内容区。参考处于已回答状态，用户要求把该布局用于初始页，因此只比较网格、底部输入栏与主内容结构，不把缺少示例回答视为问题。
- Implementation：[初始页](design/agent-initial-qa/initial-1280-858.png)，1280×858 CSS px、deviceScaleFactor=1；未拉伸，模拟已登录空会话。保留本草既有导航、页头、处方入口和服务说明，是本次范围内的既定约束。
- Full-view comparison：[完整同图对照](design/agent-initial-qa/comparison-full.png)。Focused comparison：[输入栏局部同图对照](design/agent-initial-qa/comparison-footer.png)。两者均按原始像素拼接，已实际打开检查；另外查看[320px 手机页](design/agent-initial-qa/initial-320-844.png)。

### Findings 与五项检查

- 原初始页[P1]：白色欢迎区及居中大标题 / 输入卡片与参考的网格主区和底部输入栏不同。已取消可见欢迎标题、统一空会话 / 回答布局，内容区铺满网格，输入栏贴底。首次修改后的完整及局部对照没有剩余可操作的 P0 / P1 / P2。
- 字体：复用 DM Sans 与系统中文，输入文字 16px、服务说明 12px，手机说明 11px；保留本草品牌与导航字号，不复制其他产品的文案或制造参数。
- 间距与结构：桌面文本框 74px、输入区左右 24px，细边矩形与方形发送按钮接近参考。因保留处方检查和说明，桌面底栏约 127px（参考约 109px），属于既定功能差异；手机按钮换行，输入区仍贴底，无控件裁切。
- 颜色：继续使用既有浅蓝灰网格、细蓝灰边框、白色底栏与品牌操作色；网格 30px，无新增视觉主题。
- 图像与图标：没有需要生成的图片资产；继续使用已有 Phosphor 图标和已选网格样式，未使用截图代替可操作界面。
- 文案与内容：空会话只为读屏保留操作提示，界面没有伪造问答、方案或设备数据；处方检查、服务状态和既有资料 / 运行查询提示保留。

### 验证与比较历史

原问题证据为[用户原初始页](design/agent-initial-qa/before.png)；本轮首版完成上述调整后，同图比较通过，无后续视觉修复迭代。Chrome 六种窗口验证初始状态、发送 / 换行、处方弹窗草稿、连续长回答、主栏单层滚动、切页位置及原文弹窗通过，无 pageerror；类型检查、36 项前端回归及隔离单 worker 生产构建通过。已有 Next.js 安全升级提示仍待单独处理。[完整记录](docs/AGENT-INITIAL-QA.md)。

没有剩余 P3 调整项。

final result: passed

---

## 最新验收：弹窗排版与实时北京时间（2026-11-14）

- 用户新要求：修正控件排布不协调，并删除累计运行时长，显示当前实时时间。问题来源为[局部截图](design/new-test-task-layout-qa/reported-layout.png)，836×134px；源图密度与完整视口未知，不做伪精确的逐像素匹配。
- 实现：1591×900 CSS px、deviceScaleFactor=1，[弹窗截图](design/new-test-task-layout-qa/popup-dialog-1591.png)1101×352px、操作栏1051×84px。默认5批、上层弹窗打开、隔离平台运行状态；实时钟读取浏览器当前时刻并显式按北京时间显示。
- [完整同图对照](design/new-test-task-layout-qa/comparison-full.png)和[操作栏局部同图对照](design/new-test-task-layout-qa/comparison-toolbar.png)均保持原生像素并拼接留白，已打开复核。比较目标是新分区和时间语义，允许有意调整旧问题图的结构与文案。

### Findings 与检查

- 原问题[P2]：标题、输入、控制、累计时间与关闭在同一行争用空间，连体输入和按钮视觉边界不一致。现分为独立标题 / 关闭、统一操作栏、说明 / 状态三个层次，四个控件统一40px；桌面分组、中屏时间换行和手机网格均通过。
- 原时间字段已删除，改为带日期的当前北京时间，使用等宽数字固定视觉宽度；暂停和断线也继续跳秒。没有剩余可操作的P0 / P1 / P2问题。
- 字体：沿用DM Sans及系统中文，标题20px、桌面输入 / 控制 / 时间16px，辅助标签13px；手机保持可读字号。间距：40px控件、12px操作间隔，标题与控制分离。颜色：沿用白底、浅灰操作区和既有状态色；没有引入图片或手绘图标，信息 / 关闭仍用Phosphor。
- 文案：操作栏明确「批次数量」「实时时间」「北京时间」，不再以仿真累计值充当当前时间；生成 / 启停的接入范围不变。

### 验证与比较历史

本轮首次修正后的完整与局部同图比较通过，没有追加视觉迭代。类型检查和最终低并发生产构建通过；1591 / 1024 / 836 / 390 / 320px控件几何、跨时区北京时间、运行 / 暂停 / 断线跳秒及原有数量、双层焦点和草稿验证通过，无pageerror。快照采用隔离响应，没有平台写请求。详见[验收记录](docs/NEW-TEST-TASK-LAYOUT-QA.md)。

final result: passed

---

## 最新验收：新建测试任务弹窗（2026-11-14）

- Source visual truth：[用户新参考](design/new-test-task-qa/reference.png)，1591×220px，单一全局仿真控制面板。
- Implementation：1591×900 CSS px、deviceScaleFactor=1，[最终弹窗](design/new-test-task-qa/popup-dialog-1591.png)，1551×266px，未拉伸。上下文为已有测试执行页，上层全局仿真控制已打开，默认5批、运行中；用于比较的快照响应为隔离模拟。
- Full-view comparison：[最终同图上下对照](design/new-test-task-qa/comparison-full.png)。参考与实现都按原生像素拼接，源图是1591×220px的内容面板，实现增加现有产品所需的关闭、预览和读取时间信息。该面板紧凑，完整图中标题、控件和提示都可清楚阅读，无需额外局部裁剪。

### Findings 与修正历史

1. [P2，已修正] [首轮对照](design/new-test-task-qa/comparison-full-v1.png)中按钮和状态提示为14px，较参考偏小。桌面统一为16px，并减小状态条上下内距，保持接近原图的条带高度；手机分别保留14 / 13px并自然换行。
2. 字号调整后重新构建、重新完成四种宽度的浏览器流程，并打开最终同图和手机截图核验。最终没有剩余可操作的P0 / P1 / P2问题。
3. 控制按钮仍禁用、初始输入焦点、新增关闭与预览说明，以及累计时间依读取结果变化，是当前界面范围和产品容器带来的预期差异；不把源图数字或按钮可操作状态当作业务已实现。

### 五项视觉检查

- Fonts / typography：标题20px，桌面控制按钮与提示16px，说明13px，累计时长使用等宽数字；沿用DM Sans与系统中文回退。手机字号和换行已查看，控件标签可读。
- Spacing / rhythm：左侧标题 / 说明、右侧数量与控制、下方分隔说明和橙色状态条的排列与源图一致；手机控制区自然换行，弹窗可独立纵向滚动，无整体横向溢出。
- Colors / tokens：白底、灰色细线、蓝色信息图标、橙色状态区集中在`new-test-task.css`；禁用按钮有明确的灰色状态。
- Image / assets：无需要新建的位图资产，信息与关闭图标均来自既有Phosphor库；没有用截图替代页面或制作手绘图标。
- Copy / content：标题、说明、数量范围和运行 / 暂停提示对应用户参考。没有复制截图累计时间；生成和启停标记待接入，不反馈虚假成功。

### 验证与后续

类型检查、33项前端回归、最终低并发隔离生产构建通过；1591 / 1440 / 390 / 320px新建入口、默认数量、非法输入、状态 / 失败重试、双层关闭与焦点、原标签及草稿保留通过，无pageerror。未新增控制接口，后端和仿真平台未修改；后续真实控制仍待接入。详见[新建入口验收](docs/NEW-TEST-TASK-QA.md)。

final result: passed

---

## 最新验收：测试执行布局（2026-11-14）

- Source visual truth：[用户参考图](design/test-execution-qa/reference.png)，1630×869px；应用区域比较排除底部Windows任务栏和与本页无关的桌面浮层。
- Implementation：[最终桌面截图](design/test-execution-qa/execution-1630.png)，1630×869 CSS px、deviceScaleFactor=1；独立生产版3217端口。弹窗原生截图1594×817px，参考应用内容裁剪1590×820px。对照只做等密度裁剪和留白拼接，没有拉伸字形。
- State：执行中标签、布局预览、两处任务区域。按用户「内容我等下加」要求，任务编号、数量、进度、机台与记录使用明确的待补充状态；操作按钮禁用，未复制参考业务数据。框架沿用本草现有模态、字体和图标体系。
- Full-view comparison：[同图上下对照](design/test-execution-qa/comparison-full.png)。Focused comparison：[首个任务卡片同图对照](design/test-execution-qa/comparison-task.png)，参考1586×212px、实现1537×217px，保持原生密度，用于检查字号、顶边、按钮、结果摘要和进度 / 机台区域节奏。两张对照均已打开查看。

### Findings

- 无剩余可操作的P0 / P1 / P2布局问题。区域次序、三标签、两任务卡片及实时记录表结构与参考一致，卡片高度相差5px；手机按钮和标签正常排列，表格只在自身区域滚动。
- 预览提示、空记录和禁用按钮是用户要求后补内容带来的预期状态差异；进度条为空，机台区域不显示假设备编号或运行灯。当前不比较真实运行内容或成功状态。
- 页头包含现有弹窗关闭按钮，背景沿用项目浅灰白色工作区；不复制参考中的操作系统任务栏、桌面浮层或截图背景纹理。这些不属于测试执行业务布局。

### 五项视觉检查

- Fonts / typography：页面沿用本地DM Sans与系统中文无衬线字体，正文14px、辅助12–13px；任务标题为Consolas搭配中文回退17px，指标23px。标题、描述、按钮和表头层级清楚，手机允许自然换行。
- Spacing / rhythm：任务卡片4px蓝色顶边、18px内距、16px间隔，进度位置12px高，机台占位36px高；两处任务区与记录区保持截图的纵向顺序，手机控件换行且无整体横向溢出。
- Colors / tokens：主题集中在`test-execution.css`，采用深蓝、灰白、通过绿、不合格红和中止棕；禁用按钮有一致的弱化状态，空进度为中性灰，不暗示已完成。
- Image / assets：业务区域没有需要新建的位图资产。下载、播放、报告、停止和记录图标均复用Phosphor；没有复制桌面程序图标、用户信息或外部截图作为页面。
- Copy / content：标签与主要操作名称沿用参考；任务与结果均明确待补充，空表为零数据行。历史批次、测试记录和全部记录切换可用，没有虚构操作成功或任务计数。

### Comparison history

最终生产版的第一轮完整 / 卡片同图比较没有发现需要迭代的P0 / P1 / P2问题。浏览器验证前已将空状态移到横向表格之外；最终四种宽度检查确认手机可直接看到待补充说明。

### 验证与后续

类型检查、33项前端回归、最终隔离生产构建，以及1630 / 1440 / 390 / 320px三标签、全部记录、键盘、禁用状态、焦点和草稿测试通过；无pageerror。运行测试使用隔离的模拟登录 / 文档响应，没有测试业务请求。详见[布局验收](docs/TEST-EXECUTION-LAYOUT-QA.md)。

后续只需在用户提供内容后补入任务、记录和业务操作；真实运行、报告和导出尚未接入。本次未做后端测试，因为没有后端修改。

final result: passed

---

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


## 2026-11-19 · AI Agent 会话窗口

按用户右侧参考增加独立会话栏，深蓝新会话按钮、细边框历史条目与选中态；历史来自当前页面真实问答，不复制参考图的设备操作示例。桌面保持功能导航 / 会话 / 聊天三栏，1100px 及以下从页头打开会话窗口。已检查 1440px 空状态与历史、390px 及320px 历史截图，按钮和边线层级与参考一致，无遮挡和整体横向溢出。六种宽度的交互、隔离、取消请求、错误与键盘验收通过，见[验收记录](docs/CONVERSATION-SESSIONS-QA.md)。


## 2026-11-19 · 去除聊天区标题栏

按用户截图去掉整条「中药基础资料 / 原文 + AI」白色标题栏和占位，桌面网格从主区顶端开始。窄屏会话、手机导航及收起侧栏后的展开入口使用网格上的小按钮。类型检查与 Chrome 六种宽度的布局和既有会话流程验证通过，无页面异常；已查看[桌面空状态](design/chat-header-removed-qa/empty-1440.png)及[手机会话窗口](design/chat-header-removed-qa/empty-390.png)，没有白色标题带或顶部空位，参见[完整结果](design/chat-header-removed-qa/results.json)。本次未重复生产构建及前后端单元回归，未操作真实业务数据。
