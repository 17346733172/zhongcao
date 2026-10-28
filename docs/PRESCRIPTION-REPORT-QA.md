# 五节处方审核意见验收

日期：2026-10-28。规则 / 报告版本：2026-10-28.6。

## 当前结果

按用户提供的正文样式显示 3.1 审核结论、3.2 主要问题、3.3 毒性药材与煎法核查、3.4 其他核查、3.5 处理建议。结果用连续文字、项目符号和编号建议展示，结论与建议前缀加粗。删除旧计数、彩色卡片、药物明细折叠、版本 / 范围 / 边界面板和报告内批量口径按钮；修改数据使用现有底部复查操作。

后端 narrative.py 根据本次已确认数据、实际 findings 和 conclusion 构造五节 sections。原 API 元数据保留兼容，前端不再展示。页面与复制仅消费同一 sections，复制为 Markdown 标题、加粗及列表，不在客户端另生成临床判断。

主要问题标题保留实际药名及炮制别名；制附子、法半夏的剂量比较仅在成人条件、每剂量和可用克数完整时执行。儿童、总量、未明单位不套用成人每剂范围；重复记录先核实合计口径。煎法只陈述原处方记录，不将注明先煎等同于实际完成操作。十九畏未建立完整库，正文明确需药师核查。替代方案由医师决定，不自动补药名和剂量；必要签字等按适用规范及机构制度核实，不照抄样例当成普遍要求。

## 依据

- [香港卫生署：生附子和制附子](https://www.cmro.gov.hk/html/b5/useful_information/public_health/publication/AdverseEvents8.html)：制附子公开参考用量、炮制和先煎 / 久煎提示。
- [香港卫生署：生半夏和制半夏](https://www.cmro.gov.hk/html/b5/useful_information/public_health/publication/AdverseEvents7.html)：半夏公开参考用量及乌头类配伍注意。
- [香港卫生署：含乌头类生物碱中药材](https://www.cmro.gov.hk/html/gb/useful_information/public_health/pamphlet/The_safe_use_of_Chinese_medicines_containing_aconitum_alkaloids.html)：相关风险与用药提示。
- [北京市中医药管理局 / 丰台区中医医院：秋季防过敏，别忘稳血压](https://zyj.beijing.gov.cn/sy/whkp/202610/t20261009_4894097.html)：甘草长期 / 大量使用与血压、低钾风险及合并用药核对。
- 项目内置基础资料：有限配伍与砂仁特殊煎法。未核实的现行药典全文不以完整药典结论输出。

## 验证

前端类型检查、22 项前端回归、独立源码副本 `next build --webpack` 和完整后端 83 项通过，本次增加 4 项报告接口回归。覆盖动态标题、当前数字与方法、改后重算、原始别名、多个配伍组合、儿童 / 总量 / 单位边界及避免套用示例事实。

Edge 使用真实生产代理 Next.js 3116 → FastAPI 8116、临时 SQLite 和随机账号。录入用户虚构的 10 味药示例，验证固定五节、加粗结论、项目符号、编号及子项、页面和剪贴板一致；旧卡片与面板不存在。修改处方后重新生成全部五节，原禁忌标题和剂量事实不残留。真实缺失信息仍写在 3.4 正文中。390 / 320px 长标题、链接和建议可换行，无横向溢出；桌面与 320px 截图已打开目视核验。

未模拟业务 API 或调用模型。首次生产构建后仅修改后端正文措辞，最终浏览器验证复用该未变更构建并重新启动后端，全部通过。临床完整性仍受现有规则覆盖范围限制，界面核验不作为真实临床审方验证。

证据：[验收结果](../design/prescription-narrative-qa/result.json)、[实际五节 Markdown](../design/prescription-narrative-qa/example-report.md)、[结构化报告](../design/prescription-narrative-qa/example-report.json)、[桌面报告](../design/prescription-narrative-qa/desktop-report-top.png)、[煎法段落](../design/prescription-narrative-qa/desktop-method-review.png)、[320px 建议](../design/prescription-narrative-qa/mobile-320-advice.png)、[修改后报告](../design/prescription-narrative-qa/desktop-edited-report.png)。

## 具体补充信息提示（.6）

3.1 结论下增加「需补充信息」清单。服务端以现有 findings 和本次已确认字段为依据，区分实际缺失的患者资料与药物行的药名、剂量、单位、口径，不添加肝肾功能等尚未作为既有必填项的要求；无缺失时返回空数组。列表写入原 sections，页面与 Markdown 复制保持一致。

「去补充信息」保留当前数据返回核对页，并聚焦首个缺失字段；药物控件可随表格横向滚动到可见位置。用户补充后仍需重新勾选确认，重查后移除已补齐项。十八反等优先不通过的情况仍会列出真实缺失项，补齐资料不等于解除原有风险。

验证：后端新增 4 项回归，完整 87 项通过；前端类型、22 项回归与独立 `next build --webpack` 通过。Edge 真实 Next.js 3117 → FastAPI 8117、临时 SQLite、随机账号，使用虚构处方验证：只缺年龄 / 过敏史时仅提示这两项；药物缺单位不会被笼统提示为剂量也缺失；点击入口准确聚焦年龄、过敏史或药物单位，剂量及其他数据不变；补齐后清单消失。390 / 320px 无横向溢出，药物字段可定位并编辑。含配伍禁忌的病例补齐信息后仍保持不通过。没有模拟 API 或调用模型；桌面和 320px 提示截图已打开核验，本地前后端服务返回正常。

证据：[本次验收](../design/prescription-supplement-qa/result.json)、[缺失清单 Markdown](../design/prescription-supplement-qa/missing-report.md)、[结构化结果](../design/prescription-supplement-qa/missing-report.json)、[桌面患者字段提示](../design/prescription-supplement-qa/desktop-patient-gaps.png)、[桌面药物字段提示](../design/prescription-supplement-qa/desktop-medicine-gap.png)、[320px 提示](../design/prescription-supplement-qa/mobile-320-missing-prompt.png)、[320px 定位单位](../design/prescription-supplement-qa/mobile-320-focused-unit.png)。
