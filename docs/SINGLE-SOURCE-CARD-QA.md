# 引用资料卡片去重验收

日期：2026-10-30。结果：通过。

勾选「原文检索」后，AI 回答下方不再展示重复的「引用资料」卡片，下方独立原文结果继续保留资料卡片。AI 正文编号直接打开该编号对应的原文弹窗；原文结果编号仍切换自身卡片。两个结果的来源索引不混用；即使附加原文未命中，AI 编号仍能打开自身来源。普通 AI 不显示任何文档引用。

- `pnpm typecheck`、`pnpm test`（27 项）、`pnpm build --webpack` 通过。
- Edge + 生产 Next.js 3117，受控 API 模拟数据，不调用外部模型、不修改实际数据。
- 1440 × 900、390 × 844、320 × 844：同轮仅原文结果保留一处资料卡片；AI 两个编号分别打开不同的正确原文，支持 Enter / Escape 并恢复焦点；原文编号、资料查看、折叠与两个结果的复制均可用，无横向溢出。
- 桌面额外验证附加原文未命中时，AI 来源仍能直接打开，不产生空卡片；切换模式不改变旧结果，普通模式仍无引用。

共 4 项浏览器场景通过，无页面异常；已目视检查桌面及 320px 截图。本次请求无剩余待办。

证据：[结果记录](../design/single-source-card-qa/result.json)、[桌面](../design/single-source-card-qa/checked-1440.png)、[390px](../design/single-source-card-qa/checked-390.png)、[320px](../design/single-source-card-qa/checked-320.png)。
