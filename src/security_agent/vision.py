from __future__ import annotations

import base64
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from security_agent.config import Settings, get_settings


DATA_URL_RE = re.compile(r"^data:(?P<mime>[^;]+);base64,(?P<data>.+)$", re.DOTALL)


@dataclass(frozen=True)
class VisionInput:
    mime_type: str
    data_url: str
    source: str


@dataclass(frozen=True)
class VisionResult:
    answer: str
    model: str
    source: str
    raw: dict[str, Any]


def build_vision_client(settings: Settings | None = None):
    settings = settings or get_settings()
    if not settings.vision_enabled:
        return None
    if not settings.vision_api_key:
        raise RuntimeError("SECURITY_AGENT_VISION_API_KEY is required when vision is enabled")
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("openai package is required for vision analysis") from exc
    return OpenAI(api_key=settings.vision_api_key, base_url=settings.vision_base_url)


def resolve_vision_input(
    *,
    image_path: str | None = None,
    image_url: str | None = None,
    image_base64: str | None = None,
    settings: Settings | None = None,
) -> VisionInput:
    settings = settings or get_settings()

    if image_url:
        if image_url.startswith("data:"):
            match = DATA_URL_RE.match(image_url)
            if not match:
                raise ValueError("Invalid data URL for image.")
            return VisionInput(
                mime_type=match.group("mime"),
                data_url=image_url,
                source="inline_data_url",
            )
        return VisionInput(mime_type="image/url", data_url=image_url, source=image_url)

    if image_base64:
        mime_type = "image/jpeg"
        payload = image_base64.strip()
        if payload.startswith("data:"):
            match = DATA_URL_RE.match(payload)
            if not match:
                raise ValueError("Invalid base64 image payload.")
            return VisionInput(
                mime_type=match.group("mime"),
                data_url=payload,
                source="inline_base64",
            )
        encoded = payload.split(",", 1)[-1]
        data_url = f"data:{mime_type};base64,{encoded}"
        return VisionInput(mime_type=mime_type, data_url=data_url, source="inline_base64")

    if image_path:
        path = Path(image_path)
        if not path.is_absolute():
            path = settings.workspace_dir / path
        path = path.resolve()
        workspace_root = settings.workspace_dir.resolve()
        if workspace_root not in path.parents and path != workspace_root:
            raise ValueError("Image path must stay inside the workspace directory.")
        if not path.is_file():
            raise ValueError(f"Image file not found: {path}")
        mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return VisionInput(
            mime_type=mime_type,
            data_url=f"data:{mime_type};base64,{encoded}",
            source=str(path.relative_to(workspace_root)) if path.is_relative_to(workspace_root) else str(path),
        )

    raise ValueError("An image_path, image_url, or image_base64 value is required for vision analysis.")


def analyze_security_image(
    question: str,
    *,
    image_path: str | None = None,
    image_url: str | None = None,
    image_base64: str | None = None,
    settings: Settings | None = None,
) -> VisionResult:
    settings = settings or get_settings()
    if not settings.vision_enabled:
        raise RuntimeError("Vision analysis is disabled. Set SECURITY_AGENT_VISION_ENABLED=true.")

    client = build_vision_client(settings)
    if client is None:
        raise RuntimeError("Vision client is not configured.")

    vision_input = resolve_vision_input(
        image_path=image_path,
        image_url=image_url,
        image_base64=image_base64,
        settings=settings,
    )
    prompt = question.strip() or "请识别图片中的安防相关物品，并给出研判结论。"
    response = client.chat.completions.create(
        model=settings.vision_model,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是安防物品研判专家。请识别图片中的关键对象、场景、风险点和处置建议。"
                    "输出结构：场景概述、识别到的物品/对象、风险判断、建议动作。"
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": vision_input.data_url}},
                ],
            },
        ],
    )
    answer = response.choices[0].message.content or "未返回识别结果。"
    return VisionResult(
        answer=str(answer).strip(),
        model=settings.vision_model,
        source=vision_input.source,
        raw=response.model_dump(),
    )
