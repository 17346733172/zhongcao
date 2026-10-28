"""Build the user's five-section review from confirmed data, never from model prose."""
import re
from collections import defaultdict
from decimal import Decimal
from .models import Prescription, ReportItem, ReportSection, ReportSource
from .rules import ACONITE, PINELLIA, REFERENCE, REGULATION, canonical
from .audit_knowledge import GINSENG_SOURCE, PROFILES, PRESCRIPTION_LAW, AUDIT_STANDARD

FUZI = "https://www.cmro.gov.hk/html/b5/useful_information/public_health/publication/AdverseEvents8.html"
LICORICE = "https://zyj.beijing.gov.cn/sy/whkp/202610/t20261009_4894097.html"
PROCESSED_FUZI = {"制附子", "黑顺片", "白附片", "炮附片", "淡附片"}
PROCESSED_PINELLIA = {"法半夏", "姜半夏", "清半夏", "制半夏"}


def item(text, lead="", children=None, sources=None):
    return ReportItem(text=text, lead=lead, children=children or [],
                      sources=[ReportSource(label=label, url=url) for label, url in sources or []])


def names(medicines):
    return "、".join(dict.fromkeys(m.name or "药名未提供" for m in medicines))


def dose_text(medicine):
    scope = {"per_dose": "每剂", "total": "总量", "unknown": "口径待确认"}[medicine.dose_scope]
    return f"{medicine.name or '未命名饮片'} {medicine.dose or '剂量未提供'} {medicine.unit or '单位未提供'}（{scope}）"


def dose_review(prescription, medicine, group, low, high, reference_label="公开资料所列"):
    adult = prescription.age is not None and prescription.age >= 18 and prescription.pregnancy != "yes" and (prescription.sex == "male" or prescription.pregnancy == "no")
    if len(group) > 1:
        return "存在同类饮片重复记录，须先核对重复情况和合计剂量。"
    if not adult or medicine.dose_scope != "per_dose":
        return "年龄、特殊人群条件或每剂量口径未完整确认，暂不作成人每剂参考剂量比较。"
    if medicine.unit.lower() not in {"g", "克", "mg", "毫克"} or not re.fullmatch(r"\d{1,6}(?:\.\d{1,6})?", medicine.dose):
        return "剂量数字或单位需核实后再比较参考用量。"
    value = Decimal(medicine.dose) / (1000 if medicine.unit.lower() in {"mg", "毫克"} else 1)
    if value <= 0:
        return "剂量数值异常，须核对后重新审核。"
    position = "位于" if Decimal(low) <= value <= Decimal(high) else "超出"
    return f"按每剂 {value.normalize():f} g 记录，{position}{reference_label} {low}～{high} g 参考范围；个体用量仍须结合病情复核。"


def method_text(medicine):
    return f"原处方注明“{medicine.method}”。" if medicine.method else "原处方未注明煎法，需补充核实。"


def finding_text(finding):
    detail = {
        "missing_dose": "剂量或单位未记载，请补充原文记录后评估。",
        "dose_scope": "每剂量口径待确认，暂不能比较每剂参考用量。",
        "dose_total_review": "已按总量记录，需核对总剂数及每剂实际用量后比较参考范围。",
        "invalid_dose": "剂量数值异常，请核实原文、小数点及正数记录要求。",
        "duplicate_herb": "同一饮片或炮制别名重复出现，请核对是否重复开具或重复录入。",
        "unknown_herb": "药名或炮制规格尚需与原处方、药材资料进一步核对。",
        "unit_review": "计量单位需与原文核对，由药师确认实际用量。",
        "child_review": "儿童用量需结合年龄、体重及具体病情单独复核。",
        "pregnancy_review": "妊娠用药需结合孕周与适应证，逐味核查禁忌及注意事项。",
    }.get(finding["code"], finding["detail"])
    if finding["code"] == "reference_dose":
        detail = finding["detail"].split("。", 1)[0].replace("本地资料", "参考资料") + "；需结合证候、疗程和原方复核。"
    label = "、".join(finding["medicines"])
    return (label + "：" if label else "") + detail


def build_sections(prescription: Prescription, findings, conclusion, missing_information):
    groups = defaultdict(list)
    for medicine in prescription.medicines:
        groups[canonical(medicine.name)].append(medicine)
    pairs = [f for f in findings if f["code"] in {"incompatible_pair", "nineteen_incompatible_pair"}]
    blocking = [f for f in findings if f.get("blocking", True)]
    pair_names = ["与".join(names(groups[base]) or base for base in f["medicines"]) for f in pairs]
    primary = []
    primary_title = "主要问题核查"
    if pairs:
        primary_title = "主要问题：" + (pair_names[0] + "同方" if len(pairs) == 1 else "多组配伍禁忌")
        for finding, pair in zip(pairs, pair_names):
            bases = finding["medicines"]
            category = "；".join(f"{names(groups[base]) or base}按{base}类饮片核查" for base in bases)
            family = "十九畏" if finding["code"] == "nineteen_incompatible_pair" else "十八反"
            primary.append(item(f"{pair}同方。{category}，命中“{family}”配伍规则。",
                                sources=[("配伍依据", finding["url"] or REFERENCE)]))
        if any(f["code"] == "nineteen_incompatible_pair" for f in pairs):
            primary.append(item("“十九畏”歌诀载“人参最怕五灵脂”。公开转载的《中国药典》（2025年版）人参条目明确提示不宜与五灵脂同用，本次按该配伍条件判为不通过。", sources=[("人参条目依据", GINSENG_SOURCE)]))
        if any(set(f["medicines"]) & {"附子", "川乌", "草乌"} for f in pairs):
            primary.append(item("用药资料提示：附子、川乌、草乌等乌头类饮片不宜与半夏、瓜蒌、贝母、白蔹、白及等同用；炮制品也需按相应配伍注意核查。",
                                sources=[("乌头类用药注意", ACONITE), ("半夏用药注意", PINELLIA)]))
            primary.append(item("应重点关注含乌头类饮片的中毒风险，包括口舌或肢体麻木、恶心呕吐、心悸、心律紊乱等；不得仅因已炮制或注明先煎而忽略配伍问题。",
                                lead="风险提示：", sources=[("风险依据", ACONITE)]))
        else:
            primary.append(item("上述组合属于已核查的传统配伍禁忌，应联系处方医师确认或修改，问题解决前暂缓调配。",
                                lead="风险提示：", sources=[("用药禁忌", REFERENCE)]))
    else:
        errors = [f for f in findings if f["level"] == "error"]
        if errors:
            primary_title = "主要问题：" + errors[0]["title"]
            primary.extend(item(finding_text(f)) for f in errors)
        elif any(f["level"] == "missing" for f in findings):
            primary_title = "主要问题：审核信息待补充"
            primary.append(item("本次需补充项目已列于 3.1 审核结论下，请对照原文完善后再完成审核。"))
        elif blocking:
            primary.append(item(f"本方所列饮片为{names(prescription.medicines)}。未命中已核查的配伍禁忌，但存在未满足的审核条件，系统判断依据见 3.1。"))
        else:
            primary.append(item(f"本方所列饮片为{names(prescription.medicines)}。已覆盖的配伍、数据及煎法检查未发现阻断问题，本次系统辅助审核通过。"))

    methods = []
    for medicine in prescription.medicines:
        base = canonical(medicine.name)
        normalized_name = re.sub(r"\s+", "", medicine.name)
        if base == "附子":
            processed = normalized_name in PROCESSED_FUZI
            detail = dose_review(prescription, medicine, groups[base], "3", "15") if processed else "炮制品种尚需核实；生附子不宜内服，不能按制附子直接判断。"
            methods.append(item(f"{dose_text(medicine)}：{detail}{method_text(medicine)}须核实合规炮制品及先煎、久煎的实际落实情况。",
                                sources=[("附子用药资料", FUZI)]))
        elif base in {"川乌", "草乌"}:
            methods.append(item(f"{dose_text(medicine)}：{method_text(medicine)}须核实炮制规格及先煎、久煎要求，由药师专项复核。",
                                sources=[("乌头类用药资料", ACONITE)]))
        elif base == "半夏":
            processed = normalized_name in PROCESSED_PINELLIA
            detail = dose_review(prescription, medicine, groups[base], "3", "9") if processed else "炮制品种未明确，须核实是否为合规炮制品，不能把生半夏按制半夏处理。"
            methods.append(item(f"{dose_text(medicine)}：{detail}{method_text(medicine)}",
                                sources=[("半夏用药资料", PINELLIA)]))
        elif base == "砂仁":
            methods.append(item(f"{dose_text(medicine)}：{method_text(medicine)}应对照原方核实后下、打碎等要求及实际操作；记录不等于已完成煎煮。",
                                sources=[("砂仁煎法资料", REFERENCE)]))
        elif base in PROFILES:
            profile = PROFILES[base]
            detail = dose_review(prescription, medicine, groups[base], profile["low"], profile["high"], profile["range_label"])
            method = "应明确" + profile["method_label"] + "。" if profile["method"] else "有小毒，不宜多用久服，应结合疗程观察。"
            dose_source = "五灵脂常用量采用用户提供的参考口径，具体按适用饮片标准执行。" if base == "五灵脂" else ""
            methods.append(item(f"{dose_text(medicine)}：{detail}{method_text(medicine)}{method}{dose_source}", sources=[("核查依据", profile["url"])]))
    if any(base in groups for base in {"附子", "川乌", "草乌"}):
        methods.append(item("含乌头类饮片，应按本机构毒性 / 高风险饮片管理制度核对储存、复核、单包先煎标识及发药交代。",
                            sources=[("饮片管理要求", REGULATION)]))
    if not methods:
        methods.append(item("本方未涉及本次重点核查的乌头类、半夏、砂仁条目；其他毒性饮片及特殊煎法仍请药师按原方核实。"))

    nineteen_hit = any(f["code"] == "nineteen_incompatible_pair" for f in pairs)
    others = [item("人参—五灵脂十九畏组合：" + ("本次已命中，见 3.2。" if nineteen_hit else "本次未命中。") + "其他十九畏组合尚未全部覆盖，不作已排除判断。")]
    pregnancy = {"yes": "已记录妊娠，应逐味复核妊娠用药禁忌。", "no": "已确认非妊娠 / 不适用。", "unknown": "尚未单独确认，需对照患者记录核实。"}[prescription.pregnancy]
    others.append(item(pregnancy, lead="妊娠相关核查："))
    missing = [f for f in findings if f["code"].startswith("missing_") and f["code"] != "missing_dose"]
    if missing:
        others.append(item("、".join(dict.fromkeys(f["title"] for f in missing)) + "；请对照原文补充，不将未知补成正常。", lead="患者及用药信息："))
    handled = {"incompatible_pair", "nineteen_incompatible_pair", "aconite_review", "evodia_notice", "special_method"} | {f["code"] for f in missing}
    for finding in findings:
        if finding["code"] in handled or (not pairs and finding["level"] == "error"):
            continue
        others.append(item(finding_text(finding),
                           sources=[("核查依据", finding["url"])] if finding["url"] else []))
    if "甘草" in groups:
        others.append(item("方中含甘草，需询问是否长期或大量使用甘草制剂、有无高血压或低钾风险，并由医师按需评估血压和电解质。",
                           sources=[("甘草用药提示", LICORICE)]))
    others.append(item("请核对同时使用的西药、中成药及其他长期用药，由药师评估重复用药与相互作用。", lead="合并用药："))
    if any(base in groups for base in {"附子", "川乌", "草乌"}):
        others.append(item("若后续经审核调配含乌头类饮片，须交代避免饮酒；出现口舌麻木、心悸、恶心呕吐、头晕等不适应立即停药并就医。",
                           lead="发药交代：", sources=[("乌头类用药提示", ACONITE)]))

    advice = []
    if pairs:
        alternatives = ["由医师决定保留的饮片及替代方案，不自行加减药或调整剂量。"]
        if len(pairs) == 1:
            left, right = [names(groups[base]) or base for base in pairs[0]["medicines"]]
            alternatives = [f"保留{left}：由医师调整或移除{right}，并决定是否需要替代方案。", f"保留{right}：由医师调整或移除{left}，并决定是否需要替代方案。"]
        advice.append(item("请处方医师结合证候修改处方，避免" + "；".join(pair + "同方" for pair in pair_names) + "。",
                           lead="首选：", children=alternatives + ["修改后重新核对配伍、每剂量和煎法，再交药师复核。"] ))
        advice.append(item("请按适用规范与本机构制度核实合用依据、必要签字、知情沟通及监测安排；药师保留审核意见和沟通记录。在问题解决前继续暂缓调配。",
                           lead="如医师认为必须合用："))
    else:
        if conclusion["status"] == "not_passed":
            advice.append(item("按 3.1 的系统判断依据逐项处理剂量、配伍、煎法或记录问题，再重新检查；问题未解决前暂缓调配。", lead="优先处理："))
        elif conclusion["status"] == "needs_information":
            advice.append(item("补齐患者资料、药物剂量、单位或口径等未确认信息，再重新检查。", lead="优先处理："))
        else:
            advice.append(item("本次系统辅助审核已通过；保留原处方与审核记录，实际调配仍应执行机构规定的专业核对流程。", lead="处理意见："))
        advice.append(item("涉及高风险饮片、特殊人群或煎法事项时，应逐项落实对应复核与发药交代。", lead="复核要点："))
    advice.append(item("保留核对、医师沟通及药师复核记录；本报告为系统辅助意见，最终由具备资质的药师确认。", lead="记录与确认："))
    if conclusion["status"] == "not_passed":
        advice.append(item("存在严重不合理用药或用药错误时，应拒绝调剂，告知医师并记录、按规定报告；未解决的问题不能因系统重查而自动解除。", lead="处置依据：", sources=[("处方管理办法", PRESCRIPTION_LAW), ("处方审核规范", AUDIT_STANDARD)]))
    return [section.model_dump() for section in [
        ReportSection(number="3.1", title="审核结论",
                      paragraphs=[item(conclusion["detail"], lead=conclusion["result"])]
                      + ([item("；".join(reason.rstrip("。；") for reason in conclusion["decision_reasons"]) + "。", lead="判断依据：")] if conclusion["decision_reasons"] else [])
                      + ([item("以下项目缺失或尚未确认，请对照原文补充。", lead="需补充信息：")] if missing_information else []),
                      items=[item(entry.prompt, lead=entry.label + "：") for entry in missing_information]),
        ReportSection(number="3.2", title=primary_title, items=primary),
        ReportSection(number="3.3", title="毒性药材与煎法核查", items=methods),
        ReportSection(number="3.4", title="其他核查", items=others),
        ReportSection(number="3.5", title="处理建议", items=advice, ordered=True),
    ]]
