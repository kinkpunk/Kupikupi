# Closed-Test Support, Privacy, And Terms Checklist

Status date: 2026-06-17

Use this checklist before inviting closed Telegram testers. It is an operator checklist, not final
legal advice. Public beta still requires legal review and final hosted policy pages.

## Required Links

- Support contact: an operator-monitored `mailto:` or HTTPS support page.
- Privacy policy: a hosted draft based on `docs/privacy-data-retention.md`.
- Terms: a hosted closed-test terms page that explains the service is experimental and does not
  purchase products or process payments.

For the closed test, these can be draft pages as long as testers can open them from Telegram and
WebApp and the support contact is monitored.

## Environment Values

Set the same support, privacy, and terms URLs across backend-generated env templates, Telegram Bot,
WebApp, and operator smoke:

```text
SUPPORT_CONTACT_URL=mailto:support@example.test
PRIVACY_POLICY_URL=https://app.staging.kupikupi.example/privacy
TERMS_URL=https://app.staging.kupikupi.example/terms
NEXT_PUBLIC_SUPPORT_CONTACT_URL=mailto:support@example.test
NEXT_PUBLIC_PRIVACY_POLICY_URL=https://app.staging.kupikupi.example/privacy
NEXT_PUBLIC_TERMS_URL=https://app.staging.kupikupi.example/terms
KUPIKUPI_SUPPORT_URL=mailto:support@example.test
KUPIKUPI_PRIVACY_URL=https://app.staging.kupikupi.example/privacy
KUPIKUPI_TERMS_URL=https://app.staging.kupikupi.example/terms
```

## Validation

Run the staging preflight and remote smoke:

```bash
cd backend
python scripts/staging_preflight.py \
  --backend-env /tmp/kupikupi-staging-env/kupikupi-backend.env \
  --bot-env /tmp/kupikupi-staging-env/kupikupi-bot.env \
  --webapp-env /tmp/kupikupi-staging-env/kupikupi-webapp.env \
  --operator-env /tmp/kupikupi-staging-env/kupikupi-operator.env
python scripts/staging_smoke.py \
  --api-base-url "$KUPIKUPI_API_BASE_URL" \
  --webapp-url "$KUPIKUPI_WEBAPP_URL" \
  --support-url "$KUPIKUPI_SUPPORT_URL" \
  --privacy-url "$KUPIKUPI_PRIVACY_URL" \
  --terms-url "$KUPIKUPI_TERMS_URL"
```

Manual Telegram check:

1. Open `/privacy` in the staging bot.
2. Confirm Privacy, Terms, and support contact are visible.
3. Open the WebApp and confirm the footer links open the same destinations.
4. Send a test support email or message and confirm the operator receives it.

## Go Criteria

- Links are configured in Telegram Bot, WebApp, and operator smoke env.
- HTTP(S) links return a 2xx/3xx status; `mailto:` support links are intentionally accepted.
- The support mailbox/chat is monitored during the test window.
- The draft notice tells testers what data is stored and how to request deletion.

## Public Beta No-Go

Do not treat this checklist as public beta approval. Public beta still needs legal review, final
controller/operator identity, final retention language, and production-hosted privacy and terms URLs.
