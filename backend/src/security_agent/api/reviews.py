from fastapi import APIRouter, HTTPException, status

from security_agent.harness.interrupts import (
    InterruptManager,
    ReviewNotFoundError,
    ReviewStateError,
)
from security_agent.schemas import ReviewRequestItem, ReviewResumeResponse, ReviewStatus
from security_agent.stores.factory import get_in_memory_stores

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewRequestItem])
async def list_reviews(status_filter: ReviewStatus | None = None) -> list[ReviewRequestItem]:
    store = get_in_memory_stores()
    reviews = await store.list_reviews(status=status_filter)
    return [
        ReviewRequestItem(
            review_id=review.review_id,
            risk_level=review.risk_level,
            reason=review.reason,
            proposed_action=review.proposed_action,
            status=review.status,
            resume_required=True,
        )
        for review in reviews
    ]


@router.post("/{review_id}/approve", response_model=ReviewRequestItem)
async def approve_review(review_id: str) -> ReviewRequestItem:
    store = get_in_memory_stores()
    try:
        review = await store.decide_review(
            review_id=review_id,
            status=ReviewStatus.APPROVED,
            operator_id="api",
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="review not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _to_review_item(review)


@router.post("/{review_id}/reject", response_model=ReviewRequestItem)
async def reject_review(review_id: str) -> ReviewRequestItem:
    store = get_in_memory_stores()
    try:
        review = await store.decide_review(
            review_id=review_id,
            status=ReviewStatus.REJECTED,
            operator_id="api",
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="review not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _to_review_item(review)


@router.post("/{review_id}/resume", response_model=ReviewResumeResponse)
async def resume_review(review_id: str) -> ReviewResumeResponse:
    store = get_in_memory_stores()
    manager = InterruptManager(
        store,
        message_store=store,
        memory_store=store,
    )
    try:
        result = await manager.resume_after_review(review_id)
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="review not found") from exc
    except ReviewStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ReviewResumeResponse(
        review=_to_review_item(result.review),
        thread_id=result.review.thread_id,
        answer=result.answer,
        trace=result.trace,
    )


def _to_review_item(review) -> ReviewRequestItem:
    return ReviewRequestItem(
        review_id=review.review_id,
        risk_level=review.risk_level,
        reason=review.reason,
        proposed_action=review.proposed_action,
        status=review.status,
        resume_required=True,
    )
