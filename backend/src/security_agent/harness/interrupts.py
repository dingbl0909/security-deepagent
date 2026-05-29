from dataclasses import dataclass
from hashlib import sha256
from secrets import token_urlsafe

from security_agent.harness.risk import RiskGate
from security_agent.schemas import ReviewStatus, RiskLevel, TraceEvent
from security_agent.stores.models import ReviewRecord
from security_agent.stores.protocols import MessageStore, ReviewStore, ShortTermMemoryStore


class ReviewNotFoundError(ValueError):
    pass


class ReviewStateError(ValueError):
    pass


@dataclass
class ResumeResult:
    review: ReviewRecord
    answer: str
    trace: list[TraceEvent]


class InterruptManager:
    def __init__(
        self,
        review_store: ReviewStore,
        *,
        message_store: MessageStore | None = None,
        memory_store: ShortTermMemoryStore | None = None,
        risk_gate: RiskGate | None = None,
    ) -> None:
        self._review_store = review_store
        self._message_store = message_store
        self._memory_store = memory_store
        self._risk_gate = risk_gate or RiskGate()

    async def pause_for_review(
        self,
        *,
        thread_id: str,
        user_id: str,
        proposed_action: str,
        reason: str | None = None,
        checkpoint_ref: str | None = None,
    ) -> ReviewRecord:
        risk = self._risk_gate.evaluate_text(proposed_action)
        review = await self._review_store.create_review(
            thread_id=thread_id,
            user_id=user_id,
            risk_level=RiskLevel.HIGH.value,
            reason=reason or risk.reason,
            proposed_action=proposed_action,
            checkpoint_ref=checkpoint_ref or f"checkpoint:{thread_id}",
            resume_token_hash=_hash_resume_token(token_urlsafe(24)),
        )
        _print_review_required(review)
        if self._memory_store:
            memory = await self._memory_store.load(thread_id)
            memory.active_review_id = review.review_id
            await self._memory_store.save(memory)
        return review

    async def resume_after_review(self, review_id: str) -> ResumeResult:
        review = await self._review_store.get_review(review_id)
        if review is None:
            raise ReviewNotFoundError("review not found")
        if review.status not in {ReviewStatus.APPROVED, ReviewStatus.REJECTED}:
            raise ReviewStateError(
                f"review must be approved or rejected before resume, got {review.status.value}"
            )

        decision = review.status
        resumed = await self._review_store.mark_resumed(review_id=review_id)
        final_status = (
            ReviewStatus.COMPLETED
            if decision == ReviewStatus.APPROVED
            else ReviewStatus.CANCELLED
        )
        finished = await self._review_store.finish_review(
            review_id=review_id,
            status=final_status,
        )
        answer = _resume_answer(decision, resumed)
        trace = [
            TraceEvent(
                type="review_resumed",
                summary="Review decision consumed and flow resumed from checkpoint reference.",
                agent="harness",
                name=review_id,
                status=decision.value,
                metadata={
                    "thread_id": resumed.thread_id,
                    "checkpoint_ref": resumed.checkpoint_ref,
                    "final_status": final_status.value,
                },
            )
        ]
        if self._message_store:
            await self._message_store.add_message(
                thread_id=finished.thread_id,
                role="assistant",
                content=answer,
                metadata={
                    "review_id": finished.review_id,
                    "review_status": finished.status.value,
                    "resumed": True,
                },
            )
        if self._memory_store:
            memory = await self._memory_store.load(finished.thread_id)
            memory.active_review_id = None
            await self._memory_store.save(memory)
        return ResumeResult(review=finished, answer=answer, trace=trace)


def _hash_resume_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def _resume_answer(decision: ReviewStatus, review: ReviewRecord) -> str:
    if decision == ReviewStatus.APPROVED:
        return (
            "人工审批已通过，流程已从 checkpoint 恢复。"
            f"原高风险动作：{review.proposed_action}"
        )
    return (
        "人工审批已拒绝，流程已恢复并终止原高风险动作。"
        "建议改为人工现场确认、只读排查或提交变更单后再执行。"
    )


def _print_review_required(review: ReviewRecord) -> None:
    print(
        "\n".join(
            [
                "[REVIEW_REQUIRED]",
                f"review_id={review.review_id}",
                f"thread_id={review.thread_id}",
                f"risk_level={review.risk_level.value}",
                f"reason={review.reason}",
                f"proposed_action={review.proposed_action}",
                f"resume_api=POST /reviews/{review.review_id}/resume",
            ]
        ),
        flush=True,
    )
