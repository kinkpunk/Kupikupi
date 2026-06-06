import assert from "node:assert/strict";
import test from "node:test";

import {
  getTelegramInitData,
  loadStoredTokens,
  notifyTelegramReady,
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

function createMemoryStorage() {
  const values = new Map();
  return {
    getItem(key) {
      return values.get(key) ?? null;
    },
    setItem(key, value) {
      values.set(key, value);
    },
  };
}
