# 系统直接判定与新增审核依据验收

日期：2026-10-28。规则版本：2026-10-28.7。

## 结果与边界

3.1 由系统直接给出通过 / 不通过 / 待补充信息，并写明判断依据，不再用「待药师复核」替代系统结论。通过明确限定为本次确认数据和已覆盖项目的辅助审核；实际调配授权、签名与完整诊疗适宜性不由系统伪造。五节正文、复制、补充清单及返回字段定位继续保留，旧报告自动重查。

Finding.blocking 区分持续提醒与未满足的审核条件。人参—五灵脂十九畏、配伍禁忌、数据异常、超出采用参考范围及煎法要求未明确等为阻断项。真实缺失信息待补充；无阻断项通过本次系统检查，普通吴茱萸或乌头类用药提醒仍保留。顶层 status 与 conclusion.status 一致。

## 接入依据

- [岳阳市卫健委转载《中国药典》（2025年版）人参条目](https://wsj.yueyang.gov.cn/75523/75526/content_2349014.html)：3～9 g、另煎兑服，不宜与藜芦、五灵脂同用；十九畏歌诀与内置资料交叉核对。仅接入人参—五灵脂这一新增十九畏组合，不声称完整覆盖。
- 吴茱萸采用内置资料与用户给出的 2～5 g 参考口径，核查有小毒、不宜多用久服等注意；未取得完整现行药典吴茱萸条目时不冒称已核验该条目全文。
- 五灵脂 5～10 g 明确为用户提供常用参考口径，不标为已核验药典条目；[公开政府煎药说明](https://www.wuhe.gov.cn/zfxxgk/public/25641/51091076.html)支持包煎要求。具体按适用饮片标准执行。
- 甘草继续采用内置 2～10 g 及既有长期 / 大量使用风险提示，不虚构患者已经发生高血压或低钾。
- [香港卫生署乌头类资料](https://www.cmro.gov.hk/html/gb/useful_information/public_health/pamphlet/The_safe_use_of_Chinese_medicines_containing_aconitum_alkaloids.html)核对炮制、每剂量、配伍及用药注意。先煎时长采用[北京市卫健委 / 北京朝阳医院公开说明](https://wjw.beijing.gov.cn/bmfw_20143/jkzs/jksh/202307/t20230727_3208581.html)的核查口径：附子至少 30 分钟、川乌 / 草乌至少 60 分钟；这属于本次系统采用条件，不当成所有患者或机构统一的实际操作标准，也不能验证实际煎煮。无法解析、否定表述或时长不足均不通过相应检查。
- [《处方管理办法》](https://www.nhc.gov.cn/yzygj/c100068/200602/890d7c8eb1d64405a060922c93c9f900.shtml)及[2018 年处方审核规范通知](https://www.nhc.gov.cn/wjw/c100175/201807/1774578ad7ad410491c060f684947639.shtml)作为处置依据链接，不虚构已联系医师、已拒绝调配或已上报。

## 验证

新增 5 项关键回归，完整后端 92 项通过；最终仅整理依据顺序和标点后，处方专项 39 项再通过。前端类型检查、22 项回归及独立源码副本 `next build --webpack` 成功。

Edge 使用真实 Next.js 3118 → FastAPI 8118、临时 SQLite 和随机账号，录入项目虚构样例二的 10 味药原方。系统明确判不通过，并列人参 / 五灵脂十九畏、吴茱萸每剂 10 g 超出采用 2～5 g 参考范围、人参未另煎及五灵脂未包煎。页面、复制和 390 / 320px 均一致。

在隔离测试中手动移除五灵脂、将人参记录改为另煎兑服、将吴茱萸改为 5 g 后，系统已覆盖检查无阻断项并明确通过，普通吴茱萸提醒仍保留；这些是测试操作，不是系统自动给患者改方。清空真实必需信息时才待补充，补齐后恢复相应系统结论。未模拟业务响应或调用模型；浏览器无页面异常与业务 API 5xx。通过不代表已完成真实临床审方验证。

证据：[验收记录](../design/prescription-decision-qa/result.json)、[原方不通过 Markdown](../design/prescription-decision-qa/failed-report.md)、[修改后系统通过 Markdown](../design/prescription-decision-qa/passed-report.md)、[不通过结构](../design/prescription-decision-qa/failed-report.json)、[通过结构](../design/prescription-decision-qa/passed-report.json)、[桌面不通过](../design/prescription-decision-qa/desktop-system-failed.png)、[320px 系统通过](../design/prescription-decision-qa/mobile-320-system-passed.png)。桌面与手机截图已目视核验。
