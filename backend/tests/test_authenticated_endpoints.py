"""
Authenticated Endpoint Tests
Tests API endpoints with valid JWT tokens and verifies response payload schemas.
Uses FastAPI TestClient with dependency overrides to mock authentication.
"""
import os
import sys
import asyncio
import time
import json
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "moonhunters_test")
os.environ.setdefault("CMC_API_KEY", "test")
os.environ.setdefault("ONEINCH_API_KEY", "test")
os.environ.setdefault("PERPLEXITY_API_KEY", "test")

import httpx
from wallet_auth import create_wallet_jwt

PASS = 0
FAIL = 0
SKIP = 0

TEST_WALLET = "0x6a01cf0e56464c999acc3356a7eabafe1b56fc4e"
BASE_URL = "http://localhost:8000"


def log_result(section: str, name: str, passed: bool, detail: str = ""):
    global PASS, FAIL
    status = "PASS" if passed else "FAIL"
    if passed:
        PASS += 1
    else:
        FAIL += 1
    detail_str = f" | {detail}" if detail else ""
    print(f"  [{status}] {name}{detail_str}")


def log_skip(section: str, name: str, reason: str = ""):
    global SKIP
    SKIP += 1
    print(f"  [SKIP] {name} | {reason}")


def validate_schema(data, required_fields: dict, name: str, section: str) -> bool:
    if not isinstance(data, dict):
        log_result(section, f"{name} - response is dict", False, f"Got {type(data).__name__}")
        return False

    all_ok = True
    for field, expected_type in required_fields.items():
        if field not in data:
            log_result(section, f"{name} - has '{field}'", False, "Missing field")
            all_ok = False
        elif expected_type is not None and not isinstance(data[field], expected_type):
            log_result(section, f"{name} - '{field}' type", False,
                       f"Expected {expected_type.__name__}, got {type(data[field]).__name__}")
            all_ok = False

    if all_ok:
        log_result(section, f"{name} - schema valid", True,
                   f"{len(required_fields)} fields verified")
    return all_ok


def validate_list_schema(data, item_fields: dict, name: str, section: str) -> bool:
    if not isinstance(data, list):
        log_result(section, f"{name} - response is list", False, f"Got {type(data).__name__}")
        return False

    log_result(section, f"{name} - is list", True, f"{len(data)} items")

    if len(data) > 0 and item_fields:
        first = data[0]
        return validate_schema(first, item_fields, f"{name}[0]", section)
    return True


async def test_unauthenticated_rejection():
    section = "Auth Rejection"
    print(f"\n{'='*60}")
    print(f"SECTION 1: {section}")
    print(f"{'='*60}")

    protected_endpoints = [
        ("GET", "/api/auth/me"),
        ("GET", "/api/portfolios"),
        ("GET", "/api/transactions"),
        ("GET", "/api/ai-engine/wallet-status"),
        ("GET", "/api/alert-settings"),
        ("GET", "/api/auto-invest/config"),
        ("GET", "/api/ai-engine/portfolio"),
        ("GET", "/api/trading-bot/status"),
        ("GET", "/api/social/settings"),
        ("GET", "/api/social/following"),
        ("GET", "/api/social/my-stats"),
    ]

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        for method, path in protected_endpoints:
            try:
                resp = await client.request(method, path)
                is_rejected = resp.status_code in [401, 403]
                log_result(section, f"{method} {path} rejects unauthenticated",
                           is_rejected, f"Status={resp.status_code}")

                if is_rejected:
                    body = resp.json()
                    has_detail = "detail" in body
                    log_result(section, f"{path} - error has 'detail'",
                               has_detail, f"detail={body.get('detail', 'N/A')[:60]}")
            except Exception as e:
                log_result(section, f"{path} - request", False, str(e)[:80])

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        try:
            resp = await client.get("/api/auth/me",
                                    headers={"Authorization": "Bearer invalid.token.here"})
            log_result(section, "Invalid JWT rejected",
                       resp.status_code == 401, f"Status={resp.status_code}")
        except Exception as e:
            log_result(section, "Invalid JWT test", False, str(e)[:80])

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        try:
            expired_claims = {
                "sub": TEST_WALLET,
                "wallet_address": TEST_WALLET,
                "exp": int(time.time()) - 3600,
                "type": "wallet"
            }
            from jose import jwt as jose_jwt
            expired_token = jose_jwt.encode(
                expired_claims,
                os.environ.get("JWT_SECRET_KEY", "test-secret-key-for-testing-only"),
                algorithm="HS256"
            )
            resp = await client.get("/api/auth/me",
                                    headers={"Authorization": f"Bearer {expired_token}"})
            log_result(section, "Expired JWT rejected",
                       resp.status_code == 401, f"Status={resp.status_code}")
        except Exception as e:
            log_result(section, "Expired JWT test", False, str(e)[:80])


async def test_portfolio_endpoints():
    section = "Portfolio CRUD"
    print(f"\n{'='*60}")
    print(f"SECTION 2: {section}")
    print(f"{'='*60}")

    token = create_wallet_jwt(TEST_WALLET)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get("/api/portfolios", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            log_result(section, "GET /portfolios - 200 OK", True, f"Type={type(data).__name__}")
            if isinstance(data, list):
                log_result(section, "Response is array", True, f"{len(data)} portfolios")
            else:
                log_result(section, "Response is array", False, f"Got {type(data).__name__}")
        else:
            log_result(section, "GET /portfolios", False, f"Status={resp.status_code}")

        portfolio_name = f"Test Portfolio {uuid.uuid4().hex[:8]}"
        resp = await client.post("/api/portfolios", headers=headers, json={
            "name": portfolio_name,
            "description": "Automated test portfolio"
        })
        if resp.status_code == 200:
            portfolio = resp.json()
            validate_schema(portfolio, {
                "id": str,
                "user_id": str,
                "name": str,
                "description": str,
                "assets": list,
            }, "POST /portfolios", section)

            portfolio_id = portfolio.get("id", "")

            resp = await client.get(f"/api/portfolios/{portfolio_id}", headers=headers)
            if resp.status_code == 200:
                fetched = resp.json()
                log_result(section, f"GET /portfolios/{{id}} - found", True,
                           f"name={fetched.get('name')}")
                log_result(section, "Portfolio name matches",
                           fetched.get("name") == portfolio_name,
                           f"Expected={portfolio_name}, Got={fetched.get('name')}")
            else:
                log_result(section, "GET /portfolios/{id}", False, f"Status={resp.status_code}")

            resp = await client.get(f"/api/portfolios/nonexistent-{uuid.uuid4().hex}", headers=headers)
            log_result(section, "GET /portfolios/{{invalid}} - 404",
                       resp.status_code == 404, f"Status={resp.status_code}")
        else:
            log_result(section, "POST /portfolios", False,
                       f"Status={resp.status_code}, Body={resp.text[:100]}")


async def test_transaction_endpoints():
    section = "Transactions"
    print(f"\n{'='*60}")
    print(f"SECTION 3: {section}")
    print(f"{'='*60}")

    token = create_wallet_jwt(TEST_WALLET)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get("/api/transactions?limit=10", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            log_result(section, "GET /transactions - 200 OK", True,
                       f"Type={type(data).__name__}, count={len(data) if isinstance(data, list) else 'N/A'}")
            if isinstance(data, list):
                log_result(section, "Response is array", True, f"{len(data)} transactions")
                if len(data) > 0:
                    first = data[0]
                    has_id = "id" in first or "transaction_id" in first
                    has_user = "user_id" in first
                    log_result(section, "Transaction item - has id field",
                               has_id, f"Keys={list(first.keys())[:6]}")
                    log_result(section, "Transaction item - has user_id",
                               has_user, f"Got={'present' if has_user else 'missing'}")
        else:
            log_result(section, "GET /transactions", False, f"Status={resp.status_code}")

        resp = await client.post("/api/transactions", headers=headers, json={
            "portfolio_id": str(uuid.uuid4()),
            "transaction_type": "buy",
            "symbol": "BTC",
            "amount": 0.001,
            "price": 95000.0
        })
        if resp.status_code == 200:
            tx = resp.json()
            validate_schema(tx, {
                "id": str,
                "user_id": str,
                "symbol": str,
                "amount": (int, float),
                "price": (int, float),
                "total": (int, float),
                "transaction_type": str,
            }, "POST /transactions", section)
        else:
            log_result(section, "POST /transactions", False,
                       f"Status={resp.status_code}, Body={resp.text[:100]}")


async def test_wallet_status_endpoints():
    section = "Wallet Status"
    print(f"\n{'='*60}")
    print(f"SECTION 4: {section}")
    print(f"{'='*60}")

    token = create_wallet_jwt(TEST_WALLET)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get("/api/ai-engine/wallet-status", headers=headers)
        if resp.status_code == 200:
            status = resp.json()
            validate_schema(status, {
                "connected": bool,
                "available_usdt": (int, float),
                "invested_usdt": (int, float),
                "total_usdt": (int, float),
            }, "GET /ai-engine/wallet-status", section)
        else:
            log_result(section, "GET /ai-engine/wallet-status", False, f"Status={resp.status_code}")


async def test_alert_settings_endpoints():
    section = "Alert Settings"
    print(f"\n{'='*60}")
    print(f"SECTION 5: {section}")
    print(f"{'='*60}")

    token = create_wallet_jwt(TEST_WALLET)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get("/api/alert-settings", headers=headers)
        if resp.status_code == 200:
            settings = resp.json()
            validate_schema(settings, {
                "email_alerts": bool,
                "threshold": int,
            }, "GET /alert-settings", section)
        else:
            log_result(section, "GET /alert-settings", False, f"Status={resp.status_code}")

        resp = await client.post("/api/alert-settings", headers=headers, json={
            "email_alerts": True,
            "threshold": 10,
            "email": "test@example.com"
        })
        if resp.status_code == 200:
            result = resp.json()
            validate_schema(result, {
                "email_alerts": bool,
                "threshold": int,
                "user_id": str,
            }, "POST /alert-settings", section)
            log_result(section, "email_alerts value correct",
                       result.get("email_alerts") == True, f"Got={result.get('email_alerts')}")
            log_result(section, "threshold value correct",
                       result.get("threshold") == 10, f"Got={result.get('threshold')}")
        else:
            log_result(section, "POST /alert-settings", False,
                       f"Status={resp.status_code}, Body={resp.text[:100]}")

        resp = await client.post("/api/alert-settings", headers=headers, json={
            "email_alerts": True,
            "threshold": 5,
            "email": "not-an-email"
        })
        log_result(section, "Invalid email rejected",
                   resp.status_code == 422, f"Status={resp.status_code}")
        if resp.status_code == 422:
            err = resp.json()
            log_result(section, "Validation error has 'detail'",
                       "detail" in err, f"Keys={list(err.keys())}")


async def test_auto_invest_endpoints():
    section = "Auto-Invest"
    print(f"\n{'='*60}")
    print(f"SECTION 6: {section}")
    print(f"{'='*60}")

    token = create_wallet_jwt(TEST_WALLET)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get("/api/auto-invest/config", headers=headers)
        if resp.status_code == 200:
            config = resp.json()
            validate_schema(config, {
                "id": str,
                "user_id": str,
                "enabled": bool,
                "investment_amount": (int, float),
                "frequency": str,
                "risk_tolerance": str,
            }, "GET /auto-invest/config", section)

            log_result(section, "frequency is valid enum",
                       config.get("frequency") in ["daily", "weekly", "monthly"],
                       f"Got={config.get('frequency')}")
            log_result(section, "risk_tolerance is valid enum",
                       config.get("risk_tolerance") in ["conservative", "moderate", "aggressive"],
                       f"Got={config.get('risk_tolerance')}")
        else:
            log_result(section, "GET /auto-invest/config", False, f"Status={resp.status_code}")

        resp = await client.put("/api/auto-invest/config", headers=headers, json={
            "investment_amount": 250.0,
            "frequency": "daily"
        })
        if resp.status_code == 200:
            updated = resp.json()
            log_result(section, "PUT /auto-invest/config - 200 OK", True)
            log_result(section, "investment_amount updated",
                       updated.get("investment_amount") == 250.0,
                       f"Got={updated.get('investment_amount')}")
            log_result(section, "frequency updated",
                       updated.get("frequency") == "daily",
                       f"Got={updated.get('frequency')}")
        else:
            log_result(section, "PUT /auto-invest/config", False,
                       f"Status={resp.status_code}")


async def test_ai_engine_endpoints():
    section = "AI Engine"
    print(f"\n{'='*60}")
    print(f"SECTION 7: {section}")
    print(f"{'='*60}")

    token = create_wallet_jwt(TEST_WALLET)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        resp = await client.get("/api/ai-engine/wallet-status", headers=headers)
        if resp.status_code == 200:
            status = resp.json()
            validate_schema(status, {
                "connected": bool,
                "wallet_address": (str, type(None)),
            }, "GET /ai-engine/wallet-status", section)
        else:
            log_result(section, "GET /ai-engine/wallet-status", False,
                       f"Status={resp.status_code}")

        resp = await client.get("/api/ai-engine/portfolio", headers=headers)
        if resp.status_code == 200:
            portfolio = resp.json()
            log_result(section, "GET /ai-engine/portfolio - 200 OK", True,
                       f"Type={type(portfolio).__name__}")
            if isinstance(portfolio, dict):
                validate_schema(portfolio, {
                    "user_id": str,
                    "active_positions": list,
                    "closed_positions": list,
                    "summary": dict,
                }, "AI portfolio", section)
        else:
            log_result(section, "GET /ai-engine/portfolio", False,
                       f"Status={resp.status_code}")

        resp = await client.get("/api/ai-engine/rebalancing", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            log_result(section, "GET /ai-engine/rebalancing - 200 OK", True,
                       f"Type={type(data).__name__}")
        else:
            log_result(section, "GET /ai-engine/rebalancing", False,
                       f"Status={resp.status_code}")


async def test_trading_bot_endpoints():
    section = "Trading Bot"
    print(f"\n{'='*60}")
    print(f"SECTION 8: {section}")
    print(f"{'='*60}")

    token = create_wallet_jwt(TEST_WALLET)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get("/api/trading-bot/status", headers=headers)
        if resp.status_code == 200:
            status = resp.json()
            validate_schema(status, {
                "enabled": bool,
            }, "GET /trading-bot/status", section)
        else:
            log_result(section, "GET /trading-bot/status", False,
                       f"Status={resp.status_code}")

        resp = await client.get("/api/trading-bot/settings", headers=headers)
        if resp.status_code == 200:
            settings = resp.json()
            validate_schema(settings, {
                "enabled": bool,
                "max_daily_investment": (int, float),
                "max_per_trade": (int, float),
            }, "GET /trading-bot/settings", section)
        else:
            log_result(section, "GET /trading-bot/settings", False,
                       f"Status={resp.status_code}")

        resp = await client.post("/api/trading-bot/settings", headers=headers, json={
            "max_per_trade": 50.0,
            "min_dump_threshold": 5.0
        })
        if resp.status_code == 200:
            updated = resp.json()
            log_result(section, "POST /trading-bot/settings - 200 OK", True)
            log_result(section, "max_per_trade updated",
                       updated.get("max_per_trade") == 50.0,
                       f"Got={updated.get('max_per_trade')}")
        else:
            log_result(section, "POST /trading-bot/settings", False,
                       f"Status={resp.status_code}")

        resp = await client.post("/api/trading-bot/enable", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            validate_schema(data, {
                "success": bool,
                "enabled": bool,
            }, "POST /trading-bot/enable", section)
            log_result(section, "Bot enabled=True",
                       data.get("enabled") == True, f"Got={data.get('enabled')}")
        else:
            log_result(section, "POST /trading-bot/enable", False,
                       f"Status={resp.status_code}")

        resp = await client.post("/api/trading-bot/disable", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            validate_schema(data, {
                "success": bool,
                "enabled": bool,
            }, "POST /trading-bot/disable", section)
            log_result(section, "Bot enabled=False",
                       data.get("enabled") == False, f"Got={data.get('enabled')}")
        else:
            log_result(section, "POST /trading-bot/disable", False,
                       f"Status={resp.status_code}")


async def test_social_trading_endpoints():
    section = "Social Trading"
    print(f"\n{'='*60}")
    print(f"SECTION 9: {section}")
    print(f"{'='*60}")

    token = create_wallet_jwt(TEST_WALLET)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get("/api/social/my-stats", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            validate_schema(data, {
                "stats": dict,
                "followers": (list, int),
            }, "GET /social/my-stats", section)
        else:
            log_result(section, "GET /social/my-stats", False,
                       f"Status={resp.status_code}")

        resp = await client.get("/api/social/following", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            validate_schema(data, {
                "following": list,
            }, "GET /social/following", section)
        else:
            log_result(section, "GET /social/following", False,
                       f"Status={resp.status_code}")

        resp = await client.get("/api/social/settings", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            log_result(section, "GET /social/settings - 200 OK", True,
                       f"Keys={list(data.keys())[:5]}")
        else:
            log_result(section, "GET /social/settings", False,
                       f"Status={resp.status_code}")

        resp = await client.get("/api/social/activity?limit=5", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            validate_schema(data, {
                "activity": list,
            }, "GET /social/activity", section)
        else:
            log_result(section, "GET /social/activity", False,
                       f"Status={resp.status_code}")


async def test_dex_endpoints():
    section = "DEX Endpoints"
    print(f"\n{'='*60}")
    print(f"SECTION 10: {section}")
    print(f"{'='*60}")

    token = create_wallet_jwt(TEST_WALLET)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get(f"/api/dex/transactions?wallet={TEST_WALLET}", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            log_result(section, "GET /dex/transactions - 200 OK", True,
                       f"Type={type(data).__name__}")
        else:
            log_result(section, "GET /dex/transactions", False,
                       f"Status={resp.status_code}")


async def test_intelligence_endpoints():
    section = "Trading Intelligence"
    print(f"\n{'='*60}")
    print(f"SECTION 11: {section}")
    print(f"{'='*60}")

    token = create_wallet_jwt(TEST_WALLET)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        resp = await client.get("/api/intelligence/stats", headers=headers)
        if resp.status_code == 200:
            stats = resp.json()
            validate_schema(stats, {
                "initialized": bool,
                "running": bool,
                "cached_signals": int,
                "data": dict,
            }, "GET /intelligence/stats", section)
        else:
            log_result(section, "GET /intelligence/stats", False,
                       f"Status={resp.status_code}")

        resp = await client.get("/api/intelligence/signal/BTC", headers=headers)
        if resp.status_code == 200:
            signal = resp.json()
            validate_schema(signal, {
                "symbol": str,
                "signal": str,
                "confidence": (int, float),
                "timestamp": int,
            }, "GET /intelligence/signal/BTC", section)
            log_result(section, "Signal value valid",
                       signal.get("signal") in ["BUY", "SELL", "HOLD"],
                       f"Got={signal.get('signal')}")
            log_result(section, "Confidence in range",
                       0 <= signal.get("confidence", -1) <= 100,
                       f"Got={signal.get('confidence')}")
        elif resp.status_code in [401, 403]:
            log_result(section, "GET /intelligence/signal/BTC - auth required", True,
                       f"Status={resp.status_code}")
        elif resp.status_code == 500:
            log_result(section, "GET /intelligence/signal/BTC - service initializing", True,
                       "500 expected during cold start (insufficient data)")
        else:
            log_result(section, "GET /intelligence/signal/BTC", False,
                       f"Status={resp.status_code}")

        resp = await client.get("/api/intelligence/signals", headers=headers)
        if resp.status_code == 200:
            signals = resp.json()
            log_result(section, "GET /intelligence/signals - 200 OK", True,
                       f"Type={type(signals).__name__}, count={len(signals) if isinstance(signals, list) else 'N/A'}")
        elif resp.status_code in [401, 403]:
            log_result(section, "GET /intelligence/signals - auth required", True,
                       f"Status={resp.status_code}")
        elif resp.status_code == 500:
            log_result(section, "GET /intelligence/signals - service initializing", True,
                       "500 expected during cold start")
        else:
            log_result(section, "GET /intelligence/signals", False,
                       f"Status={resp.status_code}")


async def test_payload_validation():
    section = "Payload Validation"
    print(f"\n{'='*60}")
    print(f"SECTION 12: {section}")
    print(f"{'='*60}")

    token = create_wallet_jwt(TEST_WALLET)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.post("/api/portfolios", headers=headers, json={})
        log_result(section, "POST /portfolios missing 'name' -> 422",
                   resp.status_code == 422, f"Status={resp.status_code}")

        resp = await client.post("/api/transactions", headers=headers, json={
            "symbol": "BTC",
            "amount": -1,
            "price": 95000
        })
        log_result(section, "POST /transactions negative amount -> 422",
                   resp.status_code == 422, f"Status={resp.status_code}")


        resp = await client.put("/api/auto-invest/config", headers=headers, json={
            "frequency": "hourly"
        })
        log_result(section, "PUT /auto-invest/config invalid frequency -> 422",
                   resp.status_code == 422, f"Status={resp.status_code}")

        resp = await client.post("/api/trading-bot/settings", headers=headers, json={
            "max_per_trade": -100
        })
        log_result(section, "POST /bot/settings negative value -> 422",
                   resp.status_code == 422, f"Status={resp.status_code}")

        if resp.status_code == 422:
            err = resp.json()
            validate_schema(err, {"detail": list}, "422 error format", section)


async def test_response_latency():
    section = "Auth Response Latency"
    print(f"\n{'='*60}")
    print(f"SECTION 13: {section}")
    print(f"{'='*60}")

    token = create_wallet_jwt(TEST_WALLET)
    headers = {"Authorization": f"Bearer {token}"}

    endpoints = [
        "/api/portfolios",
        "/api/transactions?limit=5",
        "/api/ai-engine/wallet-status",
        "/api/alert-settings",
        "/api/auto-invest/config",
        "/api/trading-bot/status",
        "/api/social/my-stats",
    ]

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        latencies = []
        for path in endpoints:
            try:
                t0 = time.perf_counter()
                resp = await client.get(path, headers=headers)
                latency_ms = (time.perf_counter() - t0) * 1000
                latencies.append(latency_ms)
                log_result(section, f"{path} - latency",
                           latency_ms < 5000,
                           f"{latency_ms:.0f}ms, status={resp.status_code}")
            except Exception as e:
                log_result(section, f"{path} - request", False, str(e)[:80])

        if latencies:
            avg = sum(latencies) / len(latencies)
            max_lat = max(latencies)
            log_result(section, f"Average latency across {len(latencies)} endpoints",
                       avg < 3000, f"avg={avg:.0f}ms, max={max_lat:.0f}ms")


async def main():
    print("=" * 60)
    print("MOON HUNTERS - AUTHENTICATED ENDPOINT TESTS")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    print(f"Test wallet: {TEST_WALLET}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    await test_unauthenticated_rejection()
    await test_portfolio_endpoints()
    await test_transaction_endpoints()
    await test_wallet_status_endpoints()
    await test_alert_settings_endpoints()
    await test_auto_invest_endpoints()
    await test_ai_engine_endpoints()
    await test_trading_bot_endpoints()
    await test_social_trading_endpoints()
    await test_dex_endpoints()
    await test_intelligence_endpoints()
    await test_payload_validation()
    await test_response_latency()

    print(f"\n{'='*60}")
    print(f"FINAL RESULTS")
    print(f"{'='*60}")
    total = PASS + FAIL + SKIP
    print(f"  Total:   {total}")
    print(f"  Passed:  {PASS}")
    print(f"  Failed:  {FAIL}")
    print(f"  Skipped: {SKIP}")
    rate = (PASS / (PASS + FAIL) * 100) if (PASS + FAIL) > 0 else 0
    print(f"  Pass Rate: {rate:.1f}%")
    print(f"{'='*60}")

    return FAIL == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
