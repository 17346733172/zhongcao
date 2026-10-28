from .models import AuditConclusion


def build_conclusion(findings):
    codes = {item["code"] for item in findings}
    blocking = [item for item in findings if item.get("blocking", True)]
    levels = {item["level"] for item in blocking}
    reasons = []
    priority = {"incompatible_pair": 0, "nineteen_incompatible_pair": 0, "profile_dose": 1, "reference_dose": 1, "invalid_dose": 1, "required_method": 2, "aconite_method": 2}
    for finding in sorted(blocking, key=lambda finding: priority.get(finding["code"], 3)):
        if finding["level"] == "missing":
            continue
        prefix = "" if finding["code"] in {"incompatible_pair", "nineteen_incompatible_pair"} else "、".join(finding["medicines"])
        reason = (prefix + "：" if prefix else "") + finding["detail"].split("。", 1)[0] + "。"
        if reason not in reasons:
            reasons.append(reason)
    if "nineteen_incompatible_pair" in codes:
        categories = "“十八反”及“十九畏”" if "incompatible_pair" in codes else "“十九畏”"
        status, result, detail = (
            "not_passed", "不通过。",
            f"处方存在{categories}配伍禁忌，其中人参与五灵脂同方；系统判定本次审核不通过，建议暂缓调配并联系处方医师修改。",
        )
    elif "incompatible_pair" in codes:
        status, result, detail = (
            "not_passed", "不通过。",
            "处方存在“十八反”配伍禁忌，建议暂缓调配，联系处方医师确认或修改。",
        )
    elif "error" in levels:
        status, result, detail = (
            "not_passed", "不通过。",
            "处方数据存在异常，建议暂缓调配，核对并更正药名、剂量或相关信息后，提交药师复核。",
        )
    elif "missing" in levels:
        status, result, detail = (
            "needs_information", "待补充信息。",
            "处方关键信息不完整，暂无法完成审核；请补齐下列信息后重新检查，并提交药师复核。",
        )
    elif blocking:
        status, result, detail = (
            "not_passed", "不通过。",
            "系统已检出未满足本次审核条件的用药或数据问题，依据如下；请更正或补全相应处方记录后重新检查。",
        )
    else:
        status, result, detail = (
            "passed", "通过。",
            "基于本次已确认数据，在系统已覆盖的检查项目内未检出配伍禁忌、数据异常或其他阻断问题，本次系统辅助审核通过。",
        )
        reasons = ["患者必需信息已补齐，药名、剂量数字、单位及口径未发现已覆盖规则异常。", "本次已登记的配伍与特殊煎法检查未发现阻断项。"]
    return AuditConclusion(status=status, result=result, detail=detail,
                           finding_codes=sorted(codes), decision_reasons=reasons).model_dump()
