from __future__ import annotations

from security_agent.vision import VisionResult, analyze_security_image


OBJECT_ANALYST_PROMPT = """你是安防物品研判子 Agent。
你的职责是调用多模态模型完成图片识别，并输出可执行的安防研判结论。
重点关注：人员、车辆、包裹、门禁设施、监控盲区、异常物品、危险源和现场风险。"""


def run_object_analyst(
    question: str,
    *,
    image_path: str | None = None,
    image_url: str | None = None,
    image_base64: str | None = None,
) -> VisionResult:
    return analyze_security_image(
        question,
        image_path=image_path,
        image_url=image_url,
        image_base64=image_base64,
    )
