import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from ..reference_document import load_reference_document
from .models import Finding, Prescription
from .audit_knowledge import ACONITE_METHOD_SOURCE, GINSENG_SOURCE, PROFILES, aconite_decoction_issue, method_recorded

RULES_VERSION = "2026-10-28.7"
REGULATION = "https://wsjk.ln.gov.cn/wsjk/zfxxgk/zc/gjjwj/2026042809553322479/index.shtml"
ACONITE = "https://www.cmro.gov.hk/html/b5/useful_information/public_health/exhibit_boards/The_Safe_Use_of_Chinese_Medicines_Containing_Aconitum_Alkaloids.html"
PINELLIA = "https://www.cmro.gov.hk/html/b5/useful_information/public_health/publication/AdverseEvents7.html"
REFERENCE = "/api/reference-document/file"
ALIASES = {alias: base for base, aliases in {
    "附子": ["附子", "制附子", "黑顺片", "白附片", "炮附片", "淡附片", "生附子"],
    "川乌": ["川乌", "制川乌", "生川乌"], "草乌": ["草乌", "制草乌", "生草乌"],
    "半夏": ["半夏", "法半夏", "姜半夏", "清半夏", "制半夏", "生半夏"],
    "甘草": ["甘草", "炙甘草", "生甘草"], "白及": ["白及", "白芨"],
    "瓜蒌": ["瓜蒌", "全瓜蒌", "瓜蒌皮", "瓜蒌子"],
    "白术": ["白术", "麸炒白术", "炒白术"],
    "人参": ["人参", "红参", "生晒参"], "芍药": ["芍药", "白芍", "赤芍"],
    "五灵脂": ["五灵脂", "醋五灵脂", "醋炙五灵脂", "炒五灵脂"],
    "吴茱萸": ["吴茱萸", "制吴茱萸"], "延胡索": ["延胡索", "醋延胡索", "醋炙延胡索"],
}.items() for alias in aliases}


def canonical(name):
    name = re.sub(r"\s+", "", name)
    return ALIASES.get(name, name)


def reference_entries():
    entries, title, lines = {}, "", []
    for block in load_reference_document().get("blocks", []):
        if block["type"] == "heading":
            if title:
                entries[title] = "\n".join(lines)
            title = re.split(r"[（(]", block["text"])[0].strip()
            lines = []
        elif block["type"] == "paragraph":
            lines.append(block["text"])
    if title:
        entries[title] = "\n".join(lines)
    return entries


def check_prescription(prescription: Prescription):
    findings = []
    def absent(value):
        return value.strip() in {"", "未知", "未提供", "不详", "未记录", "待补充", "不清楚"}
    def add(code, level, title, detail, names=None, basis="处方数据一致性规则", url=None, blocking=True):
        findings.append(Finding(code=code, level=level, title=title, detail=detail,
                                medicines=names or [], basis=basis, url=url, blocking=blocking).model_dump())
    for key, label, missing in [
        ("age", "年龄", prescription.age is None), ("sex", "性别", prescription.sex == "unknown"),
        ("diagnosis", "诊断 / 证候", absent(prescription.diagnosis)), ("allergies", "过敏史", absent(prescription.allergies)),
        ("regimen", "用法用量", absent(prescription.regimen)), ("doses", "总剂数", prescription.doses is None),
    ]:
        if missing:
            add("missing_" + key, "missing", "缺少" + label, "处方数据未提供此项，需补充后由药师复核。", basis="《医院中药饮片管理规范（2026版）》处方审核要求", url=REGULATION)
    if prescription.sex == "female" and prescription.pregnancy == "unknown":
        add("missing_pregnancy", "missing", "妊娠状态未确认", "不能从性别或年龄推断妊娠状态，需明确后复核。", basis="特殊人群用药信息核对", url=REGULATION)
    if prescription.sex == "male" and prescription.pregnancy == "yes":
        add("conflicting_metadata", "error", "性别与妊娠信息相互冲突", "请核对是否识别错误、录入错误或混合了不同处方的信息。")
    if prescription.age is not None and prescription.age < 18:
        add("child_review", "review", "未成年人处方需个体化复核", "本工具不按成人参考范围判断儿童剂量，也不进行年龄折算。", basis="适用范围边界", url=REGULATION)
    if prescription.pregnancy == "yes":
        add("pregnancy_review", "review", "妊娠用药需专项审核", "当前规则不覆盖完整妊娠禁忌库，请由药师逐味检查。", basis="特殊人群用药信息核对", url=REGULATION)
    if not prescription.medicines:
        add("empty_medicines", "error", "没有药物明细", "至少需要一味药物，不能形成有效检查。")
    groups, totals = defaultdict(list), defaultdict(Decimal)
    entries = reference_entries()
    for index, medicine in enumerate(prescription.medicines):
        name = medicine.name or f"第 {index + 1} 味药"
        base = canonical(medicine.name)
        groups[base].append(medicine)
        if not medicine.name:
            add("missing_name", "error", "药名缺失", f"第 {index + 1} 行药名为空。")
        if not medicine.dose or not medicine.unit:
            add("missing_dose", "missing", "剂量或单位缺失", "不能猜测剂量、默认克数或把片数换算为克。", [name])
        value = None
        if medicine.dose:
            try:
                if not re.fullmatch(r"\d{1,6}(?:\.\d{1,6})?", medicine.dose):
                    raise InvalidOperation
                value = Decimal(medicine.dose)
                if not value.is_finite() or value <= 0:
                    raise InvalidOperation
            except InvalidOperation:
                add("invalid_dose", "error", "剂量数字无效", "剂量必须是大于零的有限数字，请核对小数点与识别结果。", [name])
                value = None
        unit = medicine.unit.lower()
        if unit and unit not in {"g", "克", "mg", "毫克", "片", "枚", "个", "条", "ml", "毫升"}:
            add("unit_review", "review", "单位需要人工核实", f"识别单位为「{medicine.unit}」，本工具不会换算为克。", [name])
        if medicine.dose_scope == "unknown":
            add("dose_scope", "missing", "剂量口径未确认", "尚未确认此剂量是每剂量还是总量，因此未比较每剂参考剂量。", [name])
        elif medicine.dose_scope == "total":
            add("dose_total_review", "review", "已按总量记录，需核对每剂量", "当前口径已确认为总量；未自动均分为每剂量，也未比较每剂参考范围。如原文实际指每剂量，请修改口径后重新检查。", [name])
        if value is not None and medicine.dose_scope == "per_dose" and unit in {"g", "克", "mg", "毫克"}:
            totals[base] += value / 1000 if unit in {"mg", "毫克"} else value
        entry = entries.get(base, "")
        if not entry and base not in PROFILES:
            add("unknown_herb", "review", "药名尚未匹配本地条目", "请核对原药名、炮制规格或 OCR 错字；当前不自动修正药名。", [name])
        if base in {"附子", "川乌", "草乌"}:
            add("aconite_review", "review", "乌头类饮片用药提醒", "含乌头类饮片，须按原方落实炮制、先煎久煎及不良反应交代；本项为持续用药提醒。", [name], "香港卫生署：安全使用含乌头类生物碱中药材", ACONITE, blocking=False)
            processed = {"制附子", "黑顺片", "白附片", "炮附片", "淡附片", "制川乌", "制草乌"}
            if re.sub(r"\s+", "", medicine.name) not in processed:
                add("aconite_processing", "risk", "乌头类炮制规格未明确", "原药名未明确为已登记的合规炮制品，当前不能按炮制饮片通过审核。", [name], "乌头类炮制要求", ACONITE)
            method_issue = aconite_decoction_issue(medicine.method, base)
            if method_issue:
                add("aconite_method", "risk", "未满足乌头类先煎条件", method_issue, [name], "北京市卫健委 / 北京朝阳医院先煎说明（采用核查口径）", ACONITE_METHOD_SOURCE)
            if medicine.dose_scope != "per_dose" or unit not in {"g", "克", "mg", "毫克"} or value is None:
                add("aconite_dose_scope", "risk", "乌头类每剂克数未确认", "当前记录不能明确核对该乌头类饮片的每剂克数，未满足本次剂量审核条件。", [name], "乌头类用量要求", ACONITE)
            if prescription.pregnancy == "yes":
                add("aconite_pregnancy", "risk", "妊娠处方含乌头类饮片", "公开用药注意提示孕妇禁用，当前处方未通过相应用药禁忌审核。", [name], "乌头类用药注意", ACONITE)
        profile = PROFILES.get(base)
        if profile and profile["method"] and not method_recorded(medicine.method, profile["method"]):
            add("required_method", "review", profile["method_label"] + "要求未明确", f"原处方记为“{medicine.method or '未注明'}”，未明确{profile['method_label']}。", [name], profile["basis"], profile["url"])
        if base == "吴茱萸":
            add("evodia_notice", "review", "吴茱萸用药提醒", "吴茱萸有小毒，不宜多用久服，应结合疗程及患者情况观察。", [name], "内置基础资料：吴茱萸", REFERENCE, blocking=False)
        if base == "砂仁" and not method_recorded(medicine.method, "后下"):
            add("special_method", "review", "特殊煎法未明确", "本地基础资料提示砂仁需核对后下要求，请与原处方及药师核实。", [name], "本地《中药基础知识（详解版）》砂仁条目", REFERENCE)
        if prescription.pregnancy == "yes" and base == "半夏":
            add("pinellia_pregnancy", "risk", "半夏妊娠用药需复核", "公开用药注意提示孕妇慎用，请由医师和药师核实适宜性。", [name], "香港卫生署：生半夏和制半夏", PINELLIA)
    for base, medicines in groups.items():
        if base and len(medicines) > 1:
            add("duplicate_herb", "error", "疑似重复饮片", "同一药材或已登记的炮制别名出现多次，请核对是否重复录入；不得自动合并或删药。", [m.name for m in medicines])
    present = set(groups)
    if {"人参", "五灵脂"} <= present:
        add("nineteen_incompatible_pair", "risk", "十九畏：人参与五灵脂同方", "人参与五灵脂同方，命中十九畏配伍禁忌；公开人参条目提示不宜与五灵脂同用。", ["人参", "五灵脂"], "《中国药典》（2025年版）人参条目官方转载及内置十九畏", GINSENG_SOURCE)
    pair_groups = [
        ({"附子", "川乌", "草乌"}, {"半夏", "瓜蒌", "天花粉", "川贝母", "浙贝母", "平贝母", "白蔹", "白及"}, "十八反配伍疑点", ACONITE),
        ({"甘草"}, {"海藻", "京大戟", "甘遂", "芫花"}, "十八反配伍疑点", REFERENCE),
        ({"藜芦"}, {"人参", "党参", "西洋参", "丹参", "沙参", "玄参", "苦参", "细辛", "芍药"}, "十八反配伍疑点", REFERENCE),
    ]
    for left, right, title, url in pair_groups:
        for a in sorted(present & left):
            for b in sorted(present & right):
                add("incompatible_pair", "risk", title, f"「{a}」与「{b}」同方，命中已登记配伍规则。请联系处方医师与药师确认依据及处理，不自动给出替代处方。", [a, b], "乌头类公开用药提示" if url == ACONITE else "本地基础资料：用药禁忌（有限规则）", url)
    adult = prescription.age is not None and prescription.age >= 18 and prescription.pregnancy != "yes" and (prescription.sex == "male" or prescription.pregnancy == "no")
    for base, total in totals.items():
        profile = PROFILES.get(base)
        if profile and adult:
            if total < Decimal(profile["low"]) or total > Decimal(profile["high"]):
                add("profile_dose", "review", "未满足采用参考剂量条件", f"已确认每剂合计 {total.normalize():f} g，采用参考范围为 {profile['low']}～{profile['high']} g，当前剂量超出该范围。", [base], profile["basis"], profile["url"] if base != "五灵脂" else None)
            continue
        entry = entries.get(base, "")
        dose_line = next((line for line in entry.splitlines() if "用法用量" in line), "")
        match = re.search(r"(\d+(?:\.\d+)?)\s*[～~\-—–至]\s*(\d+(?:\.\d+)?)\s*(?:g|克)", dose_line)
        if match and adult and (total < Decimal(match[1]) or total > Decimal(match[2])):
            add("reference_dose", "review", "与本地参考剂量不一致", f"已确认每剂合计 {total.normalize():f} g，本地资料所列范围为 {match[1]}–{match[2]} g。该资料不是完整现行药典或个体化处方标准，需药师结合证候、疗程和原处方复核。", [base], "本地《中药基础知识（详解版）》用法用量", REFERENCE)
    return findings
