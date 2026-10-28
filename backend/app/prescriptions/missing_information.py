from .models import MissingInformation, Prescription


PATIENT_FIELDS = [
    ("missing_age", "age", "患者年龄", "请填写患者实际年龄，单位为岁。"),
    ("missing_sex", "sex", "患者性别", "请根据患者原始记录选择性别，无法确认时向处方方核实。"),
    ("missing_diagnosis", "diagnosis", "诊断 / 证候", "请补充本次就诊的诊断或中医证候。"),
    ("missing_allergies", "allergies", "过敏史", "请补充已知药物过敏史；经确认无过敏史时可填写“无”，未知时请先核实。"),
    ("missing_regimen", "regimen", "用法用量", "请补充原方的每日剂数、服用次数及服法等信息。"),
    ("missing_doses", "doses", "总剂数", "请填写这张处方一共开具几剂。"),
    ("missing_pregnancy", "pregnancy", "妊娠状态", "请确认是否妊娠，或是否已确认非妊娠 / 不适用。"),
]


def build_missing_information(prescription: Prescription, findings):
    """Point to existing editable fields; do not introduce new clinical requirements."""
    codes = {finding["code"] for finding in findings}
    missing = [MissingInformation(field=field, label=label, prompt=prompt)
               for code, field, label, prompt in PATIENT_FIELDS if code in codes]
    for index, medicine in enumerate(prescription.medicines):
        label = f"第{index + 1}味药" + (f"「{medicine.name}」" if medicine.name else "")
        def add(field, title, prompt):
            missing.append(MissingInformation(field=f"medicines.{index}.{field}", label=label + "的" + title, prompt=prompt))
        if not medicine.name and "missing_name" in codes:
            add("name", "药名", "请补充原处方药名及已注明的炮制规格。")
        if not medicine.dose and "missing_dose" in codes:
            add("dose", "剂量", "请填写原处方标注的剂量数字。")
        if not medicine.unit and "missing_dose" in codes:
            add("unit", "单位", "请填写原方单位，例如 g、克或片，不要默认补成克。")
        if medicine.dose_scope == "unknown" and "dose_scope" in codes:
            add("dose_scope", "剂量口径", "请确认该数值是每剂量，还是多剂合计总量。")
    return missing
