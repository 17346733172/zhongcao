"""Explain the simulator's cumulative metric without inventing calendar history."""

import math
import re

RATE_WORDS = re.compile(r"利用率|使用率|稼动率|开工率|占用率")
PERIOD_WORDS = (
    ("今天", r"今天|今日|当天|本日"), ("昨天", r"昨天|昨日"),
    ("本周", r"本周|这周"), ("上周", r"上周"),
    ("近7天", r"一周|近7天|最近7天|过去7天"),
    ("本月", r"本月|这个月"), ("上个月", r"上个月|上月"),
    ("近30天", r"一个月|近30天|最近30天|过去30天"),
)


def requested_period(text):
    for label, pattern in PERIOD_WORDS:
        if re.search(pattern, text):
            return label
    if re.search(r"近\d+天|最近\d+天|过去\d+天|\d{4}[-年/]\d|\d{1,2}月\d{1,2}日|时间段|自定义|历史", text):
        return "指定时间段"
    return ""


def format_utilization(intent, state, answer):
    entity = "煎药锅" if intent.kind == "pot" else "设备"
    metric = "占用率" if intent.topic == "occupancy" else "利用率"
    label = f"{intent.period}的{entity}{metric}"
    if intent.period:
        answer["title"] = f"暂无法准确统计{label}"
        answer["sections"].append({"title": "时间范围说明", "content":
            f"数据中心当前提供设备加入平台后的累计利用率和读取时的设备状态，缺少{intent.period}完整的起止工作时长及状态记录，无法准确计算{label}。下方仅展示标明口径的参考数据。"})
    if state.data is None:
        if not intent.period:
            answer["title"] = "暂时没有可用的设备数据"
        answer["sections"].append({"title": "数据状态", "content": "尚未取得有效设备快照，当前也无法提供累计利用率或占用率参考。"})
        return answer
    devices = [d for d in state.data.devices if (not intent.kind or d.kind == intent.kind)
               and (not intent.device_id or d.id.casefold() == intent.device_id)
               and (not intent.status or d.status == intent.status)]
    if not devices:
        answer["title"] = f"{'上次记录中' if state.stale or state.error else '当前记录中'}未找到设备 {intent.device_id}" if intent.device_id else "当前没有符合条件的设备"
        answer["sections"].append({"title": "查询结果", "content": "没有可统计的设备样本，不能计算百分比。请核对设备编号或筛选条件。"})
        return answer
    if any(not math.isfinite(d.utilization_percent) or not 0 <= d.utilization_percent <= 100 for d in devices):
        answer["title"] = "设备利用率数据格式异常"
        answer["sections"].append({"title": "数据状态", "content": "平台返回了无效的累计利用率，暂时无法给出可靠的利用率参考。"})
        return answer
    average = sum(d.utilization_percent for d in devices) / len(devices)
    busy = sum(d.status == "busy" for d in devices)
    occupancy = busy / len(devices) * 100
    old = "上次读取" if state.stale or state.error else "读取时"
    sample = f"设备编号（锅号）：{devices[0].id}" if intent.device_id and intent.kind == "pot" else f"设备编号：{devices[0].id}" if intent.device_id else f"所选{entity}：{len(devices)} 台"
    if intent.status:
        status_name = {"busy": "使用中", "idle": "空闲", "fault": "故障", "offline": "已停用"}.get(intent.status, intent.status)
        sample += f"（仅包含{status_name}设备）"
    content = (f"{sample}\n累计利用率{'（所选设备算术平均）' if len(devices) > 1 else ''}：{average:.2f}%\n"
               f"{old}占用率：{occupancy:.2f}%（使用中 {busy} / {len(devices)} 台）\n"
               "累计利用率按有效工作时长 ÷ 设备加入后的仿真累计时长计算；占用率按读取时使用中台数 ÷ 所选设备总数计算。")
    if not intent.period:
        answer["title"] = (f"{'上次读取的' if state.stale or state.error else ''}{entity}{'占用率' if intent.topic == 'occupancy' else '累计利用率（平均）' if len(devices) > 1 else '累计利用率'}为 "
                           f"{occupancy if intent.topic == 'occupancy' else average:.2f}%")
    answer["sections"].append({"title": "参考数据（累计 / 读取时）" if intent.period else "统计口径与结果", "content": content})
    if intent.details and len(devices) > 1:
        lines = [f"{d.id}：累计利用率 {d.utilization_percent:.2f}%" for d in devices[:20]]
        if len(devices) > 20:
            lines.append("仅列出前20台，可打开数据中心查看全部设备。")
        answer["sections"].append({"title": "设备累计利用率明细", "content": "\n".join(lines)})
    return answer
