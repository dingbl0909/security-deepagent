from security_agent.adapters.protocols import KnowledgeHit, VisionAnalysis
from security_agent.stores.protocols import AlarmStore, DeviceStore


class LocalKnowledgeRetriever:
    async def search(self, query: str, *, top_k: int = 5) -> list[KnowledgeHit]:
        if not query.strip():
            return []
        hits = [
            KnowledgeHit(
                title="安防设备排障 SOP",
                source="local://knowledge/device-troubleshooting",
                snippet="常见排障顺序：检查供电、网络连通性、设备心跳、平台接入配置和服务日志。",
                score=0.78,
                metadata={"doc_type": "sop"},
            ),
            KnowledgeHit(
                title="告警误报分析 SOP",
                source="local://knowledge/alarm-analysis",
                snippet="误报分析应核对告警时间、设备位置、规则阈值、历史同类告警和现场证据。",
                score=0.72,
                metadata={"doc_type": "sop"},
            ),
        ]
        return hits[:top_k]


class StoreBackedDeviceGateway:
    def __init__(self, device_store: DeviceStore) -> None:
        self._device_store = device_store

    async def query(self, device_id_or_name: str) -> list[dict]:
        devices = await self._device_store.list_devices()
        if not devices:
            return []
        keyword = device_id_or_name.lower()
        return [
            device.model_dump(mode="json")
            for device in devices
            if keyword in device.device_id.lower() or keyword in device.name.lower()
        ]


class StoreBackedAlarmGateway:
    def __init__(self, alarm_store: AlarmStore) -> None:
        self._alarm_store = alarm_store

    async def query(self, query: str) -> list[dict]:
        alarms = await self._alarm_store.list_alarms()
        if not query.strip():
            return [alarm.model_dump(mode="json") for alarm in alarms]
        keyword = query.lower()
        return [
            alarm.model_dump(mode="json")
            for alarm in alarms
            if keyword in alarm.alarm_type.lower()
            or keyword in alarm.severity.lower()
            or keyword in alarm.status.lower()
            or (alarm.description and keyword in alarm.description.lower())
        ]


class LocalVisionGateway:
    async def analyze(
        self,
        *,
        image_path: str | None = None,
        image_url: str | None = None,
        image_base64: str | None = None,
        prompt: str,
    ) -> VisionAnalysis:
        source = image_path or image_url or ("base64" if image_base64 else "unknown")
        return VisionAnalysis(
            scene_summary=f"已接收现场图片输入：{source}",
            objects=["现场图片", "待识别目标"],
            risk_level="medium",
            recommendation="请结合现场 SOP 复核识别结果；当前为本地占位分析。",
        )

