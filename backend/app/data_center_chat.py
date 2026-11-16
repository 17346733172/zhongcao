"""Read-only operational questions answered from the data center, without an LLM."""

import asyncio
from dataclasses import dataclass
from datetime import timedelta, timezone
import re
import time
import unicodedata

from .data_center_utilization import RATE_WORDS, format_utilization, requested_period

WAIT_SECONDS = 8
STATUS_WORDS = {
    "fault": r"故障|坏了|坏的|损坏|异常",
    "offline": r"停用|离线",
    "idle": r"空闲|闲置|闲着|可用|没在用",
    "busy": r"在用|使用中|工作|运行|忙碌|占用|正在用",
}
STATUS_LABELS = {"busy": "使用中", "idle": "空闲", "fault": "故障", "offline": "已停用"}
KNOWLEDGE = re.compile(r"材质|铁锅|砂锅|铝锅|不锈钢|煎药用什么|怎么煎|如何煎|功效|药效|禁忌|需要几个|需要几台|需要多少|应该用|怎么保养|如何保养|原理|用途|选购|使用方法")
OPERATION = re.compile(r"现在|当前|目前|我|平台|数据中心|工厂|车间|有几|多少|几台|几口|几个|数量|总数|状态|在用|工作|运行|空闲|故障|异常|停用|哪些|哪几|编号|锅号")
FOLLOW_UP = re.compile(r"^(?:那|那么|还有|请问|请|告诉我|查看|看看|查询|查|一下|它|这台|现在|当前|目前|一共|总共|具体|到底|还|的|呢|啊|吗|有|是|哪些|哪几台|哪几个|哪台|几台|几个|多少|数量|总数|锅号|锅编号|设备编号|编号|工作|运行|在用|使用中|空闲|闲着|闲置|可用|故障|异常|坏|停用|离线|都|台|个|口|全部|所有|总计|原因|未解除|已解除|历史|记录)+$")
DEVICE_ID = re.compile(r"(?<![a-z0-9_-])pot-\d{1,6}(?![a-z0-9_-])")
LABELED_ID = re.compile(r"(?:设备编号|锅号|锅编号)([a-z][a-z0-9_-]{0,127})(?![a-z0-9_-])")
COMMAND = re.compile(r"(?:帮我|给我|直接|立即|请)?(?:修复|启动|暂停|停掉|停止|重置|注入|修改|删除|启用)")


@dataclass(frozen=True)
class Intent:
    topic: str
    kind: str = ""
    status: str = ""
    details: bool = False
    device_id: str = ""
    period: str = ""


def normalize(question):
    return re.sub(r"[\s？?！!。，,、：:；;]", "", unicodedata.normalize("NFKC", question).lower())


def detect_intent(question, history=()):
    text = normalize(question)
    if KNOWLEDGE.search(text):
        return None
    device = re.search(r"煎药锅|药锅|锅|设备|工位", text)
    details = bool(re.search(r"哪些|哪几|哪台|哪口|明细|列表|编号|锅号|原因|具体|为什么", text))
    status_text = RATE_WORDS.sub("", text)
    status = next((key for key, words in STATUS_WORDS.items() if re.search(words, status_text)), "")
    direct_id = DEVICE_ID.search(text)
    labeled_id = LABELED_ID.search(text)
    device_id = direct_id.group() if direct_id else labeled_id.group(1) if labeled_id else ""
    period = requested_period(text)
    rate = RATE_WORDS.search(text)
    previous = detect_intent(history[-1].question) if history and history[-1].channel == "data_center" else None
    metric_followup = bool(re.fullmatch(r"(?:那|那么|请问|它|这台|的|呢|啊|吗|多少|是多少|怎么样|今天|今日|昨天|昨日|本周|本月|上周|上月|一周|一个月|近7天|近30天|利用率|使用率|稼动率|开工率|占用率)+", text))
    metric_context = previous and previous.topic in {"devices", "utilization", "occupancy"} and metric_followup
    if (rate and (device or device_id or metric_context)) or (metric_context and previous.topic in {"utilization", "occupancy"} and period):
        kind = "pot" if "锅" in text or device_id.startswith("pot-") else "" if device else previous.kind if previous else ""
        ident = device_id or (previous.device_id if metric_context else "")
        selected = "" if device_id else status or (previous.status if metric_context else "")
        topic = "occupancy" if "占用率" in text else "utilization" if rate else previous.topic
        return Intent("read_only" if COMMAND.search(text) else topic, kind, selected, details, ident,
                      period or (previous.period if metric_context and previous.topic in {"utilization", "occupancy"} else ""))
    if device_id:
        kind = "pot" if device_id.startswith("pot-") else ""
        return Intent("read_only" if COMMAND.search(text) else "devices", kind, details=True, device_id=device_id)
    if history and history[-1].channel == "data_center" and FOLLOW_UP.fullmatch(text):
        if previous and previous.topic in {"devices", "utilization", "occupancy"}:
            selected = status or ("" if re.search(r"一共|总共|全部|所有|总数|总计", text) else previous.status)
            kind = "pot" if "锅" in text else previous.kind
            return Intent("devices", kind, selected, details,
                          previous.device_id if not status and not re.search(r"全部|所有|总数|总计", text) else "")
        if previous and previous.topic == "alarms" and not re.search(r"锅号|锅编号|设备编号", text):
            selected = "" if re.search(r"全部|历史", text) else "resolved" if "已解除" in text else "active" if "未解除" in text else previous.status
            return Intent("alarms", status=selected, details=True)
    if device and OPERATION.search(text):
        kind = "pot" if "锅" in text else ""
        if COMMAND.search(text):
            return Intent("read_only", kind, status)
        return Intent("devices", kind, status, details)
    if re.search(r"报警|异常记录|故障记录", text) and OPERATION.search(text + "状态"):
        alarm_status = "" if re.search(r"全部|历史|所有", text) else "resolved" if "已解除" in text else "active"
        return Intent("alarms", status=alarm_status, details=True)
    if ("数据中心" in text and re.search(r"概览|统计|情况|数据", text)
            or re.search(r"(?:现在|当前|目前|平台|数据中心|工厂).*(?:处方|批次|配发).*(?:多少|几张|数量|总数|情况|状态)", text)):
        return Intent("summary")
    return None


def target(intent):
    if intent.topic == "summary":
        return {"tab": "overview"}
    result = {"tab": "devices", "kind": intent.kind, "status": intent.status if intent.topic != "alarms" else ""}
    if intent.device_id:
        result["deviceId"] = intent.device_id
    if intent.topic == "alarms":
        result.update(alarmStatus=intent.status, section="alarms")
    return result


def canonical_question(intent):
    if intent.topic in {"utilization", "occupancy"}:
        entity = f"设备编号{intent.device_id}" if intent.device_id else "煎药锅" if intent.kind == "pot" else "设备"
        return f"数据中心：{intent.period or '当前'}{STATUS_LABELS.get(intent.status, '')}{entity}的{'占用率' if intent.topic == 'occupancy' else '利用率'}"
    if intent.device_id:
        return f"数据中心：设备编号{intent.device_id}的当前状态与编号"
    if intent.topic == "alarms":
        label = {"active": "未解除", "resolved": "已解除", "": "全部"}[intent.status]
        return f"数据中心：{label}报警有哪些？"
    if intent.topic != "devices":
        return "数据中心当前运行概况"
    entity = "煎药锅" if intent.kind == "pot" else "设备"
    state = STATUS_LABELS.get(intent.status, "")
    return f"数据中心：当前{state}的{entity}{'有哪些' if intent.details else '有多少台'}？"


def format_answer(intent, state):
    answer = {"mode": "data_center", "title": "数据中心", "introduction": "来源：煎药流程仿真数据中心。",
              "sections": [], "sources": [], "dataCenter": target(intent), "resolvedQuestion": canonical_question(intent)}
    if intent.topic == "read_only":
        answer.update(title="这里支持查询设备状态", introduction="聊天只能读取数据中心，不能修复、启停或修改设备。请在仿真平台中由工作人员操作。")
        return answer
    if state.data is None:
        answer.update(title="暂时没有可用的平台数据", introduction="数据中心尚未取得有效数据，当前无法确认设备数量或运行状态。后台正在尝试读取，请稍后重试或打开数据中心。")
        if intent.topic in {"utilization", "occupancy"}:
            return format_utilization(intent, state, answer)
        return answer
    when = state.fetched_at.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    answer["introduction"] = f"来源：煎药流程仿真数据中心 · 数据读取时间：{when}（北京时间）。"
    if state.stale or state.error:
        answer["introduction"] += " 当前更新未完成或失败，以下是上次成功读取的数据，不能确认实时状态。"
    if intent.topic == "devices" and intent.kind == "pot" and intent.details:
        answer["introduction"] += " 锅号就是煎药锅的设备编号，以下使用平台原始编号。"
    data = state.data
    if intent.topic in {"utilization", "occupancy"}:
        return format_utilization(intent, state, answer)
    if intent.topic == "devices":
        devices = [d for d in data.devices if not intent.kind or d.kind == intent.kind]
        if intent.device_id:
            found = next((d for d in devices if d.id.casefold() == intent.device_id), None)
            if found is None:
                answer["title"] = f"{'上次记录中' if state.stale or state.error else '当前记录中'}未找到设备 {intent.device_id}"
                answer["sections"] = [{"title": "查询结果", "content": "请核对设备编号（锅号），或打开数据中心查看已登记的设备。"}]
                return answer
            answer["title"] = f"{'上次记录中' if state.stale or state.error else '当前'}设备 {found.id}：{STATUS_LABELS.get(found.status, found.status)}"
            reasons = [a.message for a in data.alarms if a.device_id == found.id and a.status == "active"]
            content = f"设备编号{'（锅号）' if found.kind == 'pot' else ''}：{found.id}\n设备名称：{found.name}\n设备类型：{found.kind_name}\n状态：{STATUS_LABELS.get(found.status, found.status)}\n关联批次：{found.batch_id or '无'}"
            if reasons:
                content += "\n未解除报警：" + "；".join(reasons)
            elif found.status == "fault":
                content += "\n平台未提供具体故障原因。"
            answer["sections"] = [{"title": "设备详情", "content": content}]
            return answer
        selected = [d for d in devices if not intent.status or d.status == intent.status]
        entity = "煎药锅" if intent.kind == "pot" else "设备"
        label = STATUS_LABELS.get(intent.status, "")
        answer["title"] = f"{'上次记录中' if state.stale or state.error else '当前'}{label}的{entity}有 {len(selected)} 台"
        counts = "\n".join(f"{name}：{sum(d.status == code for d in devices)} 台" for code, name in STATUS_LABELS.items())
        answer["sections"].append({"title": "设备概况", "content": f"{entity}总数：{len(devices)} 台\n{counts}\n使用中按平台设备占用状态统计。"})
        if intent.details or intent.status == "fault":
            lines = []
            for d in selected[:20]:
                reasons = [a.message for a in data.alarms if a.device_id == d.id and a.status == "active"]
                line = f"{d.id}（{d.name}）：{STATUS_LABELS.get(d.status, d.status)}"
                if d.status == "fault":
                    line += "；" + ("；".join(reasons) if reasons else "平台未提供具体故障原因")
                lines.append(line)
            if len(selected) > 20:
                lines.append("仅列出前 20 台，可打开数据中心查看完整列表。")
            answer["sections"].append({"title": "设备明细", "content": "\n".join(lines) if lines else "没有符合条件的设备。"})
    elif intent.topic == "alarms":
        alarms = [a for a in data.alarms if not intent.status or a.status == intent.status]
        label = {"active": "未解除", "resolved": "已解除", "": "全部"}[intent.status]
        answer["title"] = f"{label}报警共 {len(alarms)} 条"
        lines = [f"{a.device_id}：{a.message}（{'未解除' if a.status == 'active' else '已解除'}）" for a in alarms[:20]]
        if len(alarms) > 20:
            lines.append("仅列出前 20 条，可在数据中心查看全部记录。")
        answer["sections"] = [{"title": "报警记录", "content": "\n".join(lines) if lines else f"当前记录中没有{label}报警。"}]
    else:
        s = data.summary
        answer["title"] = "仿真平台运行概况"
        answer["sections"] = [{"title": "统计", "content": f"处方总数：{s.total_prescriptions} 张\n批次：排队 {s.batch_counts.queued}、运行 {s.batch_counts.running}、暂停 {s.batch_counts.paused}、完成 {s.batch_counts.completed}、取消 {s.batch_counts.cancelled}\n已配发：{s.dispatched_bags} 袋\n设备：{len(data.devices)} 台\n活跃报警：{s.active_alarms} 条"}]
    return answer


async def answer_from_data_center(intent, reader):
    if intent.topic == "read_only":
        return format_answer(intent, reader.state())
    await reader.start()
    state = reader.state()
    if state.data is None or state.stale or state.error:
        reader.request_refresh()
        deadline = time.monotonic() + WAIT_SECONDS
        while reader.refreshing and time.monotonic() < deadline:
            await asyncio.sleep(.1)
        state = reader.state()
    return format_answer(intent, state)
