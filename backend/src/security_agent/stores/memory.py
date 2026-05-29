from dataclasses import dataclass, field

from security_agent.schemas import ReviewStatus, RiskLevel, TaskStatus
from security_agent.stores.models import (
    AlarmRecord,
    DeviceRecord,
    MessageRecord,
    ReviewRecord,
    SessionMemory,
    TaskRecord,
    ThreadRecord,
    HandoffRecord,
    new_id,
    utc_now,
)


@dataclass
class InMemoryStores:
    threads: dict[str, ThreadRecord] = field(default_factory=dict)
    messages: list[MessageRecord] = field(default_factory=list)
    tasks: dict[str, TaskRecord] = field(default_factory=dict)
    reviews: dict[str, ReviewRecord] = field(default_factory=dict)
    handoffs: dict[str, HandoffRecord] = field(default_factory=dict)
    devices: dict[str, DeviceRecord] = field(default_factory=dict)
    alarms: dict[str, AlarmRecord] = field(default_factory=dict)
    sessions: dict[str, SessionMemory] = field(default_factory=dict)

    async def upsert_thread(
        self,
        *,
        user_id: str,
        thread_id: str | None = None,
        title: str | None = None,
    ) -> ThreadRecord:
        if thread_id and thread_id in self.threads:
            thread = self.threads[thread_id]
            thread.updated_at = utc_now()
            if title:
                thread.title = title
            return thread
        thread = ThreadRecord(
            thread_id=thread_id or new_id("thread"),
            user_id=user_id,
            title=title,
        )
        self.threads[thread.thread_id] = thread
        return thread

    async def get_thread(self, thread_id: str) -> ThreadRecord | None:
        return self.threads.get(thread_id)

    async def list_threads(self, *, user_id: str | None = None) -> list[ThreadRecord]:
        threads = list(self.threads.values())
        if user_id:
            threads = [thread for thread in threads if thread.user_id == user_id]
        return sorted(threads, key=lambda item: item.updated_at, reverse=True)

    async def add_message(
        self,
        *,
        thread_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> MessageRecord:
        message = MessageRecord(
            thread_id=thread_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self.messages.append(message)
        if thread_id in self.threads:
            self.threads[thread_id].updated_at = utc_now()
        return message

    async def list_messages(self, *, thread_id: str) -> list[MessageRecord]:
        return [message for message in self.messages if message.thread_id == thread_id]

    async def create_task(
        self,
        *,
        thread_id: str,
        title: str,
        description: str | None = None,
    ) -> TaskRecord:
        task = TaskRecord(thread_id=thread_id, title=title, description=description)
        self.tasks[task.task_id] = task
        return task

    async def update_task_status(
        self,
        *,
        task_id: str,
        status: TaskStatus,
    ) -> TaskRecord:
        task = self.tasks[task_id]
        task.status = status
        task.updated_at = utc_now()
        return task

    async def list_tasks(self, *, thread_id: str) -> list[TaskRecord]:
        return [task for task in self.tasks.values() if task.thread_id == thread_id]

    async def create_review(
        self,
        *,
        thread_id: str,
        user_id: str,
        risk_level: str,
        reason: str,
        proposed_action: str,
        checkpoint_ref: str | None = None,
        resume_token_hash: str | None = None,
    ) -> ReviewRecord:
        review = ReviewRecord(
            thread_id=thread_id,
            user_id=user_id,
            risk_level=RiskLevel(risk_level),
            reason=reason,
            proposed_action=proposed_action,
            checkpoint_ref=checkpoint_ref,
            resume_token_hash=resume_token_hash,
        )
        self.reviews[review.review_id] = review
        return review

    async def decide_review(
        self,
        *,
        review_id: str,
        status: ReviewStatus,
        operator_id: str,
    ) -> ReviewRecord:
        if status not in {ReviewStatus.APPROVED, ReviewStatus.REJECTED}:
            raise ValueError("review decision must be approved or rejected")
        review = self.reviews[review_id]
        if review.status != ReviewStatus.PENDING:
            raise ValueError("only pending review can be decided")
        review.status = status
        review.operator_id = operator_id
        review.decided_at = utc_now()
        review.updated_at = utc_now()
        return review

    async def mark_resumed(self, *, review_id: str) -> ReviewRecord:
        review = self.reviews[review_id]
        if review.status not in {ReviewStatus.APPROVED, ReviewStatus.REJECTED}:
            raise ValueError("review must be approved or rejected before resume")
        review.status = ReviewStatus.RESUMED
        review.resumed_at = utc_now()
        review.updated_at = utc_now()
        return review

    async def list_reviews(
        self,
        *,
        status: ReviewStatus | None = None,
    ) -> list[ReviewRecord]:
        reviews = list(self.reviews.values())
        if status:
            reviews = [review for review in reviews if review.status == status]
        return sorted(reviews, key=lambda item: item.created_at, reverse=True)

    async def get_review(self, review_id: str) -> ReviewRecord | None:
        return self.reviews.get(review_id)

    async def finish_review(
        self,
        *,
        review_id: str,
        status: ReviewStatus,
    ) -> ReviewRecord:
        if status not in {ReviewStatus.COMPLETED, ReviewStatus.CANCELLED}:
            raise ValueError("review finish status must be completed or cancelled")
        review = self.reviews[review_id]
        if review.status != ReviewStatus.RESUMED:
            raise ValueError("review must be resumed before finish")
        review.status = status
        review.updated_at = utc_now()
        return review

    async def create_handoff(
        self,
        *,
        thread_id: str,
        from_agent: str,
        to_agent: str,
        task_brief: str,
        allowed_tools: list[str] | None = None,
    ) -> HandoffRecord:
        handoff = HandoffRecord(
            thread_id=thread_id,
            from_agent=from_agent,
            to_agent=to_agent,
            task_brief=task_brief,
            allowed_tools=allowed_tools or [],
        )
        self.handoffs[handoff.handoff_id] = handoff
        return handoff

    async def complete_handoff(
        self,
        *,
        handoff_id: str,
        status: str = "completed",
    ) -> HandoffRecord:
        handoff = self.handoffs[handoff_id]
        handoff.status = status
        handoff.completed_at = utc_now()
        return handoff

    async def list_handoffs(self, *, thread_id: str | None = None) -> list[HandoffRecord]:
        handoffs = list(self.handoffs.values())
        if thread_id:
            handoffs = [handoff for handoff in handoffs if handoff.thread_id == thread_id]
        return sorted(handoffs, key=lambda item: item.created_at, reverse=True)

    async def list_devices(self) -> list[DeviceRecord]:
        return list(self.devices.values())

    async def get_device(self, device_id: str) -> DeviceRecord | None:
        return self.devices.get(device_id)

    async def list_alarms(self) -> list[AlarmRecord]:
        return list(self.alarms.values())

    async def load(self, thread_id: str) -> SessionMemory:
        return self.sessions.get(thread_id) or SessionMemory(thread_id=thread_id)

    async def save(self, memory: SessionMemory) -> None:
        memory.updated_at = utc_now()
        self.sessions[memory.thread_id] = memory

    async def append_fact(self, thread_id: str, fact: str) -> SessionMemory:
        memory = await self.load(thread_id)
        memory.important_facts.append(fact)
        await self.save(memory)
        return memory
