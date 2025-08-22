from __future__ import annotations

import os
from typing import Optional

import streamlit as st
from email_validator import validate_email, EmailNotValidError
from dotenv import load_dotenv

from db import init_db, get_db_session, create_user, authenticate_user, decrement_download_credit, get_user_by_email
from utils import normalize_hex, generate_swatch_image, image_to_bytes
from payments import create_checkout_session, verify_and_apply_credits


APP_TITLE = "🎨 Swatch Generator"

# Load env and initialize database
load_dotenv()
init_db()


def get_current_user():
    return st.session_state.get("current_user")


def set_current_user(user_obj):
    st.session_state["current_user"] = user_obj


def handle_auth_ui():
    tabs = st.tabs(["Log In", "Register"])

    with tabs[0]:
        st.subheader("Log In")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")
        if st.button("Log In", type="primary"):
            if not login_email or not login_password:
                st.error("Enter your email and password.")
            else:
                db = get_db_session()
                try:
                    user = authenticate_user(db, login_email, login_password)
                    if user:
                        set_current_user({
                            "id": user.id,
                            "email": user.email,
                            "free": user.free_downloads_remaining,
                            "paid": user.paid_credits,
                        })
                        st.success("Logged in.")
                        st.experimental_rerun()
                    else:
                        st.error("Invalid credentials.")
                finally:
                    db.close()

    with tabs[1]:
        st.subheader("Register")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        if st.button("Create Account", key="register_btn"):
            if not reg_email or not reg_password:
                st.error("Enter email and password.")
            else:
                try:
                    validate_email(reg_email)
                except EmailNotValidError:
                    st.error("Invalid email address.")
                else:
                    db = get_db_session()
                    try:
                        user = create_user(db, reg_email, reg_password)
                        set_current_user({
                            "id": user.id,
                            "email": user.email,
                            "free": user.free_downloads_remaining,
                            "paid": user.paid_credits,
                        })
                        st.success("Account created and logged in.")
                        st.experimental_rerun()
                    except ValueError as exc:
                        st.error(str(exc))
                    finally:
                        db.close()


def refresh_user_state():
    # Reload user counters into session state
    current = get_current_user()
    if not current:
        return
    db = get_db_session()
    try:
        user = get_user_by_email(db, current["email"])
        if user:
            set_current_user({
                "id": user.id,
                "email": user.email,
                "free": user.free_downloads_remaining,
                "paid": user.paid_credits,
            })
    finally:
        db.close()


# Sidebar: account info and purchase
with st.sidebar:
    st.title("Account")
    user = get_current_user()

    # Stripe success/cancel handling via query params
    try:
        qp = st.query_params
        qp_dict = dict(qp)
    except Exception:
        qp_dict = st.experimental_get_query_params()

    if qp_dict.get("session_id") and user:
        session_id = qp_dict.get("session_id")
        ok, msg = verify_and_apply_credits(session_id, user_id=user["id"])
        if ok:
            st.success("Payment verified. Credits added.")
            try:
                st.query_params.clear()
            except Exception:
                st.experimental_set_query_params()
            refresh_user_state()
        else:
            st.warning(msg)

    if user:
        st.write(f"**Email:** {user['email']}")
        st.write(f"**Free downloads left:** {user['free']}")
        st.write(f"**Paid credits:** {user['paid']}")

        # Purchase credits via Stripe
        if st.button("Buy 100 credits — $10", use_container_width=True):
            checkout_url = create_checkout_session(user)
            if not checkout_url:
                st.error("Stripe is not configured. Set STRIPE_API_KEY and APP_BASE_URL.")
            else:
                st.link_button("Open Stripe Checkout", url=checkout_url, use_container_width=True)

        if st.button("Log out"):
            set_current_user(None)
            st.experimental_rerun()
    else:
        st.caption("Log in to track free downloads and credits.")
        handle_auth_ui()


# Main app UI
st.title(APP_TITLE)

col1, col2 = st.columns([2, 1])
with col1:
    hex_input = st.text_input("Enter HEX color", value="#FF5733", help="Format: #RRGGBB")
    orientation = st.selectbox("Orientation", ["Square", "Portrait", "Landscape"], index=0)
    export_format = st.selectbox("Export format", ["JPG", "PNG"], index=0)

    # Live preview
    try:
        normalized = normalize_hex(hex_input)
        preview_img = generate_swatch_image(normalized, orientation, text_overlay=True)
        st.image(preview_img, caption=f"Preview {normalized}", use_container_width=True)
    except Exception as exc:
        st.error(str(exc))
        preview_img = None

    # Download button gated by login and credits
    user = get_current_user()

    def can_download(u) -> tuple[bool, str]:
        if not u:
            return False, "Please log in to download."
        if (u.get("free", 0) + u.get("paid", 0)) <= 0:
            return False, "Out of downloads. Purchase more credits."
        return True, ""

    if preview_img is not None:
        allowed, reason = can_download(user)
        img_bytes = image_to_bytes(preview_img, export_format)
        filename = f"swatch_{normalize_hex(hex_input).lstrip('#')}_{orientation.lower()}.{export_format.lower()}"

        if allowed:
            clicked = st.download_button(
                label="Download swatch",
                data=img_bytes,
                file_name=filename,
                mime="image/png" if export_format.upper() == "PNG" else "image/jpeg",
                type="primary",
            )
            if clicked and user:
                db = get_db_session()
                try:
                    # Re-fetch persistent user and decrement
                    persistent = get_user_by_email(db, user["email"])
                    if persistent is not None:
                        decrement_download_credit(db, persistent)
                        # Update session counters immediately
                        refresh_user_state()
                        st.toast("Download counted. Enjoy!", icon="✅")
                except Exception:
                    st.error("Failed to decrement credit. Please contact support.")
                finally:
                    db.close()
        else:
            st.warning(reason)
            if st.button("Buy 100 credits — $10", key="buy_btn_main") and user:
                checkout_url = create_checkout_session(user)
                if checkout_url:
                    st.link_button("Open Stripe Checkout", url=checkout_url)
                else:
                    st.error("Stripe is not configured. Set STRIPE_API_KEY and APP_BASE_URL.")

with col2:
    st.markdown(
        """
        **How credits work**
        - First 10 downloads are free after creating an account.
        - When you run out, buy 100 downloads for $10 via Stripe.
        - Credits are deducted when you click Download.
        """
    )

st.caption("Built with Streamlit, Stripe, and Pillow.")