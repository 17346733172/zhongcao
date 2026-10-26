# 本草知问 · 中药知识库问答

面向上传中药资料并据此提问的客户。界面采用已选定的第 3 张 Product Design 方案：左侧知识库与历史对话，中间问答与引用，右侧资料上传。

## 当前功能

- 使用“中药基础资料”知识库，创建、切换本次页面内的历史会话。
- 输入问题，查看演示回答或本地文本原文摘录。
- 点击引用切换片段，展开或折叠引用，打开完整原文。
- 复制回答、拖拽或选择多个文件、查看处理队列、移除文件。
- Markdown / TXT 使用浏览器读取；PDF / Word 显示待接入解析服务。
- 适配电脑与手机；小屏使用导航和上传抽屉。

当前为前端原型，没有真实 AI、服务器上传、PDF / Word 正文解析、账号或持久化存储。示例回答和演示资料有标识；本地文件只在当前页面中保留，刷新后清除。

## 技术栈

- Next.js 16（App Router）
- React 19
- TypeScript 5.9
- 普通 CSS 与集中设计变量
- Phosphor React 图标
- pnpm 11；运行环境要求 Node.js 20.9 或以上

具体安装版本以 frontend/pnpm-lock.yaml 为准。

## 本地运行

可双击根目录的 **启动前端.cmd**，或在项目根目录终端运行 `./启动前端.cmd`。脚本自动查找本机或 Codex 自带 Node，已有依赖时直接启动 Next.js，无需全局 pnpm；页面已经运行时会显示访问地址。运行 `./启动前端.cmd --check` 可检查启动环境。也可以在终端执行：

```powershell
cd D:\项目\frontend
pnpm install
pnpm dev
```

浏览器打开 http://127.0.0.1:3000 。安装过依赖后，日常只需运行 pnpm dev。

```powershell
pnpm typecheck
pnpm test
pnpm build
pnpm start
```

start 用于运行已完成 build 的生产版本；dev 与 start 使用同一端口，启动其中一个即可。

## 项目目录

```text
项目/
├── AGENTS.md、DESIGN.md、TODO.md、CHANGELOG.md
├── README.md
├── 启动前端.cmd
├── docs/                       # 产品、架构与开发说明
├── design/                     # 已选参考图与验收资料
└── frontend/
    ├── src/app/                # Next.js 页面、布局与样式
    ├── src/components/         # 导航、问答、上传和原文查看
    ├── src/lib/                # 数据类型与演示数据适配
    ├── scripts/                # 原文与来源行为测试
    ├── package.json
    └── pnpm-lock.yaml
```

## 资料使用边界

单个文件限制 10 MB；支持选择 MD、TXT、PDF、DOCX。文本以 UTF-8 读取；空文件、超限与不支持的格式会显示错误。PDF / Word 不产生虚构的解析结果。

本地文本问答只展示原文摘录，不等于语义检索或大模型回答。没有本地文本时，内置资料用于展示预设交互；没有可读取资料时会提示先添加文件。

## 文档

- [协作规范](AGENTS.md)、[设计规范](DESIGN.md)、[开发计划](TODO.md)、[更新记录](CHANGELOG.md)
- [产品范围](docs/PROJECT-SPEC.md)、[架构](docs/ARCHITECTURE.md)、[组件规范](docs/COMPONENT-GUIDELINES.md)
- [页面结构](docs/PAGE-STRUCTURE.md)、[开发流程](docs/DEVELOPMENT.md)、[Registry](docs/REGISTRY.md)、[部署](docs/DEPLOYMENT.md)

后续接入真实服务时，应将文件存储、解析、检索、模型调用和来源元数据放到服务端，再替换 src/lib/demo-data.ts 的演示适配。
