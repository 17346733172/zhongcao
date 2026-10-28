# 多轮与口语追问验收

日期：2026-10-27。

## 当前行为

AI 请求只发送当前会话最近 5 轮，单轮问题最多 500 字符、回答摘要最多 1000 字符；新建会话不带旧上下文，连续追问通过 resolvedQuestion 保留主题。常见短追问先在本地规则中承接；关键词没有命中的自然语言由配置的 DeepSeek 做一次意图理解，整理口语和有语境支持的轻微错字，再重新检索。简介显示理解后的完整问题，原始气泡保持原样。

语义理解输出只包含动作、完整问题和澄清文字（follow_up / standalone / clarify / unrelated），最多 512 tokens、10 秒网络阶段超时，不发送文档正文。新药材优先，追问不能无声替换成其他药材；多解 / 缺主题先澄清，纯数字与代码式无意义输入不调用模型。重检没有相关原文时不生成。语义阶段和生成阶段共享 4 个并发名额；前端总等待上限仍为 45 秒。

历史回答、语义理解结果都不是文档证据，每轮重新读取授权原文。文档段引用当前检索结果；AI 补充段单独标为非文档原文且无引用。模型知识未联网核实，编号校验不验证医学事实。实现不保证每个错字都能纠正；不确定时澄清。

原文检索模式仍按当前输入独立检索。会话仅存当前页面，未实现刷新后的持久化；已暂停的历史列表交互问题未在本轮处理。

## 自动检查

- 后端：`.venv/Scripts/python.exe -m unittest discover -s tests -v`，53 项通过。覆盖权限、受限历史、连续主题、明确换药材、错字口语语义重检、歧义、未知 / 无关主题、伪造角色、错误 JSON、上游超时、并发释放和来源隔离。
- 前端：`pnpm typecheck` 通过；`pnpm test` 17 项通过，覆盖最近 5 轮、空会话、长度上限、原文对象不进入历史、AI 补充标识及检索来源。
- 真实 DeepSeek 接口三项冒烟通过：党参后问「有什么不要的药效吗?」理解为党参不良反应 / 用药禁忌并生成；「那吃了会不会不舒服」承接党参；无上文时同一句错字问题先澄清。

## 已完成的基础多轮浏览器检查

在独立源码副本运行 `next build --webpack`，通过 Next.js 3107 → FastAPI 8107 真实代理，使用临时 SQLite / 随机验收账号及实际 DeepSeek，无 API 模拟。13 项检查通过：陈皮 → 作用 → 手机用量连续承接，换为黄芪后作用承接黄芪，111 无内容 / 引用，新建会话缺主题澄清。桌面 1487px、手机 390px 无横向溢出、无页面异常或 5xx。

证据：[基础多轮结果](../design/follow-up-qa/result.json)、[桌面追问](../design/follow-up-qa/desktop-chenpi-follow-up.png)、[手机追问](../design/follow-up-qa/mobile-follow-up.png)、[主题切换](../design/follow-up-qa/desktop-topic-change.png)。

## 口语语义浏览器检查

采用同样的独立生产构建、临时 SQLite / 随机账号、真实 DeepSeek 和 Next.js 代理，无 API 模拟。15 项检查通过，浏览器无页面异常或 API 5xx：

- 党参 →「有什么不要的药效吗?」理解为党参的不良反应 / 用药风险，简介说明理解结果，正文保留文档依据和 AI 补充标签。
- 手机 390px 输入「那吃了会不会不舒服」连续承接党参；无横向溢出。
- 桌面 1487px 明确切到陈皮，再输入相同错字问题，回答和引用切到陈皮。
- 111 无内容与来源；「今天天气怎么样」不借用旧药材。
- 新建会话后直接输入同一句口语错字问题，先询问药材，不凭空作答。

证据：[语义追问结果](../design/semantic-follow-up-qa/result.json)、[桌面错字追问](../design/semantic-follow-up-qa/desktop-typo-follow-up.png)、[手机口语追问](../design/semantic-follow-up-qa/mobile-colloquial-follow-up.png)、[主题切换](../design/semantic-follow-up-qa/desktop-topic-switch.png)、[新会话澄清](../design/semantic-follow-up-qa/new-conversation-clarification.png)。这些验证检查流程和来源标识，不视为对模型医学知识的事实审查。

接口使用官方 [JSON 输出](https://api-docs.deepseek.com/guides/json_mode/) 和 [Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)；没有增加依赖或新增环境变量。
