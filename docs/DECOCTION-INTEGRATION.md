# 两个项目的后端对接

更新于 2026-11-11。

本草知问负责识别、人工核对和系统检查，煎药流程仿真平台负责接收匿名处方、人工审核及仿真批次。两个后端通过 HTTP API 连接，各自维护数据库。

```mermaid
flowchart LR
    UI[本草检查结果页] --> B[本草处方上传接口]
    B --> A[煎药平台适配模块]
    A --> G[HTTPS 网关]
    G --> R[仿真平台处方路由]
    R --> S[Service 与 Store]
    S --> DB[(仿真平台 PostgreSQL)]
    DB --> Review[平台人工审核]
    Review --> Batch[创建仿真批次]
```

## 代码入口

| 项目 | 文件 | 职责 |
| --- | --- | --- |
| 本草 | `backend/app/prescriptions/routes.py` | 登录鉴权、请求接收、调用适配模块 |
| 本草 | `backend/app/prescriptions/models.py` | `SimulationUploadRequest` 与 `SimulationUploadResult` |
| 本草 | `backend/app/integrations/decoction.py` | `build_simulation_payload` 转换字段，`upload_to_simulation` 认证、重试及核对回执 |
| 本草 | `backend/app/config.py` | 服务地址、API Key 与 HTTP Basic 环境配置 |
| 本草 | `backend/app/prescriptions/simulation.py` | 旧版诊断脚本的兼容导入 |
| 仿真平台 | `backend/app/prescription_routes.py` | 处方录入、分页查询、详情、人工审核 |
| 仿真平台 | `backend/app/models.py` | `PrescriptionCreate`、`Herb`、`Review` 输入边界 |
| 仿真平台 | `backend/app/service.py` | 编号唯一性、待审核状态、审核和批次业务 |
| 仿真平台 | `backend/app/store.py` | PostgreSQL 事务与事件保存 |

HTTP 接口是两项目之间的调用边界。项目部署时安装各自的依赖，通过服务地址连接。

数据中心通过 `backend/app/data_center.py` 读取相同配置实例的 `GET /api/v1/simulation` 和 `GET /api/v1/prescriptions`，对登录用户提供 `/api/data-center/snapshot` 与 `/api/data-center/prescriptions`。读取覆盖该实例全部处方、全部设备和报警；处方使用服务端分页及审核状态过滤。仿真平台项目路径仅用于核对接口，运行时不依赖该源码目录。概览 / 设备自动更新，处方进入标签及手动操作时读取；不触发运行、审核、修复或其他写操作。详情见[数据中心验收](DATA-CENTER-LIVE-QA.md)。

## 接口和编号

1. 本草 `POST /api/prescriptions/check` 为当前报告生成 `simulation_upload_id`。
2. 用户点击上传，页面向本草 `POST /api/prescriptions/simulation` 提交 `upload_id`、`doses`、`medicines`。
3. 本草完成字段转换，向仿真平台 `POST /api/v1/prescriptions` 发送匿名处方。
4. 仿真平台创建后返回 HTTP 201，状态为 `pending_review`。
5. 平台工作人员通过 `POST /api/v1/prescriptions/{id}/review` 审核，审核通过后可创建批次。

本草上传入口要求有效登录、`knowledge:read` 和 `X-CSRF-Protection: 1`。外部编号由 `BENCAO-` 加上传 UUID 的大写十六进制组成，匿名编号使用相同 UUID 加 `SIM-` 前缀。同一份报告重试复用编号，修改后重新检查会得到新编号。

## 字段对应

| 本草字段 | 发给仿真平台的字段 | 转换与校验 |
| --- | --- | --- |
| `upload_id` | `external_no`、`patient_code` | 生成外部编号与匿名编号 |
| `doses` | `doses` | 1–30 剂，缺失时要求补充 |
| `medicines[].name` | `herbs[].name` | 保留已核对药名，空值和相同药名重复时拒绝上传 |
| `dose`、`unit`、`dose_scope` | `grams_per_dose` | 克直接使用，毫克除以 1000，总量再除以剂数 |
| `dose`、`unit="片"`、`dose_scope` | `unit="piece"`、`quantity_per_dose` | 按每剂片数传递；总量除以剂数，保留计数单位，不猜测克数 |
| `method` | `method` | 常规为 `normal`，先煎为 `pre_decoct`，后下为 `late_add`，包煎为 `bag` |

每剂克数要求大于 0 且不超过 1000 g。片数可为正小数，上限为每剂 100 万片；平台保存片数后等待审核，审核时按药名补充 `herb_grams_per_dose`，每项为每剂这些片数的实测总克数，不是单片默认克重。未称重不能审核通过或计算水量，驳回处方无需补称重。未知口径、其他未支持的单位及无法映射的煎法返回可核对提示。

例如生姜每剂 3 片、5 剂上传为 `{"name":"生姜","unit":"piece","quantity_per_dose":3,"method":"normal"}`；平台显示每剂 3 片、合计 15 片，`grams_per_dose` 初始为空。审核补充 `{"approved":true,"operator":"演示审核员","herb_grams_per_dose":{"生姜":4.5}}` 后，仍保留 3 片，并用实测 4.5 g/剂参与水量计算。示例数字仅用于验证字段含义，不是药材换算标准。

请求只向平台传递上述字段。包装、优先级和工艺采用平台当前默认值，处方中附带的具体煎煮时长仅映射工序类别。患者年龄、诊断、过敏史、原文和检查报告由本草流程处理。

以下为独立测试环境使用的请求示例。

```json
{
  "upload_id": "12345678-1234-4234-8234-1234567890ab",
  "doses": 3,
  "medicines": [
    {"name": "演示常规饮片", "dose": "36000", "unit": "mg", "dose_scope": "total", "method": "常规"}
  ]
}
```

转换后的平台请求如下。

```json
{
  "external_no": "BENCAO-123456781234423482341234567890AB",
  "patient_code": "SIM-123456781234423482341234567890AB",
  "doses": 3,
  "herbs": [
    {"name": "演示常规饮片", "grams_per_dose": 12.0, "method": "normal"}
  ]
}
```

本草向页面返回以下结构，`already_uploaded` 为 true 时表示平台已存在该编号。

```json
{"external_no": "BENCAO-123456781234423482341234567890AB", "already_uploaded": false}
```

## 地址和认证

本草实际连接哪个实例，由本草 `backend/.env` 中的 `DECOCTION_BASE_URL` 决定。本机 `127.0.0.1:8080` 和服务器各自保存处方，浏览器中查看的平台应与接收实例对应。

下面的域名和凭据均为占位值。

```dotenv
DECOCTION_BASE_URL=https://simulation.example
DECOCTION_API_KEY=
DECOCTION_HTTP_USERNAME=CHANGE_ME
DECOCTION_HTTP_PASSWORD=CHANGE_ME
```

| 配置 | 生效位置 |
| --- | --- |
| 本草 `DECOCTION_BASE_URL` | 平台服务根地址，适配模块追加 `/api/v1/prescriptions` |
| 本草 `DECOCTION_API_KEY` | 向平台发送 `X-API-Key`，与平台后端的同名配置一致 |
| 本草 `DECOCTION_HTTP_USERNAME` / `DECOCTION_HTTP_PASSWORD` | HTTPS 网关要求 HTTP Basic 时同时填写 |
| 平台 `DECOCTION_API_KEY` | FastAPI 接口鉴权 |
| 平台 HTTPS 网关 | 验证 HTTP Basic，并将请求转发至平台后端 |

配置由后端读取，修改本草 `.env` 后重启本草后端。网关认证使用 HTTPS，本地回环地址可用于 HTTP 测试。基础配置及启动命令见 [开发说明](DEVELOPMENT.md)，接收侧细节见仿真平台项目的 `docs/BENCAO-INTEGRATION.md`。

## 重试和错误

| 情况 | 本草处理 |
| --- | --- |
| 平台 201，编号一致且状态为 `pending_review` | 返回新录入回执 |
| 平台 409，错误码 `duplicate_prescription` | 返回该编号已录入的回执 |
| 平台 401 / 403 | 返回认证配置提示 |
| 本地字段或平台字段校验不通过 | 返回 422，页面提供「确认药材」入口 |
| 含片数的请求被旧平台拒绝 | 返回 502 并提示确认接收端版本，保留报告供升级后重试 |
| 网络超时或连接中断 | 同编号最多尝试 3 次，仍未确认则保留报告供再次上传 |
| 非预期状态或响应格式 | 返回无法确认接收的反馈 |

单次连接等待 10 秒、读取 15 秒、写入与连接池等待各 5 秒。页面为整个上传流程保留 120 秒。平台在事务内检查外部编号唯一性，因此首次写入后响应丢失时，重试可以取得已录入回执。

遇到列表中缺少处方时，先检查接收实例和状态筛选。遇到 401 时区分网关 HTTP Basic 与后端 API Key。连接失败日志仅包含尝试次数和异常类型，可用于区分 `ConnectTimeout`、`ReadTimeout`。

## 维护与验证

本草后端在 `backend` 目录执行以下回归。

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

仿真平台后端在自己的 `backend` 目录执行以下回归，数据库测试按其开发说明使用独立测试库。

```powershell
.venv\Scripts\python.exe -m unittest discover -v
```

本草 OpenAPI 的「处方仿真对接」标签列出上传入口与回执模型。平台 OpenAPI 列出接收字段、默认值和重复编号的 409 语义。调整字段时同步核对两端模型、转换函数与此文档。
