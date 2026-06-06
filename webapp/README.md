# Kupikupi WebApp

Telegram WebApp frontend for Kupikupi.

The first iteration lets a user submit a shopping request, inspect deterministic parser output,
and explicitly confirm watchlist creation.

## Development

```bash
cd webapp
npm install
npm run dev
```

The app expects the backend API at `NEXT_PUBLIC_API_BASE_URL`.
For local MVP testing, set `NEXT_PUBLIC_DEMO_ACCESS_TOKEN` to a backend access token.

## Tests

```bash
npm test
```
