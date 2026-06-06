import assert from "node:assert/strict";
import test from "node:test";

import { ApiError, createApiClient } from "../src/lib/api-client.mjs";

test("createShoppingRequest posts text without creating watchlist", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1/",
    accessToken: "token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(201, { id: "request-1", status: "parsed" });
    },
  });

  const result = await client.createShoppingRequest("Хочу кроссовки");

  assert.equal(result.id, "request-1");
  assert.equal(calls[0].url, "https://api.example.test/v1/shopping-requests");
  assert.equal(calls[0].init.method, "POST");
  assert.equal(calls[0].init.headers.Authorization, "Bearer token");
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    text: "Хочу кроссовки",
    create_watchlist_after_confirmation: false,
  });
});

test("authenticateTelegram posts init data without bearer token", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, {
        tokens: {
          access_token: "access-token",
          refresh_token: "refresh-token",
          token_type: "bearer",
          expires_in: 900,
        },
      });
    },
  });

  const result = await client.authenticateTelegram("query_id=abc");

  assert.equal(result.tokens.access_token, "access-token");
  assert.equal(calls[0].url, "https://api.example.test/v1/auth/telegram");
  assert.equal(calls[0].init.method, "POST");
  assert.equal(calls[0].init.headers.Authorization, undefined);
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    init_data: "query_id=abc",
  });
});

test("confirmWatchlistFromShoppingRequest posts confirmation endpoint", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(201, { id: "watchlist-1", active: true });
    },
  });

  const result = await client.confirmWatchlistFromShoppingRequest("request-1");

  assert.equal(result.id, "watchlist-1");
  assert.equal(calls[0].url, "https://api.example.test/v1/shopping-requests/request-1/watchlist");
  assert.equal(calls[0].init.method, "POST");
});

test("listWatchlists includes paging and archived filter", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, { items: [], total: 0 });
    },
  });

  await client.listWatchlists({ limit: 5, offset: 10, archived: false });

  assert.equal(calls[0].url, "https://api.example.test/v1/watchlists?limit=5&offset=10&archived=false");
  assert.equal(calls[0].init.method, "GET");
});

test("pauseWatchlist posts pause endpoint", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, { id: "watchlist-1", active: false });
    },
  });

  const result = await client.pauseWatchlist("watchlist-1");

  assert.equal(result.id, "watchlist-1");
  assert.equal(calls[0].url, "https://api.example.test/v1/watchlists/watchlist-1/pause");
  assert.equal(calls[0].init.method, "POST");
});

test("resumeWatchlist puts active state", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, { id: "watchlist-1", active: true, archived: false });
    },
  });

  const result = await client.resumeWatchlist("watchlist-1");

  assert.equal(result.id, "watchlist-1");
  assert.equal(calls[0].url, "https://api.example.test/v1/watchlists/watchlist-1");
  assert.equal(calls[0].init.method, "PUT");
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    active: true,
    archived: false,
  });
});

test("archiveWatchlist posts archive endpoint", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, { id: "watchlist-1", archived: true });
    },
  });

  const result = await client.archiveWatchlist("watchlist-1");

  assert.equal(result.id, "watchlist-1");
  assert.equal(calls[0].url, "https://api.example.test/v1/watchlists/watchlist-1/archive");
  assert.equal(calls[0].init.method, "POST");
});

test("client requires access token", async () => {
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "",
    fetchImpl: async () => jsonResponse(200, {}),
  });

  await assert.rejects(() => client.listShoppingRequests(), {
    name: "ApiError",
    message: "Access token is not configured.",
  });
});

test("client raises ApiError for backend failures", async () => {
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "token",
    fetchImpl: async () => jsonResponse(401, { detail: "Unauthorized" }),
  });

  await assert.rejects(() => client.listShoppingRequests(), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 401);
    return true;
  });
});

function jsonResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() {
      return payload;
    },
  };
}
