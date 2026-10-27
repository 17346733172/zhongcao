# DeepSeek 资料问答接入验收

日期：2026-10-27。已接入后端关键词检索 + DeepSeek 生成回答，并使用用户在本机填写的配置完成真实云端请求。密钥未写入本记录、前端、测试产物或 Git；实际 .env 在忽略列表中。

本记录为最初接入时的验收。此后用户已选择允许 AI 一般知识补充，当前按段区分文档依据与补充，后端共 35 项测试；最新真实联调见 [混合回答验收](HYBRID-ANSWER-QA.md)。

## 已验证

- 后端 29 / 29 项测试通过（原 16 项 + 新增 13 项），包括三角色权限、CSRF、只接受问题、未命中不调用模型、多来源编号映射、无效引用、截断 / 异常 JSON、配置缺失、上游鉴权 / 额度 / 限流 / 超时及错误脱敏。
- 前端 pnpm typecheck 和 pnpm test（12 / 12）通过。
- 隔离源码副本使用 next build --webpack 生产构建通过；随后从 3107 端口经真实 Next.js 同源代理请求 8107 端口 FastAPI，使用临时 SQLite 与随机密码。现有 3000 / 8000 用户服务和实际业务数据不用于创建测试账号。
- 9 组检查通过（包含生产构建）：真实登录及默认 AI 模式、真实生成与多来源阅读、111 无结果、原文模式、失败保留草稿、请求取消、手机流程和未配置降级。未处理页面异常为 0。
- 主流程使用真实 DeepSeek API；仅服务失败、请求等待 / 取消、未配置三个界面状态使用浏览器响应夹具，其余请求不模拟。

## 真实模型请求

| 问题 | 结果 |
| --- | --- |
| 陈皮有什么功效 | HTTP 200，deepseek-flash 生成 5 段回答，引用实际陈皮条目；单次测试约 2.52 秒 |
| 111 | HTTP 200，mode=no_match，正文和引用均为空；未命中不调用模型 |
| 陈皮和青皮有什么区别 | 浏览器经生产代理真实生成，引用陈皮 / 青皮两条原文；可切换段落引用并阅读完整 Word 正文 |

人工核对生成的陈皮功效与引用的正式条目一致；比较回答分别引用两味药的原文。上述样例通过不等于完成全量检索或医学事实评测。

## 桌面与手机

Edge 无界面浏览器，桌面 1487 × 1058、手机 390 × 844。已查看截图并检查无横向溢出；切换回答模式后旧回答仍标明各自生成方式，出错不会写入假回答，新建对话不会混入旧请求结果。

- [桌面真实生成回答](../design/deepseek-qa/desktop-generated.png)
- [服务失败保留问题](../design/deepseek-qa/desktop-error.png)
- [手机 AI 模式](../design/deepseek-qa/mobile-ready.png)
- [手机未命中](../design/deepseek-qa/mobile-no-match.png)
- [手机原文摘录](../design/deepseek-qa/mobile-extract.png)
- [结构化结果与脱敏接口状态](../design/deepseek-qa/result.json)

## 配置与边界

配置方法和接口见 [开发说明](DEVELOPMENT.md#deepseek-配置与问答接口)。backend/.env.example 只提供空密钥及公开的默认地址 / 模型；真实 .env 不进入版本库。后端已重启加载本机配置，页面刷新后可选择 AI 回答。

当前检索按关键词与药材章节选择最多 3 个片段，每段最多向模型发送 3000 字符。只接受当前问题，不传历史聊天；生成非流式。共享文本与正式基础文档均可作为来源，示例条目和无命中片段被排除。资料内容不是操作指令；JSON 与引用编号校验只能保证展示关联有效，不能证明每句回答的事实正确性。

向量语义检索、完整检索效果评测、流式回答、通用 PDF / Word 上传解析和会话持久化仍待后续实现。本轮没有执行线上部署或并发负载评测。

## 官方接口参考

[DeepSeek 接入说明](https://api-docs.deepseek.com/quick_start/agent_integrations/)、[Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion/)、[JSON 输出](https://api-docs.deepseek.com/guides/json_mode/)。按当前接口使用 deepseek-flash、关闭 thinking 及 JSON 输出；模型名可通过后端环境配置调整。
