from pydantic import BaseModel, Field

from security_agent.schemas import RiskLevel


HIGH_RISK_KEYWORDS = [
    "重启",
    "删除",
    "修改配置",
    "升级",
    "下发",
    "下发规则",
    "关闭告警",
    "执行命令",
]


class RiskDecision(BaseModel):
    risk_level: RiskLevel
    requires_review: bool
    reason: str
    matched_keywords: list[str] = Field(default_factory=list)


class RiskGate:
    def __init__(self, high_risk_keywords: list[str] | None = None) -> None:
        self._high_risk_keywords = high_risk_keywords or HIGH_RISK_KEYWORDS

    def evaluate_text(self, text: str) -> RiskDecision:
        matched = [keyword for keyword in self._high_risk_keywords if keyword in text]
        if matched:
            return RiskDecision(
                risk_level=RiskLevel.HIGH,
                requires_review=True,
                reason=f"命中高风险动作关键词：{', '.join(matched)}",
                matched_keywords=matched,
            )
        return RiskDecision(
            risk_level=RiskLevel.LOW,
            requires_review=False,
            reason="未命中高风险规则。",
        )

    def requires_review(self, text: str) -> bool:
        return self.evaluate_text(text).requires_review
