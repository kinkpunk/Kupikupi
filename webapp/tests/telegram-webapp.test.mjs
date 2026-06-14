import assert from "node:assert/strict";
import test from "node:test";

import {
  clearStoredTokens,
  getShoppingRequestId,
  getTelegramInitData,
  loadStoredTokens,
  notifyTelegramReady,
  resolveInitialAuthSource,
  storeTokens,
} from "../src/lib/telegram-webapp.mjs";

test("stores and loads auth tokens", () => {
  const storage = createMemoryStorage();

  storeTokens(
    {
      access_token: "access-token",
      refresh_token: "refresh-token",
    },
    storage,
  );

  assert.deepEqual(loadStoredTokens(storage), {
    accessToken: "access-token",
    refreshToken: "refresh-token",
  });

  clearStoredTokens(storage);

  assert.deepEqual(loadStoredTokens(storage), {
    accessToken: "",
    refreshToken: "",
  });
});

test("reads Telegram initData from window", () => {
  global.window = {
    Telegram: {
      WebApp: {
        initData: "query_id=abc",
      },
    },
  };

  assert.equal(getTelegramInitData(), "query_id=abc");

  delete global.window;
});

test("notifyTelegramReady calls Telegram ready hook", () => {
  let readyCalled = false;
  global.window = {
    Telegram: {
      WebApp: {
        ready() {
          readyCalled = true;
        },
      },
    },
  };

  notifyTelegramReady();

  assert.equal(readyCalled, true);
  delete global.window;
});

test("reads shopping request id from WebApp URL", () => {
  assert.equal(
    getShoppingRequestId({ search: "?v=release&request_id=request-1" }),
    "request-1",
  );
});

test("resolveInitialAuthSource prefers Telegram initData over stored tokens and demo token", () => {
  const authSource = resolveInitialAuthSource({
    initData: "query_id=abc",
    storedTokens: {
      accessToken: "stored-access-token",
      refreshToken: "stored-refresh-token",
    },
    demoAccessToken: "demo-access-token",
  });

  assert.deepEqual(authSource, {
    mode: "telegram",
    initData: "query_id=abc",
  });
});

test("resolveInitialAuthSource uses stored tokens before local demo token", () => {
  const authSource = resolveInitialAuthSource({
    initData: "",
    storedTokens: {
      accessToken: "stored-access-token",
      refreshToken: "stored-refresh-token",
    },
    demoAccessToken: "demo-access-token",
  });

  assert.deepEqual(authSource, {
    mode: "stored",
    accessToken: "stored-access-token",
    refreshToken: "stored-refresh-token",
  });
});

test("resolveInitialAuthSource falls back to local demo token", () => {
  const authSource = resolveInitialAuthSource({
    initData: "",
    storedTokens: {
      accessToken: "",
      refreshToken: "",
    },
    demoAccessToken: "demo-access-token",
  });

  assert.deepEqual(authSource, {
    mode: "demo",
    accessToken: "demo-access-token",
    refreshToken: "",
  });
});

function createMemoryStorage() {
  const values = new Map();
  return {
    getItem(key) {
      return values.get(key) ?? null;
    },
    removeItem(key) {
      values.delete(key);
    },
    setItem(key, value) {
      values.set(key, value);
    },
  };
}
