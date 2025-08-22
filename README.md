# 🎨 Swatch Generator (Streamlit)

Generate clean color swatches from HEX codes with live preview. Includes login, 10 free downloads, credit-based downloads, and Stripe checkout for paid credits.

## Features
- Email/password login
- 10 free downloads per account
- Buy 100 credits for $10 via Stripe Checkout (configurable)
- Enter HEX color (e.g. #FF5733) and preview live
- Orientations: Square (default), Portrait, Landscape
- Export formats: JPG (default) or PNG
- Download swatch image (credits decremented on download)

## Quickstart (Local)

1. Prereqs: Python 3.10+
2. Clone or open this project, then create a virtual environment:
```bash
python -m venv .venv && source .venv/bin/activate
```
3. Install dependencies:
```bash
python -m pip install -U pip
pip install -r requirements.txt
```
4. Configure environment (optional for Stripe):
```bash
cp .env.example .env
# edit .env with your values: STRIPE_API_KEY, APP_BASE_URL, etc.
```
5. Run the app:
```bash
streamlit run app.py
```
6. Open `http://localhost:8501` in your browser.

Notes:
- Without `STRIPE_API_KEY`, the app still works; purchase buttons will show a configuration warning.
- SQLite database is created at `/workspace/swatch.db` by default. Adjust in `db.py` if needed.

## Configuration
Environment variables (can be placed in `.env` and loaded with your shell):
- `STRIPE_API_KEY`: Your Stripe secret key (test or live)
- `APP_BASE_URL`: Public URL for your app (used by Stripe return URL). Example: `http://localhost:8501` locally, your deployed URL in prod.
- `CREDITS_PER_PURCHASE`: Credits added per successful purchase (default 100)
- `PRICE_USD_CENTS`: Price in cents (default 1000 = $10)

## Stripe Setup
- Create a Stripe account and get your Secret Key (`sk_test_...` for testing)
- No webhooks required. We use the success return URL and verify the Checkout Session by ID.
- Test cards: `4242 4242 4242 4242`, any future expiry, any CVC and ZIP.

## Deployment Plan
- Streamlit Community Cloud (free):
  - Push to GitHub
  - In Streamlit Cloud, deploy the repo
  - Set environment variables in the app settings (`STRIPE_API_KEY`, `APP_BASE_URL` matching the deployed URL)
- Railway / Render / Fly.io / Docker:
  - Create a service from this repo
  - Expose port 8501 and run: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
  - Set environment variables
  - Ensure persistent disk for SQLite or swap to a managed DB
- Optionally, add a custom domain and HTTPS via your platform

## Selling This Product
- Pricing: keep the 10 free downloads to reduce friction; sell 100 credits for $10. Offer higher tiers by adjusting env vars or adding more buttons.
- Payments: Use Stripe Checkout as implemented. For subscriptions or multiple packages, add more line items or Prices.
- Distribution:
  - Deploy to a stable host (Streamlit Cloud or a VPS)
  - Add a marketing landing page describing the tool and linking to the app
  - Share on Product Hunt, X, Reddit (/r/Design, /r/Colorized), Indie Hackers
  - Offer coupon codes in Stripe for promos
- Analytics & Feedback: Add Plausible/Google Analytics on the landing page; collect feedback with a simple form.
- Support: Add a support email in the sidebar or footer.

## Dev Notes
- Database models in `db.py`. Authentication uses `passlib[bcrypt]`.
- Payment helper in `payments.py`. No webhooks; we verify with the returned `session_id`.
- Image generation in `utils.py` using Pillow.
- Main app in `app.py`.

## Security & Hardening
- Always set a strong `STRIPE_API_KEY` and keep `.env` out of source control
- Consider moving to PostgreSQL for multi-instance deployments
- Add email verification or password reset flows for production use

Enjoy building! 🎉