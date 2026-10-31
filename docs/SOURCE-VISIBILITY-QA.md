# 原文开关与引用展示验收

日期：2026-10-30。结果：通过。

后续已将开关扩展为后端是否使用知识库；最新行为与验证见[普通 AI 与知识库隔离验收](NO-KNOWLEDGE-QA.md)。以下保留为引用显示调整时的记录。

引用展示按该轮发送时「原文检索」的选择保存到 `Message.showSources`。未开启时，AI 回答不显示正文引用编号及「引用资料」区域；开启后才显示 AI 回答与附加原文结果各自的引用。以后切换开关或历史会话，不改变已有回答的选择。后台仍根据知识库检索并校验来源，保留资料依据与 AI 补充标签；默认页脚不再提示核对未显示的引用。

- `pnpm typecheck`、`pnpm test`（25 项）与 `pnpm build --webpack` 通过。
- 现有 Edge / Playwright + 生产 Next.js 3114，使用受控 API 模拟数据，原文结果由现有客户端检索实际生成。不调用外部模型，不修改实际账号或资料。
- 1440 × 900、390 × 844、320 × 844：默认发送无引用区域、无编号；勾选后同一轮显示两个结果及各自引用，AI 第二个引用和原文引用均可打开对应资料，复制可用；取消后的下一轮不显示引用，无横向溢出。
- 反复切换不改变旧回答；桌面切换两个历史会话，各轮仍保持发送时的选择。勾选但未命中时不显示空引用区域或无效编号。

共 5 项浏览器核验通过，无页面异常；已目视检查桌面未选 / 已选和 320px 未选截图。本次请求无剩余待办。

证据：[结果记录](../design/source-visibility-qa/result.json)、[桌面未选](../design/source-visibility-qa/unchecked-1440.png)、[桌面已选](../design/source-visibility-qa/checked-1440.png)、[390px 未选](../design/source-visibility-qa/unchecked-390.png)、[320px 未选](../design/source-visibility-qa/unchecked-320.png)、[320px 已选](../design/source-visibility-qa/checked-320.png)。
