# 回答头部精简验收

日期：2026-10-30。结果：通过。

本文记录头部精简时的验收；后续引用显示规则以[原文开关验收](SOURCE-VISIBILITY-QA.md)为准。

按用户截图移除生成回答上方的「DeepSeek 生成回答 · deepseek-flash」和标题下方「以下回答由 DeepSeek 生成…」的重复说明，直接展示标题和正文。复制回答同步精简。追问的「我理解你是在问：…」、澄清、未命中、问候、原文摘录以及各段来源与引用保留；没有简介时不渲染空段落。

- `pnpm typecheck`、`pnpm test`（25 项）、`pnpm build --webpack` 通过。
- 使用现有 Edge / Playwright 和生产 Next.js 3113，受控 API 演示数据仅用于核验显示、引用和复制，不调用外部模型、不改实际账号或资料。
- 1440 × 900、390 × 844、320 × 844：不显示模型 / 重复说明、不留下空简介；标题、正文、资料依据与 AI 补充标签、原文查看和复制保留，无横向溢出。
- 桌面追加核验追问理解提示的显示与复制，以及澄清、未命中、原文摘录和问候提示。

共 5 项浏览器核验通过，无页面异常；已目视检查桌面与 320px 截图。本次改动无剩余待办。

证据：[结构化结果](../design/answer-header-qa/result.json)、[桌面回答](../design/answer-header-qa/generated-1440.png)、[390px 回答](../design/answer-header-qa/generated-390.png)、[320px 回答](../design/answer-header-qa/generated-320.png)、[追问理解](../design/answer-header-qa/follow-up.png)。

## 知识库回答隐藏总标题（2026-10-30）

按用户最新截图，勾选「原文检索」发送的 AI 生成回答隐藏顶部总标题，复制同步省略。正文分节、来源标签和引用、独立原文结果标题继续显示；普通 AI 回答和澄清 / 未命中 / 问候标题保留。没有总标题和简介时，首段无额外顶端间距；后续切换开关不改变旧回答。

- `pnpm typecheck`、`pnpm test`（27 项）和 `pnpm build --webpack` 通过。
- Edge + 生产 Next.js 3116，1440 × 900、390 × 844、320 × 844 下核验总标题、正文、复制、引用查看、原文结果标题以及切换后旧回答的状态，无横向溢出；桌面补验澄清、未命中和问候标题。
- 共 4 项浏览器场景通过，无页面异常。使用受控 API 模拟数据，不调用外部模型、不修改实际账号或资料；已目视检查桌面与 320px 截图。

证据：[结果记录](../design/knowledge-title-qa/result.json)、[桌面勾选](../design/knowledge-title-qa/checked-1440.png)、[390px 勾选](../design/knowledge-title-qa/checked-390.png)、[320px 勾选](../design/knowledge-title-qa/checked-320.png)。本次请求无剩余待办。
