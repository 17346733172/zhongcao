# Markdown / Qwen / FAISS RAG

更新：2026-11-01。按 `D:\学习项目\code-RAG(1)\code-RAG` 的结构接入当前应用。

## 运行链路

页面默认执行「原文 + AI」，不再提供检索开关：鉴权 → 读取 `code/data` 中的 Markdown / TXT 与 SQLite 共享文本 → 承接追问主题 → 按 Markdown 分块（500 字符，重叠 50）→ 本地 Qwen3-Embedding-0.6B + FAISS 余弦检索（最多 3 段，默认最低相似度 0.45）→ DeepSeek → 严格 JSON 与引用校验 → AI 回答，正文引用可打开同一次召回对应的完整原文。页面不再追加独立原文摘录；服务端仍返回原文来源数据。

普通 DeepSeek 分支仅保留为内部兼容 API，页面始终使用知识库。自然语言未命中仍可先整理问题后重检；数字无意义输入不调用嵌入模型或云模型。没有原文命中时不生成知识库答案。

提示词、LLM 传输、Markdown 读取、嵌入、FAISS 分别放在参考项目对应模块中；后端适配器负责原有权限、追问、来源结构和引用校验。没有复制参考目录的 `.env`、密钥、旧数据库或学习资料。

```text
code/
├── data/
│   ├── 中药基础知识（详解版）.pdf          # 指定原件，不直接参与向量切分
│   ├── 中药基础知识（详解版）.md           # 实际检索正文
│   └── 中药基础知识（详解版）.source.json  # 来源、校验值与转换记录
├── db/                                    # 生成的索引、JSON 元数据（不提交）
├── models/                                # 本地模型（不提交）
├── RAG/
│   ├── Embeddings.py                      # Qwen3 last-token pooling
│   ├── faiss_db.py                        # 归一化、搜索、落盘、完整性校验
│   ├── llm.py                             # DeepSeek 兼容 HTTP JSON 请求
│   ├── prompt.py                          # 资料与普通 AI 两种提示词
│   └── utils.py                           # 递归读文档、分块、索引更新和检索
├── scripts/import_pdf.py                  # 本次指定 PDF 的校验导入器
├── .env.example
├── download.py                            # 显式下载模型
├── main.py                                # 建库、原文检索、终端问答
└── requirements.txt                       # 复用后端依赖清单
```

## 首次准备

在项目根目录执行，复用后端虚拟环境。尚无虚拟环境时，先按 README 的后端安装步骤建立。

```powershell
backend\.venv\Scripts\python.exe -m pip install -r code/requirements.txt
# Hugging Face 官方仓库：
backend\.venv\Scripts\python.exe code/download.py
# 或 Qwen 官方 ModelScope 仓库（逐文件 SHA-256 校验）：
backend\.venv\Scripts\python.exe code/download.py --source modelscope
backend\.venv\Scripts\python.exe code/main.py --rebuild
backend\.venv\Scripts\python.exe code/main.py --query "陈皮的功效"
```

两个下载命令任选其一。模型约 1.2 GB；本机 CPU 默认保留原始 BF16 权重、逐层以 FP32 计算，需要额外运行内存，首次建库需等待。服务端只加载本地已有模型，不会自动联网下载。默认预热开启时，缺依赖、模型或资料不可读会使启动失败并记录错误；关闭预热时请求返回明确 503，不伪造向量结果。知识库浏览器等待上限为 180 秒，Next.js 代理为 190 秒，普通 AI 浏览器等待仍为 45 秒。

准备完成后重启后端，原有前端入口不变。页面直接发送即可使用原文 + AI，无需勾选。也可运行 `backend\.venv\Scripts\python.exe code/main.py` 进行终端问答；未配置 DeepSeek 时仅显示检索原文。`--query` 始终只检索，不调用 DeepSeek。

## 提速与计时

仅使用今天的 Qwen3 + FAISS 向量链路，不用旧关键词快速路径。应用配置中的 `RAG_ENABLED=false` 旧入口会拒绝启动。保持原模型和索引格式；可选 ONNX 权重下载较慢，本次未启用、没有切换模型。

向量路径用内存 LRU 缓存查询向量（默认 128 条，0 关闭），这一层只缓存向量，不缓存来源或搜索结果。资料修改 / 删除后仍查询更新后的索引；模型或嵌入配置变化清理缓存。查询文本不写入该缓存的磁盘文件，重启清空。

另有独立的已校验回答缓存：每账号隔离，最多 16 条、120 秒；账号、原始问题、解析问题、历史、实际检索片段或完整原文哈希变化即不复用。仅缓存通过 schema 与引用校验的回答，不缓存失败 / 未命中；不落盘，重启清空。用当前检索结果重新附加真实来源。

口语省略追问先理解后只检索一次，避免先跑一次向量再丢弃结果。嵌入前向显式设置 `use_cache=false`，不保存生成用 KV 缓存。默认在服务启动期间加载并实际预热模型，完成后才提供 API；本机本次启动准备 48.24 秒。关闭 `RAG_WARMUP` 后恢复延迟初始化，首条向量请求会承担该开销。

CPU 默认保留此 Qwen 检查点的原始 BF16 权重，Linear、Embedding 和归一化实际以 FP32 计算；避免整模型权重常驻 FP32，并保持原有计算精度。配置 `EMBEDDING_CPU_STORAGE=fp32` 可恢复整模型 FP32 存储对照。未启用未通过完整一致性验证的 8 位量化或 ONNX 替代模型，保持现有索引；这次没有做流式输出或更换云模型。内存紧张或长时间空闲后的换页仍会影响延迟。

`/api/chat` 成功响应新增 `Server-Timing`：load、context、retrieval、understanding（按需）、generation、answer_cache（缓存命中时）、total，单位毫秒。后端同样记录这些阶段耗时，错误请求也记录已执行阶段；不记录问题、原文、账号或密钥。响应 total 不包含鉴权前处理和最终 JSON 序列化。详见 [性能验收](RAG-PERFORMANCE-QA.md)。

## 资料与索引更新

数据统一放在 `code/data`，UTF-8，优先使用带标题层级的 `.md`，兼容 `.txt`，递归读取子目录。PDF 和来源 JSON 不重复入库。不索引演示、未就绪或空资料，不允许链接到目录之外的文件。单份文件最多 10 MB。

页面已保存的共享 MD / TXT 继续由 SQLite 管理，也参加同一个向量索引。数据目录属于部署者维护的知识库，页面的上传 / 删除权限继续只作用于 SQLite 共享资料。左侧基础资料阅读与 Word 下载保持原有接口；RAG 正文取自新的 Markdown，不把同源 DOCX 再索引一遍。

每次知识库提问会核对当前资料内容、模型标识 / 本地模型文件信息和切分参数。没有变化直接加载或复用索引；资料新增、修改或删除时重建当前快照，复用未变片段的向量，仅对新片段计算嵌入。删除后的片段不会继续返回。大量资料更新建议提前运行 `--rebuild`，避免首次提问等待建库超过浏览器 180 秒的知识库请求期限（普通 AI 仍为 45 秒）。

FAISS 使用归一化 `IndexFlatIP`，数据保存在 `faiss_db.<生成编号>.index` 与 `faiss_db.json`。二进制索引先写入，再原子切换 JSON 清单，校验哈希和记录数，替代参考实现中的 pickle。索引只保存一份当前语料快照；当前为单进程后端，不支持多个服务进程共用同一索引目录并行写入。

指定 PDF 的一次性导入命令：

```powershell
backend\.venv\Scripts\python.exe code/scripts/import_pdf.py "D:\资料\中药基础知识（详解版）.pdf"
```

本 PDF 为 69 页。导入器将 PDF 文本与现有结构化章节模板逐字校验，仅移除空白、页码和 4 处跨页重复表头，保留 38,084 个非空白正文字符及 7 张表格，再导出 Markdown。正文不同即停止，不能把该脚本当作通用 PDF 转换工具；共享知识库的通用 PDF / Word 上传仍待接入。

## 配置

配置读取顺序：系统环境 → `backend/.env` → `code/.env` → 默认值。相对数据、索引、模型缓存路径基于 `code/`，不依赖启动工作目录。模型可以填写 Hugging Face 标识或本地模型绝对路径；ModelScope 下载到 `code/models/Qwen3-Embedding-0.6B`，默认模型标识会优先读取该本地目录。

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| RAG_ENABLED | true | 仅允许新向量 RAG，false 旧入口拒绝启动 |
| RAG_DATA_PATH | data | 原始资料目录 |
| FAISS_PERSIST_DIR | db | 索引目录 |
| EMBEDDING_MODEL | Qwen/Qwen3-Embedding-0.6B | 本地嵌入模型 |
| EMBEDDING_DEVICE | cpu | CPU 或已正确配置的 cuda |
| EMBEDDING_CPU_STORAGE | bf16 | CPU 权重存储 bf16 / fp32；此 Qwen 原始 BF16 权重逐层以 FP32 计算 |
| RAG_WARMUP | true | 启动时准备索引并预热，完成后才提供 API |
| EMBEDDING_CACHE_DIR | models | 本地模型缓存 |
| RAG_CHUNK_SIZE | 500 | 分块字符数，128–2000 |
| RAG_CHUNK_OVERLAP | 50 | 重叠字符数，小于分块大小的一半 |
| RAG_TOP_K | 3 | 最多召回 1–3 个片段，与引用上限一致 |
| RAG_MIN_SCORE | 0.45 | 向量回退的最低余弦相似度，0–1 |
| RAG_QUERY_CACHE_SIZE | 128 | 内存查询向量缓存上限，0–1024；0 关闭 |
| RAG_ANSWER_CACHE_SIZE | 16 | 已校验回答缓存条数上限，0–128；0 关闭 |
| RAG_ANSWER_CACHE_SECONDS | 120 | 回答缓存有效秒数，0–600；0 关闭 |

DeepSeek 沿用 `backend/.env` 的 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL`。不需要将密钥复制到 `code` 或前端。资料继续作为不可信参考文本，不能覆盖系统指令；AI 补充与原文引用边界不变。

与参考实现相比，Qwen3 嵌入采用[官方示例的 last-token pooling 与查询指令](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B#transformers-usage)，避免对 padding 直接求均值。运行依赖沿用当前项目已验证的 NumPy，新增 PyTorch / Transformers / FAISS，不照搬参考项目与本机 Python 3.14 不兼容的旧版本。完整版本见后端 requirements-lock.txt。

## 验证

自动回归：后端 `python -m unittest discover -s tests -v`；前端 `pnpm typecheck`、`pnpm test`、`pnpm build`。新增测试覆盖递归读取、分块与重叠、阈值、数字输入、索引复用、资料删除 / 更新、模型与分块配置变化、损坏索引、权限和普通 AI 隔离。受控测试向量只测试行为，真实 Qwen 召回单独核验。

实际模型召回、API、构建与浏览器核验结果见 [RAG 验收](RAG-QA.md)。向量召回不等于事实核验；仍需用真实语料持续评测阈值与召回质量。
