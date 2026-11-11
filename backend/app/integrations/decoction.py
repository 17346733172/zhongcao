"""将已核对处方转换并上传至煎药流程仿真平台。"""

import logging
import re
from decimal import Decimal

import httpx
from fastapi import HTTPException

from ..config import Settings
from ..prescriptions.models import SimulationUploadRequest

METHODS = {
    "": "normal", "常规": "normal", "常规煎煮": "normal", "同煎": "normal", "水煎": "normal",
    "先煎": "pre_decoct", "后下": "late_add", "包煎": "bag",
}
METHOD_WITH_TIME = re.compile(r"(先煎|后下|包煎)[（(]?\d+(?:\.\d+)?(?:分钟|分|小时)[）)]?")
UNIT_TO_GRAMS = {"g": Decimal(1), "克": Decimal(1), "mg": Decimal("0.001"), "毫克": Decimal("0.001")}
UPLOAD_TIMEOUT = httpx.Timeout(connect=10, read=15, write=5, pool=5)
UPLOAD_ATTEMPTS = 3
logger = logging.getLogger(__name__)


def build_simulation_payload(request: SimulationUploadRequest) -> dict:
    doses = request.doses
    if doses is None or not 1 <= doses <= 30:
        raise HTTPException(422, "仿真平台要求总剂数为 1–30，请返回核对页补齐或核对总剂数。")

    herbs = []
    names = set()
    for index, item in enumerate(request.medicines, start=1):
        row = f"第 {index} 味药"
        if not item.name or item.name in names:
            raise HTTPException(422, f"{row}的药名为空或重复，请返回核对页检查。")
        names.add(item.name)
        unit = item.unit.lower()
        if unit not in {*UNIT_TO_GRAMS, "片"}:
            raise HTTPException(422, f"{row}的单位「{item.unit or '未填写'}」暂不支持仿真上传，请核对克、毫克或片单位。")
        if not re.fullmatch(r"\d{1,6}(?:\.\d{1,6})?", item.dose) or item.dose_scope == "unknown":
            raise HTTPException(422, f"{row}需确认剂量数字及每剂量或总量口径，才能上传仿真。")
        quantity = Decimal(item.dose)
        if item.dose_scope == "total":
            quantity /= doses
        if quantity <= 0:
            raise HTTPException(422, f"{row}的每剂数量必须大于 0，才能上传仿真。")
        grams = quantity * UNIT_TO_GRAMS[unit] if unit != "片" else None
        if grams is not None and grams > 1000:
            raise HTTPException(422, f"{row}的每剂克数需大于 0 且不超过 1000 g，才能上传仿真。")

        method = re.sub(r"\s+", "", item.method)
        timed = METHOD_WITH_TIME.fullmatch(method)
        method_code = METHODS.get(timed[1] if timed else method)
        if method_code is None:
            raise HTTPException(422, f"{row}的煎法无法映射到仿真平台。仿真平台支持常规、先煎、后下和包煎。")
        herb = {"name": item.name, "method": method_code}
        if unit == "片":
            herb.update(unit="piece", quantity_per_dose=float(quantity))
        else:
            herb["grams_per_dose"] = float(grams)
        herbs.append(herb)

    return {
        "external_no": f"BENCAO-{request.upload_id.hex.upper()}",
        "patient_code": f"SIM-{request.upload_id.hex.upper()}",
        "doses": doses,
        "herbs": herbs,
    }


def upload_to_simulation(settings: Settings, request: SimulationUploadRequest) -> dict:
    payload = build_simulation_payload(request)
    external_no = payload["external_no"]
    headers = {"X-API-Key": settings.decoction_api_key} if settings.decoction_api_key else {}
    url = f"{settings.decoction_base_url.rstrip('/')}/api/v1/prescriptions"
    auth = None
    if settings.decoction_http_username:
        auth = httpx.BasicAuth(settings.decoction_http_username, settings.decoction_http_password)
    for attempt in range(1, UPLOAD_ATTEMPTS + 1):
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=UPLOAD_TIMEOUT, trust_env=False, auth=auth)
            break
        except httpx.RequestError as error:
            logger.warning("Simulation upload transport failure attempt=%d error=%s", attempt, type(error).__name__)
    else:
        raise HTTPException(502, "连接仿真平台超时或中断，自动重试后仍未确认接收结果。请稍后再次点击上传。")
    if response.status_code in {401, 403}:
        raise HTTPException(502, "仿真平台拒绝了连接，请检查本草后端配置的 API Key 和 HTTPS 网关认证。")
    if response.status_code == 422:
        count_note = "处方包含片数，请确认接收端已更新至支持计数单位的版本。" if any(h.get("unit") == "piece" for h in payload["herbs"]) else ""
        raise HTTPException(502 if count_note else 422, "仿真平台未接受处方字段，请核对药材、剂量、剂数和煎法。" + count_note)
    try:
        result = response.json()
    except ValueError:
        result = None
    if isinstance(result, dict):
        if (response.status_code == 201 and result.get("external_no") == external_no
                and result.get("status") == "pending_review"):
            return {"external_no": external_no, "already_uploaded": False}
        error = result.get("error")
        if (response.status_code == 409 and isinstance(error, dict)
                and error.get("code") == "duplicate_prescription"):
            return {"external_no": external_no, "already_uploaded": True}
    raise HTTPException(502, "未能确认仿真平台已接收，请检查平台地址和服务状态后重试。")
