from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
import stripe

from db import get_db_session, add_paid_credits, record_purchase, has_processed_session, get_user_by_id

# Load .env early
load_dotenv()

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8501")

# Credits/package settings
CREDITS_PER_PURCHASE = int(os.getenv("CREDITS_PER_PURCHASE", "100"))
PRICE_USD_CENTS = int(os.getenv("PRICE_USD_CENTS", "1000"))  # $10 default

if STRIPE_API_KEY:
    stripe.api_key = STRIPE_API_KEY


def create_checkout_session(user) -> Optional[str]:
    if not STRIPE_API_KEY:
        return None

    success_url = f"{APP_BASE_URL}?success=1&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{APP_BASE_URL}?canceled=1"

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"{CREDITS_PER_PURCHASE} Swatch Downloads",
                            "description": "Download swatches generated in the app",
                        },
                        "unit_amount": PRICE_USD_CENTS,
                    },
                    "quantity": 1,
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "purpose": "swatch_credits",
                "credits": str(CREDITS_PER_PURCHASE),
                "user_id": str(getattr(user, "id", None) or user.get("id")),
                "user_email": getattr(user, "email", None) or user.get("email"),
            },
        )
        return session.url
    except Exception:
        return None


def verify_and_apply_credits(session_id: str, user_id: int) -> tuple[bool, str]:
    if not STRIPE_API_KEY:
        return False, "Stripe not configured"

    db = get_db_session()
    try:
        if has_processed_session(db, session_id):
            return True, "Credits already applied"

        session = stripe.checkout.Session.retrieve(session_id)
        if session and session.get("payment_status") == "paid":
            user = get_user_by_id(db, user_id)
            if not user:
                return False, "User not found"
            credits_to_add = CREDITS_PER_PURCHASE
            add_paid_credits(db, user, credits_to_add)
            record_purchase(db, user, session_id, credits_to_add)
            return True, "Credits added"
        return False, "Payment not completed"
    except Exception:
        return False, "Failed to verify payment"
    finally:
        db.close()