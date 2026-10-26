# 项目架构与目录

## 技术栈

Next.js 16 App Router、React 19、TypeScript，使用普通 CSS 和 Phosphor 图标。应用位于 frontend，根目录文档继续保留。

## 模块

| 位置 | 职责 |
| --- | --- |
| src/app/layout.tsx | HTML 语言、页面元信息与样式入口 |
| src/app/page.tsx | 主页面入口 |
| src/app/globals.css | 全局规范、字体和设计变量 |
| src/app/workspace.css | 桌面与手机布局、组件样式 |
| src/components/knowledge-workspace.tsx | 状态编排、队列与提问 |
| src/components/sidebar.tsx | 知识库和历史对话 |
| src/components/conversation-view.tsx | 问答、引用和复制 |
| src/components/upload-panel.tsx | 文件选择、拖拽和状态 |
| src/components/source-dialog.tsx | 完整原文与焦点管理 |
| src/lib/types.ts | 文档、会话、回答和来源类型 |
| src/lib/demo-data.ts | 预置资料与本地摘录适配 |
| scripts/check-demo.mjs | 检查原文与来源边界 |

## 数据流

用户选择知识库 → 读取该库会话与资料 → 提问 → 演示适配生成回答或本地摘录 → 点击引用核对原文。

文件通过浏览器 File.text() 读取，不上传服务器。处理队列只更新本页状态；所有会话、资料和摘录在刷新后清除。

## 后端边界

当前没有业务 API、数据库或模型密钥。后续应增加服务端文件管理、解析、检索和生成能力，保持 Source 类型中的文件名、原文及位置来自真实服务结果。

浏览器不应持有模型密钥。前端显示的 PDF 页码只属于明确标记的预设示例，不代表真实解析结果。
