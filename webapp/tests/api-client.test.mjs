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

test("refreshToken posts refresh token without bearer token", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, {
        access_token: "new-access-token",
        refresh_token: "new-refresh-token",
        token_type: "bearer",
        expires_in: 900,
      });
    },
  });

  const result = await client.refreshToken("refresh-token");

  assert.equal(result.access_token, "new-access-token");
  assert.equal(calls[0].url, "https://api.example.test/v1/auth/refresh");
  assert.equal(calls[0].init.method, "POST");
  assert.equal(calls[0].init.headers.Authorization, undefined);
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    refresh_token: "refresh-token",
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

test("listRecommendations gets request recommendations", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, { items: [{ id: "recommendation-1" }] });
    },
  });

  const result = await client.listRecommendations("request-1");

  assert.equal(result.items[0].id, "recommendation-1");
  assert.equal(
    calls[0].url,
    "https://api.example.test/v1/shopping-requests/request-1/recommendations",
  );
  assert.equal(calls[0].init.method, "GET");
});

test("listProductOffers gets offers with size and stock filters", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, { items: [{ id: "offer-1" }], total: 1 });
    },
  });

  const result = await client.listProductOffers("product-1", {
    size: "41",
    inStock: true,
  });

  assert.equal(result.items[0].id, "offer-1");
  assert.equal(
    calls[0].url,
    "https://api.example.test/v1/products/product-1/offers?size=41&in_stock=true",
  );
  assert.equal(calls[0].init.method, "GET");
});

test("getPriceHistory gets product price history period", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, {
        product_id: "product-1",
        period: "90d",
        points: [],
        analytics: { eur_min_90d: 120 },
      });
    },
  });

  const result = await client.getPriceHistory("product-1", { period: "90d" });

  assert.equal(result.analytics.eur_min_90d, 120);
  assert.equal(calls[0].url, "https://api.example.test/v1/price-history/product-1?period=90d");
  assert.equal(calls[0].init.method, "GET");
});

test("listNotifications gets paginated notifications", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, { items: [{ id: "notification-1" }], total: 1 });
    },
  });

  const result = await client.listNotifications({ limit: 5, offset: 10 });

  assert.equal(result.items[0].id, "notification-1");
  assert.equal(calls[0].url, "https://api.example.test/v1/notifications?limit=5&offset=10");
  assert.equal(calls[0].init.method, "GET");
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

test("listProductDuplicateCandidates gets admin candidate groups", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "admin-token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, {
        items: [{ normalized_identity: "gt 2000 13", products: [] }],
      });
    },
  });

  const result = await client.listProductDuplicateCandidates({ limit: 25 });

  assert.equal(result.items[0].normalized_identity, "gt 2000 13");
  assert.equal(
    calls[0].url,
    "https://api.example.test/v1/admin/product-duplicate-candidates?limit=25",
  );
  assert.equal(calls[0].init.method, "GET");
  assert.equal(calls[0].init.headers.Authorization, "Bearer admin-token");
});

test("mergeDuplicateProduct posts target product id", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "admin-token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, {
        source_product_id: "source-product",
        target_product_id: "target-product",
        source_product_deleted: true,
      });
    },
  });

  const result = await client.mergeDuplicateProduct("source-product", "target-product");

  assert.equal(result.source_product_deleted, true);
  assert.equal(
    calls[0].url,
    "https://api.example.test/v1/admin/products/source-product/merge",
  );
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    target_product_id: "target-product",
  });
});

test("admin operations client lists stores and source configs", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "admin-token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, { items: [] });
    },
  });

  await client.listStores();
  await client.listStoreSourceConfigs("store-1");

  assert.equal(calls[0].url, "https://api.example.test/v1/admin/stores");
  assert.equal(calls[0].init.method, "GET");
  assert.equal(
    calls[1].url,
    "https://api.example.test/v1/admin/stores/store-1/source-configs",
  );
  assert.equal(calls[1].init.method, "GET");
});

test("admin operations client creates and updates source configs", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "admin-token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, { id: "source-config-1" });
    },
  });

  await client.createStoreSourceConfig("store-1", {
    source_type: "http_json",
    endpoint_url: "https://store.example.test/feed.json",
    active: true,
    sync_interval_minutes: 360,
    settings: { items_path: "items" },
  });
  await client.updateSourceConfig("source-config-1", {
    active: false,
  });

  assert.equal(
    calls[0].url,
    "https://api.example.test/v1/admin/stores/store-1/source-configs",
  );
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    source_type: "http_json",
    endpoint_url: "https://store.example.test/feed.json",
    active: true,
    sync_interval_minutes: 360,
    settings: { items_path: "items" },
  });
  assert.equal(
    calls[1].url,
    "https://api.example.test/v1/admin/source-configs/source-config-1",
  );
  assert.equal(calls[1].init.method, "PATCH");
  assert.deepEqual(JSON.parse(calls[1].init.body), {
    active: false,
  });
});

test("admin operations client manages sync runs", async () => {
  const calls = [];
  const client = createApiClient({
    baseUrl: "https://api.example.test/v1",
    accessToken: "admin-token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, { items: [] });
    },
  });

  await client.listSyncRuns();
  await client.listSyncRunItems("sync-run-1");
  await client.triggerSourceConfigSync("source-config-1");

  assert.equal(calls[0].url, "https://api.example.test/v1/admin/sync-runs");
  assert.equal(calls[0].init.method, "GET");
  assert.equal(calls[1].url, "https://api.example.test/v1/admin/sync-runs/sync-run-1/items");
  assert.equal(calls[1].init.method, "GET");
  assert.equal(calls[2].url, "https://api.example.test/v1/admin/sync-runs");
  assert.equal(calls[2].init.method, "POST");
  assert.deepEqual(JSON.parse(calls[2].init.body), {
    source_config_id: "source-config-1",
  });
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
