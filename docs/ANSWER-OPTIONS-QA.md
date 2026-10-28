# 回答方式独立选择验收

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
