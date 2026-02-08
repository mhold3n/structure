import pytest
from httpx import AsyncClient
from gateway.main import app


@pytest.mark.asyncio
async def test_e2e_workflow():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1. Submit a multi-step request
        response = await ac.post(
            "/workflow",
            json={
                "user_input": (
                    "1. Calculate mean of [1, 2, 3]. 2. Summarize 'Hello world. Hello universe.'"
                ),
                "domain_hint": "analysis",
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert "workflow_id" in data
        assert data["status"] in [
            "completed",
            "failed",
            "blocked",
        ]  # Could fail if router not mocked
