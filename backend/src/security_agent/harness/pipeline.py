from security_agent.harness.models import PreparedRequest
from security_agent.schemas import ChatRequest, TraceEvent
from security_agent.stores.protocols import MessageStore, ThreadStore


class RequestPipeline:
    def __init__(self, thread_store: ThreadStore, message_store: MessageStore) -> None:
        self._thread_store = thread_store
        self._message_store = message_store

    async def pre_process(self, request: ChatRequest) -> PreparedRequest:
        thread = await self._thread_store.upsert_thread(
            user_id=request.user_id,
            thread_id=request.thread_id,
            title=request.message[:80],
        )
        user_message = await self._message_store.add_message(
            thread_id=thread.thread_id,
            role="user",
            content=request.message,
            metadata={
                "has_image": _has_image(request),
                "image_path": request.image_path,
                "image_url": request.image_url,
                "image_base64": request.image_base64,
            },
        )
        return PreparedRequest(
            request=request,
            thread=thread,
            user_message=user_message,
            trace=[
                TraceEvent(
                    type="chat_received",
                    summary="User message saved and thread prepared.",
                    agent="harness",
                    metadata={
                        "thread_id": thread.thread_id,
                        "message_id": user_message.message_id,
                        "has_image": _has_image(request),
                    },
                )
            ],
        )


def _has_image(request: ChatRequest) -> bool:
    return bool(request.image_path or request.image_url or request.image_base64)
