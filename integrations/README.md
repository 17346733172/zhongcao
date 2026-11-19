# 仿真平台默认用时配套补丁

2026-11-18：已将[当前服务器版本补丁](simulator-device-defaults-server.patch)部署到现有仿真服务器，测试方案可真实修改和保存当前默认用时。该补丁基于 `checkpoint-20261116` 源码适配，保留服务器既有的内存缓存、5 秒检查点及拆分状态表。以下原补丁仍对应本机开发仓库，两个补丁不能混用。验证及上线记录见[真实保存接通记录](../docs/DEVICE-DEFAULTS-ENABLE-QA.md)。

本草“测试方案”通过接收端的 `GET /api/v1/device-defaults` 和 `POST /api/v1/device-defaults/{kind}` 读取及保存 13 类设备默认用时。当前连接服务器已提供这两个接口；页面若仍保留先前的只读结果，点击「重新读取」即可重新确认能力。旧服务器回退为只读的兼容处理继续保留。

[simulator-device-defaults.patch](simulator-device-defaults.patch) 基于本机 `D:\中药煎药流程仿真平台-dev` 当前后端准备，尚未修改该仓库或部署到服务器。只包含五个关联后端 / 测试文件，保留该仓库已有的其他更改。

在接收端仓库根目录先检查并应用：

```powershell
git apply --check D:/本草/integrations/simulator-device-defaults.patch
git apply D:/本草/integrations/simulator-device-defaults.patch
cd backend
# 将 DECOCTION_TEST_DATABASE_URL 指向独立 PostgreSQL 测试库，然后执行：
.venv/Scripts/python.exe -m unittest discover -v
```

补丁将配置及独立修订号保存到既有 PostgreSQL 状态 JSON，并在同一事务记录 `device.defaults_updated` 事件；不需要改表，不修改已创建批次的步骤。默认值范围为 6–7200 秒。后续新建批次的固定工序使用新默认值；浸泡、先煎、一煎和二煎的默认值用于之后新录入的处方，处方显式填写的工艺参数优先，显式关闭二煎仍生效。若默认后下时间不短于新的默认一煎时长，则调整到一煎的三分之一以内；明确给出的后下参数冲突则拒绝录入，不静默覆盖。

接口使用既有 API Key 保护，保存需带 `expected_revision`，并发版本不符返回 409；一次保存只改一个分类。默认值不修改模块常量，旧状态缺少配置字段时沿用原始默认值。

当前服务器版本已在本机独立 PostgreSQL 17 上完成全部 63 项回归，无跳过；本草 17 项相关接口回归通过。按用户明确授权备份并更新服务器后，原 71 张处方、71 个批次、129 台设备及既有批次步骤均保留，恢复原运行状态。真实本草接口已确认保存回执、旧修订号冲突及重新读取，验证保存采用原值，未改变任何默认用时数值。原开发仓库版本的首次 58 项运行中曾有 50 项因缺少测试数据库而跳过，仅作为历史记录，不代表本次服务器版本验收结果。
