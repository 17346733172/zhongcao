# 开发与验证

## 环境

Node.js 20.9+、pnpm 11；依赖版本以 frontend/pnpm-lock.yaml 为准。

在 frontend 目录执行：

```powershell
pnpm install
pnpm dev
pnpm typecheck
pnpm test
pnpm build
```

开发地址为 http://127.0.0.1:3000 。pnpm start 运行已构建版本，使用同一端口。

## 开发约定

页面使用 App Router。需要交互的模块使用 React 客户端组件，类型集中在 src/lib/types.ts。样式变量在 globals.css，组件布局在 workspace.css。

演示内容留在 demo-data.ts；接入后端时替换数据适配，不将密钥放入客户端。已有会话和原文由前端内存管理，不做持久化承诺。

## 验证

- typecheck：检查 TypeScript 类型。
- test：使用 Node 测试运行器验证空库、未解析 PDF、本地原文与示例来源的隔离。
- build：执行 Next.js 生产构建。
- 浏览器：验证知识库、历史会话、提问、引用、复制、上传、错误、移动布局和控制台。

视觉与交互证据记录在根目录 design-qa.md，参考图在 design/reference-selected.png。

组件目前供应用内部使用，没有发布流程。部署见 DEPLOYMENT.md。
