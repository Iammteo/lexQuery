#!/usr/bin/env python3
"""
LexQuery Stripe Setup Script.

Run once from the lexquery root folder to create all products,
prices, and the webhook endpoint in your Stripe account.

Usage:
    cd /Users/olatuyole/Downloads/lexquery
    python3 stripe_setup.py
"""
import stripe
import json

STRIPE_SECRET_KEY = "sk_test_51SaqN02LJICSbPRmXYogMCN1qY8T7LdE6igDH1L1nhiLf1ryivPzwMQb4e5SruQR0KVa5glY595Romz3TdQ4l4KX009sWTwpuJ"
STRIPE_PUBLISHABLE_KEY = "pk_test_51SaqN02LJICSbPRmER8IZdj4DRpP8YKUi8sz3ve6Yb7wLoUBVDaacfWoFhT645jalNVOrVuoJV4DN89hsxwgelLZ00XdTU7bFq"

stripe.api_key = STRIPE_SECRET_KEY

PLANS = [
    {
        "key": "starter",
        "name": "LexQuery Starter",
        "description": "Up to 10 seats, 50,000 pages indexed, 5,000 queries/month",
        "amount": 80000,  # £800.00 in pence
        "trial_days": 14,
    },
    {
        "key": "professional",
        "name": "LexQuery Professional",
        "description": "Up to 100 seats, 500,000 pages indexed, 50,000 queries/month",
        "amount": 350000,  # £3,500.00 in pence
        "trial_days": 14,
    },
    {
        "key": "enterprise",
        "name": "LexQuery Enterprise",
        "description": "Unlimited seats and usage — custom pricing applied separately",
        "amount": 100,  # £1.00 placeholder
        "trial_days": 0,
    },
]

WEBHOOK_EVENTS = [
    "checkout.session.completed",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_failed",
    "customer.subscription.trial_will_end",
]


def create_products_and_prices():
    price_ids = {}
    print("\n📦 Creating products and prices...\n")

    for plan in PLANS:
        # Check if product already exists
        existing = stripe.Product.search(query=f"metadata['lexquery_plan']:'{plan['key']}'")
        if existing.data:
            product = existing.data[0]
            print(f"  ↩  {plan['name']} already exists — skipping product creation")
        else:
            product = stripe.Product.create(
                name=plan["name"],
                description=plan["description"],
                metadata={"lexquery_plan": plan["key"]},
            )
            print(f"  ✓  Created product: {plan['name']}")

        # Check if price already exists for this product
        existing_prices = stripe.Price.list(product=product.id, active=True)
        if existing_prices.data:
            price = existing_prices.data[0]
            print(f"  ↩  Price already exists for {plan['name']} — skipping")
        else:
            price_data = {
                "product": product.id,
                "unit_amount": plan["amount"],
                "currency": "gbp",
                "recurring": {"interval": "month"},
                "metadata": {"lexquery_plan": plan["key"]},
            }
            price = stripe.Price.create(**price_data)
            amount_gbp = plan["amount"] / 100
            print(f"  ✓  Created price: £{amount_gbp:,.2f}/month")

        price_ids[plan["key"]] = price.id

    return price_ids


def create_webhook():
    print("\n🔗 Creating webhook endpoint...\n")

    # Check if webhook already exists
    existing = stripe.WebhookEndpoint.list()
    for wh in existing.data:
        if "localhost:8000/v1/billing/webhook" in wh.url:
            print(f"  ↩  Webhook already exists — {wh.url}")
            print(f"  ⚠  Cannot retrieve existing webhook secret.")
            print(f"     Go to dashboard.stripe.com/webhooks to copy the signing secret.")
            return None

    webhook = stripe.WebhookEndpoint.create(
        url="http://localhost:8000/v1/billing/webhook",
        enabled_events=WEBHOOK_EVENTS,
        description="LexQuery local development webhook",
    )
    print(f"  ✓  Webhook created: {webhook.url}")
    return webhook.secret


def main():
    print("=" * 60)
    print("  LexQuery Stripe Setup")
    print("=" * 60)

    try:
        # Verify API key works
        account = stripe.Account.retrieve()
        print(f"\n✓ Connected to Stripe account: {account.get('email', account.id)}")
    except stripe.error.AuthenticationError:
        print("\n✗ Invalid Stripe secret key. Check STRIPE_SECRET_KEY.")
        return

    price_ids = create_products_and_prices()
    webhook_secret = create_webhook()

    print("\n" + "=" * 60)
    print("  ✅ Setup complete! Add these to backend/.env:")
    print("=" * 60)
    print(f"""
STRIPE_PUBLISHABLE_KEY={STRIPE_PUBLISHABLE_KEY}
STRIPE_SECRET_KEY={STRIPE_SECRET_KEY}
STRIPE_STARTER_PRICE_ID={price_ids.get('starter', 'ERROR')}
STRIPE_PROFESSIONAL_PRICE_ID={price_ids.get('professional', 'ERROR')}
STRIPE_ENTERPRISE_PRICE_ID={price_ids.get('enterprise', 'ERROR')}
STRIPE_WEBHOOK_SECRET={webhook_secret or 'COPY_FROM_STRIPE_DASHBOARD'}
STRIPE_TRIAL_DAYS=14
""")

    if not webhook_secret:
        print("⚠  The webhook signing secret could not be retrieved.")
        print("   Go to: https://dashboard.stripe.com/webhooks")
        print("   Click your webhook → Reveal signing secret → copy it")
        print("   Add it as STRIPE_WEBHOOK_SECRET= in backend/.env\n")


if __name__ == "__main__":
    main()
