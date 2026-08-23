import uuid
from datetime import datetime, timezone

import pytest

from app.api.routes.auth import activate_card_beta_access, complete_card_beta_walkthrough, signup
from app.api.routes import billing as billing_routes
from app.billing import stripe_client
from app.config import settings
from app.schemas.user import BetaActivationRequest, SignupRequest


class _ScalarResult:
    def scalar_one_or_none(self):
        return None


class _FakeSignupSession:
    def __init__(self):
        self.added = None
        self.commits = 0

    async def execute(self, _query):
        return _ScalarResult()

    def add(self, entity):
        self.added = entity

    async def commit(self):
        self.commits += 1

    async def refresh(self, _entity):
        _entity.id = _entity.id or uuid.uuid4()
        _entity.tier = _entity.tier or "starter"
        _entity.videos_used = _entity.videos_used or 0
        _entity.billing_plan = _entity.billing_plan or "trial"
        _entity.created_at = _entity.created_at or datetime.now(timezone.utc)
        _entity.updated_at = _entity.updated_at or datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_card_beta_signup_marks_origin_but_keeps_checkout_pending(monkeypatch):
    monkeypatch.setattr(settings, "beta_card_access_code", "card-beta-code")
    db = _FakeSignupSession()

    response = await signup(
        SignupRequest(email="card-beta@example.com", password="testpass123", beta_access_code="card-beta-code"),
        db=db,
    )

    assert response.user.subscription_status == "pending_checkout"
    assert db.added.is_beta_tester is True
    assert db.added.beta_variant == "card_required"
    assert db.added.beta_expires_at is None
    assert db.added.billing_plan == "trial"
    assert db.added.platforms_allowed == 0


@pytest.mark.asyncio
async def test_card_beta_activation_for_google_signup_does_not_grant_access(monkeypatch):
    monkeypatch.setattr(settings, "beta_card_access_code", "card-beta-code")
    db = _FakeSignupSession()
    user = type(
        "PendingUser",
        (),
        {
            "subscription_status": "pending_checkout",
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
            "is_beta_tester": False,
            "beta_variant": None,
        },
    )()

    response = await activate_card_beta_access(
        BetaActivationRequest(beta_access_code="card-beta-code"), db=db, current_user=user
    )

    assert response.message == "Card-required beta access activated"
    assert user.is_beta_tester is True
    assert user.beta_variant == "card_required"
    assert user.subscription_status == "pending_checkout"
    assert user.stripe_customer_id is None
    assert user.stripe_subscription_id is None


@pytest.mark.asyncio
async def test_card_beta_walkthrough_is_persisted_before_checkout():
    db = _FakeSignupSession()
    user = type(
        "CardBetaUser",
        (),
        {
            "is_beta_tester": True,
            "beta_variant": "card_required",
            "subscription_status": "pending_checkout",
            "beta_card_walkthrough_completed_at": None,
        },
    )()

    await complete_card_beta_walkthrough(db=db, current_user=user)

    assert user.beta_card_walkthrough_completed_at is not None
    assert db.commits == 1


@pytest.mark.asyncio
async def test_checkout_session_uses_requested_trial_length_without_changing_default(monkeypatch):
    captured: list[dict] = []

    def fake_create(**kwargs):
        captured.append(kwargs)
        return {"url": "https://checkout.example.test"}

    async def fake_threadpool(func, **kwargs):
        return func(**kwargs)

    monkeypatch.setattr(stripe_client, "require_billing_enabled", lambda: None)
    monkeypatch.setattr(stripe_client.stripe.checkout.Session, "create", fake_create)
    monkeypatch.setattr(stripe_client, "run_in_threadpool", fake_threadpool)

    await stripe_client.create_checkout_session(
        customer_id="cus_test",
        user_id="user_test",
        plan="creator",
        price_id="price_creator",
        success_url="https://example.test/success",
        cancel_url="https://example.test/cancel",
        trial_period_days=30,
    )
    await stripe_client.create_checkout_session(
        customer_id="cus_test",
        user_id="user_test",
        plan="creator",
        price_id="price_creator",
        success_url="https://example.test/success",
        cancel_url="https://example.test/cancel",
    )

    assert captured[0]["subscription_data"]["trial_period_days"] == 30
    assert captured[1]["subscription_data"]["trial_period_days"] == 7


@pytest.mark.asyncio
async def test_card_beta_checkout_uses_creator_price_and_a_thirty_day_trial(monkeypatch):
    captured: dict = {}

    async def fake_ensure_customer(_user, _db):
        return "cus_card_beta"

    async def fake_checkout(**kwargs):
        captured.update(kwargs)
        return {"url": "https://checkout.example.test/card-beta"}

    monkeypatch.setattr(settings, "frontend_url", "https://postbandit.example.test")
    monkeypatch.setattr(billing_routes, "_ensure_customer", fake_ensure_customer)
    monkeypatch.setattr(billing_routes, "create_checkout_session", fake_checkout)
    monkeypatch.setattr(billing_routes, "get_price_id", lambda plan: f"price_{plan}")
    user = type(
        "CardBetaUser",
        (),
        {
            "id": uuid.uuid4(),
            "is_beta_tester": True,
            "beta_variant": "card_required",
            "subscription_status": "pending_checkout",
            "beta_card_walkthrough_completed_at": datetime.now(timezone.utc),
        },
    )()

    response = await billing_routes.create_card_beta_checkout(db=object(), current_user=user)

    assert response.checkout_url == "https://checkout.example.test/card-beta"
    assert captured["plan"] == "creator"
    assert captured["price_id"] == "price_creator"
    assert captured["trial_period_days"] == 30
    assert captured["success_url"] == "https://postbandit.example.test/beta/welcome?status=checkout_success"
    assert captured["cancel_url"] == "https://postbandit.example.test/beta/welcome?status=checkout_cancelled"
