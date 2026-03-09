import pytest
import httpx
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server import app


@pytest.fixture
def client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


# =============================================================================
# 1. Health Check
# =============================================================================

@pytest.mark.asyncio
async def test_health_check(client):
    async with client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "moon-hunters-api"
        assert "database" in data
        assert "status" in data
        assert data["status"] in ("healthy", "degraded")
        assert "websocket_connections" in data
        assert "streaming_active" in data
        assert "demo_mode" in data
        assert "environment" in data


# =============================================================================
# 2. Auth Endpoints
# =============================================================================

@pytest.mark.asyncio
async def test_wallet_nonce_generation(client):
    async with client:
        response = await client.post(
            "/api/auth/wallet/nonce",
            json={"address": "0x1234567890abcdef1234567890abcdef12345678"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "nonce" in data
        assert isinstance(data["nonce"], str)
        assert len(data["nonce"]) > 0


@pytest.mark.asyncio
async def test_wallet_nonce_invalid_address(client):
    async with client:
        response = await client.post(
            "/api/auth/wallet/nonce",
            json={"address": "invalid_address"}
        )
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == 422


@pytest.mark.asyncio
async def test_signup_validation_missing_fields(client):
    async with client:
        response = await client.post(
            "/api/auth/signup",
            json={}
        )
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == 422
        assert "details" in data["error"]
        assert isinstance(data["error"]["details"], list)
        assert len(data["error"]["details"]) > 0


@pytest.mark.asyncio
async def test_signup_validation_short_password(client):
    async with client:
        response = await client.post(
            "/api/auth/signup",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "short"
            }
        )
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == 422


@pytest.mark.asyncio
async def test_signup_validation_invalid_email(client):
    async with client:
        response = await client.post(
            "/api/auth/signup",
            json={
                "email": "not-an-email",
                "username": "testuser",
                "password": "validpassword123"
            }
        )
        assert response.status_code == 422
        data = response.json()
        assert "error" in data


@pytest.mark.asyncio
async def test_signup_validation_invalid_username(client):
    async with client:
        response = await client.post(
            "/api/auth/signup",
            json={
                "email": "test@example.com",
                "username": "ab",
                "password": "validpassword123"
            }
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    async with client:
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "wrongpassword123"
            }
        )
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == 401
        assert "Invalid" in data["error"]["message"]


@pytest.mark.asyncio
async def test_login_missing_fields(client):
    async with client:
        response = await client.post(
            "/api/auth/login",
            json={}
        )
        assert response.status_code == 422


# =============================================================================
# 3. Crypto Endpoints
# =============================================================================

@pytest.mark.asyncio
async def test_crypto_latest(client):
    async with client:
        response = await client.get("/api/crypto/latest?limit=5")
        assert response.status_code in (200, 503)
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert "timestamp" in data
            assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_crypto_latest_default_limit(client):
    async with client:
        response = await client.get("/api/crypto/latest")
        assert response.status_code in (200, 503)
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert len(data["data"]) <= 10


@pytest.mark.asyncio
async def test_crypto_latest_invalid_limit(client):
    async with client:
        response = await client.get("/api/crypto/latest?limit=0")
        assert response.status_code == 422


# =============================================================================
# 4. Backtest Endpoints
# =============================================================================

@pytest.mark.asyncio
async def test_backtest_strategies_requires_auth(client):
    async with client:
        response = await client.get("/api/backtest/strategies")
        assert response.status_code in [401, 403]


# =============================================================================
# 5. Social Endpoints
# =============================================================================

@pytest.mark.asyncio
async def test_social_leaderboard(client):
    async with client:
        response = await client.get("/api/social/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        assert "period" in data
        assert data["period"] == "all"
        assert isinstance(data["leaderboard"], list)


@pytest.mark.asyncio
async def test_social_leaderboard_with_period(client):
    async with client:
        response = await client.get("/api/social/leaderboard?period=week")
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "week"


@pytest.mark.asyncio
async def test_social_leaderboard_with_limit(client):
    async with client:
        response = await client.get("/api/social/leaderboard?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["leaderboard"], list)


# =============================================================================
# 6. WebSocket Endpoint
# =============================================================================

@pytest.mark.asyncio
async def test_websocket_status_endpoint(client):
    async with client:
        response = await client.get("/api/ws/status")
        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data
        assert "is_streaming" in data
        assert isinstance(data["active_connections"], int)
        assert isinstance(data["is_streaming"], bool)


# =============================================================================
# 7. Error Handling
# =============================================================================

@pytest.mark.asyncio
async def test_422_validation_error_format(client):
    async with client:
        response = await client.post(
            "/api/auth/wallet/nonce",
            json={"address": "bad"}
        )
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "code" in data["error"]
        assert data["error"]["code"] == 422
        assert "message" in data["error"]
        assert data["error"]["message"] == "Request validation failed"
        assert "details" in data["error"]
        assert isinstance(data["error"]["details"], list)
        for detail in data["error"]["details"]:
            assert "field" in detail
            assert "message" in detail
            assert "type" in detail


@pytest.mark.asyncio
async def test_401_unauthorized_access(client):
    async with client:
        response = await client.get("/api/auth/me")
        assert response.status_code in (401, 403)
        data = response.json()
        assert "error" in data or "detail" in data


@pytest.mark.asyncio
async def test_401_with_invalid_bearer_token(client):
    async with client:
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == 401


@pytest.mark.asyncio
async def test_401_intelligence_without_auth(client):
    async with client:
        response = await client.get("/api/intelligence/stats")
        assert response.status_code in (401, 403)


# =============================================================================
# 8. Intelligence Endpoints
# =============================================================================

@pytest.mark.asyncio
async def test_intelligence_stats_requires_auth(client):
    async with client:
        response = await client.get("/api/intelligence/stats")
        assert response.status_code in (401, 403)
        data = response.json()
        assert "error" in data or "detail" in data


@pytest.mark.asyncio
async def test_intelligence_stats_invalid_token(client):
    async with client:
        response = await client.get(
            "/api/intelligence/stats",
            headers={"Authorization": "Bearer fake_token"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_intelligence_signal_requires_auth(client):
    async with client:
        response = await client.get("/api/intelligence/signal/BTC")
        assert response.status_code in (401, 403)


# =============================================================================
# Additional Edge Cases
# =============================================================================

@pytest.mark.asyncio
async def test_wallet_nonce_missing_body(client):
    async with client:
        response = await client.post("/api/auth/wallet/nonce")
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_wallet_logout(client):
    async with client:
        response = await client.post("/api/auth/wallet/logout")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logged out successfully"


@pytest.mark.asyncio
async def test_auth_logout(client):
    async with client:
        response = await client.post("/api/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logged out successfully"
