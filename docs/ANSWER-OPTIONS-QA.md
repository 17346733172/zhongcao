# 回答方式独立选择验收

当前交互以文末「默认 AI 回答（2026-10-30）」为准；此前记录保留为历史验收。

日期：2026-10-28。结果：通过。

「AI 回答」「原文检索」改为独立开关，支持都不选、只选 AI、只选原文和同时选择，再次点击已选项可取消。未选择时保留草稿、禁用发送；按 Enter 给出选择提示，不发送请求。双选在同一轮问题下分别展示 AI 回答和原文检索结果，各自保留引用与复制。

## 自动检查

- `pnpm typecheck` 通过。
- `pnpm test` 22 项通过，其中新增 5 项覆盖所有开关转换、未选择不调用服务、单选功能隔离、双选已解析追问与引用独立、澄清和失败边界。
- 独立源码副本执行 `next build --webpack` 通过，未覆盖本机正在运行的开发构建。

## 浏览器检查

Edge，1440 × 900 桌面、390 × 844 和 320 × 844 手机。使用生产 Next.js 3109 → FastAPI 8109 真实代理、临时 SQLite 和随机测试账号，没有修改实际账号数据，没有模拟 API 响应。

1. 初始配置可用时仅选 AI；取消后两项均不选，草稿保留，按钮发送不可用，Enter 不生成问答、不调用模型。
2. 原文按钮支持空格键切换；只选原文查询「陈皮」得到实际原文摘录，没有 `/api/chat` 请求。
3. 双选查询「陈皮的功效」：一次真实 DeepSeek 请求，同一轮保留一个问题、两个结果。生成中两个选项均禁用。
4. 两个结果的引用分别打开对应原文，复制内容分别读取成功，未混用来源编号。
5. 只选 AI 查询「陈皮的禁忌」：第二次真实 DeepSeek 请求，只展示生成结果，不附加独立原文结果。AI 仍采用既有的资料优先回答规则。
6. 390px、320px 各检查四种状态：按钮和发送完整可见，无横向溢出，说明可换行，切换不丢失草稿。
7. 延迟真实 AI 状态请求，加载期间手动取消原文；状态返回后保持两项未选，不自动覆盖用户选择。

无页面异常、无业务 API 5xx。当前任务无剩余待办；其他浏览器版本未逐一验证。

## 证据

- [结构化结果](../design/answer-options-qa/result.json)
- 桌面：[未选](../design/answer-options-qa/desktop-none.png)、[仅 AI](../design/answer-options-qa/desktop-ai.png)、[仅原文](../design/answer-options-qa/desktop-extract.png)、[双选](../design/answer-options-qa/desktop-both.png)
- 双选结果：[AI 回答](../design/answer-options-qa/desktop-both-ai-result.png)、[原文结果](../design/answer-options-qa/desktop-both-original-result.png)
- 手机：[320px 未选](../design/answer-options-qa/mobile-320-none.png)、[320px 双选](../design/answer-options-qa/mobile-320-both.png)、[390px 双选](../design/answer-options-qa/mobile-390-both.png)

已打开并目视检查桌面双选、320px 未选 / 双选和原文结果截图。部分截图显示引用复制流程留下的真实成功提示。

## 问候与重复空结果修复（2026-10-30）

原因：双选时 AI 和原文检索各返回一份未命中结果，前端原样展示为两个「未找到相关内容」；纯问候此前也进入了资料检索。

纯问候现在由页面直接回复欢迎和提问引导，标为「本草知问」，不调用模型或检索，不占用最近五轮追问历史；带实际问题的问候仍正常查询。双选且两边均未命中时只保留一条提示；任一有实际内容时继续展示独立结果。

- `pnpm typecheck`、`pnpm test`（26 项）和隔离源码副本 `pnpm exec next build --webpack` 通过。
- Edge 生产 Next.js 3110 → FastAPI 8110 真实代理，使用临时 SQLite 和随机普通用户账号，不修改实际数据；模型配置使用测试占位，未调用外部模型，未模拟 API 响应。
- 1440 × 900、390 × 844、320 × 844 下，各验证 AI / 原文 / 双选三种模式发送「你好」：只有一条欢迎回复，无 `/api/chat`、无引用、无横向溢出。
- 三种宽度下双选发送「111」：一次真实 `/api/chat`，只有一条未命中提示，无原文引用。
- 桌面仅原文发送「你好，陈皮有什么功效？」：正常返回正式资料和引用，复制内容包含陈皮，无模型请求。

13 项浏览器检查通过，无页面异常。自动回归另覆盖未选模式不执行服务、含问候的实际问题、仅一边有内容时保留结果，以及多次问候不挤掉已有药材主题。此次未验证真实外部模型回答，沿用之前的模型生成与引用流程。

证据：[结果记录](../design/greeting-fix-qa/result.json)、[桌面问候](../design/greeting-fix-qa/greeting-1440.png)、[390px 问候](../design/greeting-fix-qa/greeting-390.png)、[320px 问候](../design/greeting-fix-qa/greeting-320.png)、[桌面未命中](../design/greeting-fix-qa/no-match-1440.png)、[带实际问题的问候](../design/greeting-fix-qa/greeting-with-question.png)。

## 默认 AI 回答（2026-10-30）

按用户最新截图去掉输入框中的「AI 回答」按钮，发送默认 AI 回答。「原文检索」默认关闭，开启后仅附加独立原文结果，再次关闭后仍使用 AI；不再存在未选择或仅原文的发送状态。服务配置状态只用于提示，不覆盖原文开关。未配置和请求失败时保留草稿，不显示成功结果。

- `pnpm typecheck`、`pnpm test`（25 项）通过；隔离源码副本 `next build --webpack` 和本机 `pnpm build --webpack` 均通过。
- Edge 生产 Next.js 3112 → FastAPI 8112，使用隔离 SQLite 与随机管理员账号，不修改实际账号或资料。正常流程走真实接口，完成两次真实 DeepSeek 生成；未配置 / 503 错误反馈单独使用受控 API 响应。
- 桌面取消附加原文后直接发送「陈皮的功效」，只发一次 AI 请求，显示一份真实生成回答，无附加原文；生成中输入和开关禁用。
- 键盘空格开启原文，Enter 发送「陈皮的禁忌」，一次 AI 请求，同一问题下显示两个独立结果，各自的原文查看和复制可用。
- 390px、320px 下无 AI 按钮，原文开关不丢失草稿；取消后直接发送「111」仍调用真实 AI 接口，各显示一条未命中提示，无横向溢出、无按钮裁切。
- 问候保留本地单条欢迎回复；Shift+Enter 换行不发送；延迟的真实状态请求不覆盖原文选择；未配置 / 503 时显示错误并保留输入。

共 8 项浏览器核验通过，无页面异常。已目视检查桌面与 320px 截图，输入区与用户参考一致，仅保留原文按钮及附件 / 发送操作。本次请求无剩余待办；向量检索、流式回答与会话持久化仍属项目后续范围。

证据：[结果记录](../design/default-ai-qa/result.json)、[桌面输入](../design/default-ai-qa/desktop-default.png)、[真实 AI 回答](../design/default-ai-qa/desktop-ai-answer.png)、[附加原文](../design/default-ai-qa/desktop-with-original.png)、[390px 输入](../design/default-ai-qa/mobile-390-default.png)、[320px 输入](../design/default-ai-qa/mobile-320-default.png)、[未配置错误](../design/default-ai-qa/configuration-error.png)。
