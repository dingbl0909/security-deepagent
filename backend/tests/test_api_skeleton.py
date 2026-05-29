import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from security_agent.app import create_app
from security_agent.harness.factory import get_security_agent_service
from security_agent.stores.factory import get_in_memory_stores


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    get_security_agent_service.cache_clear()
    get_in_memory_stores.cache_clear()
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ready_non_strict_allows_missing_dependencies(client: AsyncClient) -> None:
    response = await client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["strict"] is False
    assert body["dependencies"]


@pytest.mark.asyncio
async def test_chat_stub(client: AsyncClient) -> None:
    response = await client.post(
        "/chat",
        json={"user_id": "ops_001", "message": "北门摄像头离线了"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "agent"
    assert body["target_agent"] == "ops-troubleshooter"
    assert body["trace"]

    threads_response = await client.get("/threads", params={"user_id": "ops_001"})
    assert threads_response.status_code == 200
    assert threads_response.json()[0]["thread_id"] == body["thread_id"]


@pytest.mark.asyncio
async def test_chat_rejects_multiple_image_inputs(client: AsyncClient) -> None:
    response = await client.post(
        "/chat",
        json={
            "user_id": "ops_001",
            "message": "看图",
            "image_path": "a.jpg",
            "image_url": "https://example.com/a.jpg",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_review_approve_and_resume_api(client: AsyncClient) -> None:
    chat_response = await client.post(
        "/chat",
        json={"user_id": "ops_001", "message": "重启北门流媒体服务"},
    )
    assert chat_response.status_code == 200
    review_id = chat_response.json()["review_requests"][0]["review_id"]

    approve_response = await client.post(f"/reviews/{review_id}/approve")
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    resume_response = await client.post(f"/reviews/{review_id}/resume")
    assert resume_response.status_code == 200
    body = resume_response.json()
    assert body["review"]["status"] == "completed"
    assert body["resumed"] is True
    assert body["trace"][0]["type"] == "review_resumed"

    second_resume = await client.post(f"/reviews/{review_id}/resume")
    assert second_resume.status_code == 409
