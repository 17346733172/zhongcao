import re
from decimal import Decimal

GINSENG_SOURCE = "https://wsj.yueyang.gov.cn/75523/75526/content_2349014.html"
SPECIAL_METHOD_SOURCE = "https://www.wuhe.gov.cn/zfxxgk/public/25641/51091076.html"
PRESCRIPTION_LAW = "https://www.nhc.gov.cn/yzygj/c100068/200602/890d7c8eb1d64405a060922c93c9f900.shtml"
AUDIT_STANDARD = "https://www.nhc.gov.cn/wjw/c100175/201807/1774578ad7ad410491c060f684947639.shtml"
ACONITE_METHOD_SOURCE = "https://wjw.beijing.gov.cn/bmfw_20143/jkzs/jksh/202307/t20230727_3208581.html"
REFERENCE = "/api/reference-document/file"

# Only these verified / explicitly supplied profiles extend the existing local data.
PROFILES = {
    "人参": {"low": "3", "high": "9", "method": "另煎", "method_label": "另煎兑服", "url": GINSENG_SOURCE,
             "basis": "岳阳市卫健委转载《中国药典》（2025年版）人参条目", "range_label": "公开资料所列"},
    "吴茱萸": {"low": "2", "high": "5", "method": None, "url": REFERENCE,
               "basis": "内置基础资料与用户提供的吴茱萸参考口径", "range_label": "采用参考口径"},
    "五灵脂": {"low": "5", "high": "10", "method": "包煎", "method_label": "包煎", "url": SPECIAL_METHOD_SOURCE,
               "basis": "用户提供的五灵脂常用参考量（非已核验药典条目）", "range_label": "本次采用的常用参考口径"},
}


def method_recorded(text, method):
    compact = re.sub(r"\s+", "", text)
    return method in compact and not re.search(r"(?:未|不|无需|无须|勿|免).{0,4}" + re.escape(method), compact)


def aconite_decoction_issue(text, base):
    if not method_recorded(text, "先煎"):
        return "原方未明确先煎，或记录与先煎要求相反，未满足本次煎法审核条件。"
    match = re.search(r"先煎[^0-9+\-]{0,12}([+-]?\d{1,4}(?:\.\d{1,2})?)(?:\s*[～~—–-]\s*([+-]?\d{1,4}(?:\.\d{1,2})?))?\s*(分钟|分|min|小时|h)", text.lower())
    if not match:
        return "先煎具体时长未明确或无法解析，请按原方补充分钟或小时数后重新检查。"
    duration = min(Decimal(match[1]), Decimal(match[2]) if match[2] else Decimal(match[1]))
    if match[3] in {"小时", "h"}:
        duration *= 60
    minimum = 30 if base == "附子" else 60
    if duration < minimum:
        return f"先煎记录至少 {duration.normalize():f} 分钟，低于本次采用的 {minimum} 分钟核查下限，需核实并更正。"
    return None
