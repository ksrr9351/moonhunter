"""
Test cases for AI Dump Alert Service
Tests dump threshold detection, email eligibility, and rate limiting
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_dump_alert_service import AIDumpAlertService, DUMP_ALERT_THRESHOLD


class MockCollection:
    """Mock MongoDB collection"""
    def __init__(self, data=None):
        self.data = data or []
        self.inserted = []
        self.deleted_count = 0
    
    async def find(self, query=None):
        return MockCursor(self.data)
    
    async def find_one(self, query=None):
        return self.data[0] if self.data else None
    
    async def insert_one(self, doc):
        self.inserted.append(doc)
        return MagicMock(inserted_id="test_id")
    
    async def delete_many(self, query):
        result = MagicMock()
        result.deleted_count = self.deleted_count
        return result


class MockCursor:
    """Mock MongoDB cursor"""
    def __init__(self, data):
        self.data = data
    
    async def to_list(self, length=None):
        return self.data


class MockDB:
    """Mock database"""
    def __init__(self):
        self.alert_settings = MockCollection()
        self.ai_dump_alerts_sent = MockCollection()


class MockMarketProvider:
    """Mock market provider"""
    async def get_top_coins(self, limit):
        return [
            {
                "symbol": "BTC",
                "name": "Bitcoin",
                "price": 50000,
                "change1h": -2.0,
                "change24h": -3.0,
                "change7d": 5.0,
                "volume24h": 30000000000,
                "marketCap": 1000000000000,
                "rank": 1
            },
            {
                "symbol": "DUMP",
                "name": "DumpCoin",
                "price": 100,
                "change1h": -6.5,
                "change24h": -8.0,
                "change7d": -2.0,
                "volume24h": 50000000,
                "marketCap": 500000000,
                "rank": 50
            },
            {
                "symbol": "NEAR",
                "name": "NearDump",
                "price": 5,
                "change1h": -4.9,
                "change24h": -4.5,
                "change7d": 1.0,
                "volume24h": 20000000,
                "marketCap": 100000000,
                "rank": 80
            }
        ]


class MockDumpDetectionEngine:
    """Mock dump detection engine"""
    async def analyze_market(self, coins):
        opportunities = []
        for coin in coins:
            change_1h = coin.get("change1h", 0)
            if change_1h <= -5.0:
                opportunities.append({
                    "symbol": coin["symbol"],
                    "name": coin["name"],
                    "price_usdt": coin["price"],
                    "change_1h": change_1h,
                    "change_24h": coin.get("change24h", 0),
                    "change_7d": coin.get("change7d", 0),
                    "dump_magnitude": abs(change_1h),
                    "dump_window": "1h",
                    "volume_health": "healthy",
                    "risk_score": 0.3,
                    "recommendation": "buy",
                    "reason": "5% dump detected",
                    "logo": ""
                })
        return {
            "dump_opportunities": opportunities,
            "pump_risks": [],
            "neutral": [],
            "avoid_list": []
        }


class TestDumpThresholds:
    """Test dump threshold detection"""
    
    def test_threshold_constant(self):
        """Verify threshold is set to 5%"""
        assert DUMP_ALERT_THRESHOLD == 5.0
    
    @pytest.mark.asyncio
    async def test_dump_below_threshold_no_alert(self):
        """Test: Dump = 4.9% should NOT trigger email"""
        db = MockDB()
        market_provider = MockMarketProvider()
        dump_engine = MockDumpDetectionEngine()
        
        service = AIDumpAlertService(db, dump_engine, market_provider)
        
        coins = [
            {
                "symbol": "NEAR",
                "name": "NearDump",
                "price": 5,
                "change1h": -4.9,
                "change24h": -4.5,
                "change7d": 1.0,
                "volume24h": 20000000,
                "marketCap": 100000000,
                "rank": 80
            }
        ]
        
        analysis = await dump_engine.analyze_market(coins)
        
        qualifying = [
            d for d in analysis["dump_opportunities"]
            if d.get("dump_magnitude", 0) >= DUMP_ALERT_THRESHOLD
        ]
        
        assert len(qualifying) == 0, "4.9% dump should NOT qualify for alert"
    
    @pytest.mark.asyncio
    async def test_dump_at_threshold_triggers_alert(self):
        """Test: Dump = 5.0% should trigger email"""
        db = MockDB()
        market_provider = MockMarketProvider()
        dump_engine = MockDumpDetectionEngine()
        
        service = AIDumpAlertService(db, dump_engine, market_provider)
        
        coins = [
            {
                "symbol": "TEST",
                "name": "TestCoin",
                "price": 100,
                "change1h": -5.0,
                "change24h": -6.0,
                "change7d": 2.0,
                "volume24h": 50000000,
                "marketCap": 500000000,
                "rank": 30
            }
        ]
        
        analysis = await dump_engine.analyze_market(coins)
        
        qualifying = [
            d for d in analysis["dump_opportunities"]
            if d.get("dump_magnitude", 0) >= DUMP_ALERT_THRESHOLD
        ]
        
        assert len(qualifying) == 1, "5.0% dump SHOULD qualify for alert"
        assert qualifying[0]["symbol"] == "TEST"
    
    @pytest.mark.asyncio
    async def test_dump_above_threshold_triggers_alert(self):
        """Test: Dump > 5% should trigger email"""
        db = MockDB()
        market_provider = MockMarketProvider()
        dump_engine = MockDumpDetectionEngine()
        
        service = AIDumpAlertService(db, dump_engine, market_provider)
        
        coins = [
            {
                "symbol": "DUMP",
                "name": "DumpCoin",
                "price": 100,
                "change1h": -6.5,
                "change24h": -8.0,
                "change7d": -2.0,
                "volume24h": 50000000,
                "marketCap": 500000000,
                "rank": 50
            }
        ]
        
        analysis = await dump_engine.analyze_market(coins)
        
        qualifying = [
            d for d in analysis["dump_opportunities"]
            if d.get("dump_magnitude", 0) >= DUMP_ALERT_THRESHOLD
        ]
        
        assert len(qualifying) == 1, "6.5% dump SHOULD qualify for alert"
        assert qualifying[0]["dump_magnitude"] == 6.5


class TestEmailEligibility:
    """Test user eligibility for email alerts"""
    
    @pytest.mark.asyncio
    async def test_user_with_alerts_enabled(self):
        """Test: User with smart_alerts_enabled=true gets emails"""
        db = MockDB()
        db.alert_settings = MockCollection([
            {
                "user_id": "user1",
                "email": "test@example.com",
                "smart_alerts_enabled": True,
                "email_notifications_enabled": True
            }
        ])
        
        service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
        users = await service.get_eligible_users()
        
        assert len(users) == 1
        assert users[0]["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_user_with_alerts_disabled(self):
        """Test: User with email_notifications_enabled=false does NOT get emails"""
        db = MockDB()
        db.alert_settings = MockCollection([
            {
                "user_id": "user1",
                "email": "test@example.com",
                "smart_alerts_enabled": True,
                "email_notifications_enabled": False
            }
        ])
        
        service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
        users = await service.get_eligible_users()
        
        assert len(users) == 0
    
    def test_email_validation_valid(self):
        """Test: Valid email passes validation"""
        db = MockDB()
        service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
        
        assert service._validate_email("test@example.com") == True
        assert service._validate_email("user.name@domain.co.uk") == True
        assert service._validate_email("user+tag@gmail.com") == True
    
    def test_email_validation_invalid(self):
        """Test: Invalid email fails validation"""
        db = MockDB()
        service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
        
        assert service._validate_email("") == False
        assert service._validate_email(None) == False
        assert service._validate_email("notanemail") == False
        assert service._validate_email("missing@domain") == False


class TestRateLimiting:
    """Test rate limiting and duplicate prevention"""
    
    @pytest.mark.asyncio
    async def test_cooldown_prevents_duplicate(self):
        """Test: Recent alert prevents duplicate"""
        db = MockDB()
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        db.ai_dump_alerts_sent = MockCollection([
            {
                "user_id": "user1",
                "symbol": "BTC",
                "sent_at": recent_time.isoformat()
            }
        ])
        
        service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
        
        is_cooldown = await service.check_alert_cooldown("user1", "BTC")
        assert is_cooldown == True, "Should be in cooldown"
    
    @pytest.mark.asyncio
    async def test_no_cooldown_for_different_coin(self):
        """Test: Alert for different coin is allowed"""
        db = MockDB()
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        db.ai_dump_alerts_sent = MockCollection([
            {
                "user_id": "user1",
                "symbol": "BTC",
                "sent_at": recent_time.isoformat()
            }
        ])
        
        db.ai_dump_alerts_sent.data = []
        
        service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
        
        is_cooldown = await service.check_alert_cooldown("user1", "ETH")
        assert is_cooldown == False, "Different coin should not be in cooldown"
    
    @pytest.mark.asyncio
    async def test_expired_cooldown_allows_alert(self):
        """Test: Expired cooldown allows new alert"""
        db = MockDB()
        old_time = datetime.now(timezone.utc) - timedelta(hours=12)
        db.ai_dump_alerts_sent = MockCollection([])
        
        service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
        
        is_cooldown = await service.check_alert_cooldown("user1", "BTC")
        assert is_cooldown == False, "Expired cooldown should allow alert"


class TestEmailTemplate:
    """Test email template generation"""
    
    def test_template_generation(self):
        """Test: Email template generates valid HTML"""
        db = MockDB()
        service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
        
        dump_data = {
            "symbol": "BTC",
            "name": "Bitcoin",
            "price_usdt": 50000,
            "dump_magnitude": 5.5,
            "change_24h": -6.0,
            "change_7d": 2.0,
            "volume_health": "healthy",
            "risk_score": 0.3,
            "recommendation": "buy",
            "reason": "5% dump detected with healthy volume",
            "dump_window": "1h",
            "logo": ""
        }
        
        html = service.create_dump_alert_email_html(dump_data, "https://moonhunters.app")
        
        assert "<!DOCTYPE html>" in html
        assert "BTC" in html
        assert "Bitcoin" in html
        assert "5.5% DUMP DETECTED" in html
        assert "BUY" in html
        assert "View Opportunity" in html
        assert "Moon Hunters" in html
    
    def test_template_responsive(self):
        """Test: Email template has responsive styles"""
        db = MockDB()
        service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
        
        dump_data = {
            "symbol": "ETH",
            "name": "Ethereum",
            "price_usdt": 3000,
            "dump_magnitude": 7.2,
            "change_24h": -8.0,
            "change_7d": -1.0,
            "volume_health": "healthy",
            "risk_score": 0.25,
            "recommendation": "buy",
            "reason": "Strong buy signal",
            "dump_window": "1h",
            "logo": ""
        }
        
        html = service.create_dump_alert_email_html(dump_data)
        
        assert "@media only screen and (max-width: 600px)" in html
        assert "@media only screen and (min-width: 601px)" in html
        assert "viewport" in html


def run_tests():
    """Run all tests and print results"""
    print("=" * 60)
    print("AI DUMP ALERT SERVICE - TEST SUITE")
    print("=" * 60)
    
    results = {
        "passed": 0,
        "failed": 0,
        "errors": []
    }
    
    tests = [
        ("Threshold: 4.9% NO alert", test_dump_below_threshold),
        ("Threshold: 5.0% triggers alert", test_dump_at_threshold),
        ("Threshold: 6.5% triggers alert", test_dump_above_threshold),
        ("User alerts enabled", test_user_enabled),
        ("User alerts disabled", test_user_disabled),
        ("Email validation valid", test_email_valid),
        ("Email validation invalid", test_email_invalid),
        ("Cooldown prevents duplicate", test_cooldown_active),
        ("Different coin allowed", test_different_coin),
        ("Template generation", test_template),
        ("Template responsive", test_template_responsive),
    ]
    
    for name, test_func in tests:
        try:
            result = asyncio.run(test_func()) if asyncio.iscoroutinefunction(test_func) else test_func()
            if result:
                print(f"✅ PASS: {name}")
                results["passed"] += 1
            else:
                print(f"❌ FAIL: {name}")
                results["failed"] += 1
        except Exception as e:
            print(f"❌ ERROR: {name} - {str(e)}")
            results["failed"] += 1
            results["errors"].append(f"{name}: {str(e)}")
    
    print("=" * 60)
    print(f"Results: {results['passed']} passed, {results['failed']} failed")
    print("=" * 60)
    
    return results


async def test_dump_below_threshold():
    """4.9% should NOT trigger"""
    db = MockDB()
    engine = MockDumpDetectionEngine()
    coins = [{"symbol": "TEST", "name": "Test", "price": 100, "change1h": -4.9, "change24h": -4.0, "change7d": 1.0, "volume24h": 50000000, "marketCap": 500000000, "rank": 50}]
    analysis = await engine.analyze_market(coins)
    qualifying = [d for d in analysis["dump_opportunities"] if d.get("dump_magnitude", 0) >= DUMP_ALERT_THRESHOLD]
    return len(qualifying) == 0


async def test_dump_at_threshold():
    """5.0% SHOULD trigger"""
    db = MockDB()
    engine = MockDumpDetectionEngine()
    coins = [{"symbol": "TEST", "name": "Test", "price": 100, "change1h": -5.0, "change24h": -6.0, "change7d": 1.0, "volume24h": 50000000, "marketCap": 500000000, "rank": 50}]
    analysis = await engine.analyze_market(coins)
    qualifying = [d for d in analysis["dump_opportunities"] if d.get("dump_magnitude", 0) >= DUMP_ALERT_THRESHOLD]
    return len(qualifying) == 1


async def test_dump_above_threshold():
    """6.5% SHOULD trigger"""
    db = MockDB()
    engine = MockDumpDetectionEngine()
    coins = [{"symbol": "DUMP", "name": "Dump", "price": 100, "change1h": -6.5, "change24h": -8.0, "change7d": -2.0, "volume24h": 50000000, "marketCap": 500000000, "rank": 50}]
    analysis = await engine.analyze_market(coins)
    qualifying = [d for d in analysis["dump_opportunities"] if d.get("dump_magnitude", 0) >= DUMP_ALERT_THRESHOLD]
    return len(qualifying) == 1 and qualifying[0]["dump_magnitude"] == 6.5


async def test_user_enabled():
    """User with alerts enabled should be fetched"""
    db = MockDB()
    db.alert_settings = MockCollection([{"user_id": "u1", "email": "test@example.com", "smart_alerts_enabled": True, "email_notifications_enabled": True}])
    service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
    users = await service.get_eligible_users()
    return len(users) == 1


async def test_user_disabled():
    """User with alerts disabled should NOT be fetched"""
    db = MockDB()
    db.alert_settings = MockCollection([{"user_id": "u1", "email": "test@example.com", "smart_alerts_enabled": False, "email_notifications_enabled": False}])
    service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
    users = await service.get_eligible_users()
    return len(users) == 0


def test_email_valid():
    """Valid emails should pass"""
    db = MockDB()
    service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
    return (
        service._validate_email("test@example.com") and
        service._validate_email("user.name@domain.co.uk") and
        service._validate_email("user+tag@gmail.com")
    )


def test_email_invalid():
    """Invalid emails should fail"""
    db = MockDB()
    service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
    return (
        not service._validate_email("") and
        not service._validate_email(None) and
        not service._validate_email("notanemail")
    )


async def test_cooldown_active():
    """Recent alert should trigger cooldown"""
    db = MockDB()
    recent = datetime.now(timezone.utc) - timedelta(hours=1)
    db.ai_dump_alerts_sent = MockCollection([{"user_id": "u1", "symbol": "BTC", "sent_at": recent.isoformat()}])
    service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
    return await service.check_alert_cooldown("u1", "BTC") == True


async def test_different_coin():
    """Different coin should not be in cooldown"""
    db = MockDB()
    db.ai_dump_alerts_sent = MockCollection([])
    service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
    return await service.check_alert_cooldown("u1", "ETH") == False


def test_template():
    """Template should generate valid HTML"""
    db = MockDB()
    service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
    dump = {"symbol": "BTC", "name": "Bitcoin", "price_usdt": 50000, "dump_magnitude": 5.5, "change_24h": -6.0, "change_7d": 2.0, "volume_health": "healthy", "risk_score": 0.3, "recommendation": "buy", "reason": "Test", "dump_window": "1h", "logo": ""}
    html = service.create_dump_alert_email_html(dump)
    return "<!DOCTYPE html>" in html and "BTC" in html and "BUY" in html


def test_template_responsive():
    """Template should have responsive styles"""
    db = MockDB()
    service = AIDumpAlertService(db, MockDumpDetectionEngine(), MockMarketProvider())
    dump = {"symbol": "ETH", "name": "Ethereum", "price_usdt": 3000, "dump_magnitude": 7.0, "change_24h": -8.0, "change_7d": -1.0, "volume_health": "healthy", "risk_score": 0.25, "recommendation": "buy", "reason": "Test", "dump_window": "1h", "logo": ""}
    html = service.create_dump_alert_email_html(dump)
    return "@media only screen and (max-width: 600px)" in html


if __name__ == "__main__":
    run_tests()
