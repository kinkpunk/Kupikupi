import assert from "node:assert/strict";
import test from "node:test";

import {
  getWebAppConfig,
  isProductionLike,
  validateWebAppConfig,
} from "../src/lib/runtime-config.mjs";

test("getWebAppConfig returns local defaults", () => {
  const config = getWebAppConfig({});

  assert.deepEqual(config, {
    appEnv: "local",
    apiBaseUrl: "http://localhost:8000/v1",
    demoAccessToken: "",
  });
});

test("validateWebAppConfig accepts local localhost API", () => {
  const issues = validateWebAppConfig({
    appEnv: "local",
    apiBaseUrl: "http://localhost:8000/v1",
    demoAccessToken: "demo-token",
  });

  assert.deepEqual(issues, []);
});

test("validateWebAppConfig rejects invalid API URL", () => {
  const issues = validateWebAppConfig({
    appEnv: "local",
    apiBaseUrl: "/v1",
    demoAccessToken: "",
  });

  assert.deepEqual(issues, ["NEXT_PUBLIC_API_BASE_URL must be an absolute http(s) URL."]);
});

test("validateWebAppConfig rejects localhost API in production-like env", () => {
  const issues = validateWebAppConfig({
    appEnv: "production",
    apiBaseUrl: "http://localhost:8000/v1",
    demoAccessToken: "",
  });

  assert.deepEqual(issues, [
    "NEXT_PUBLIC_API_BASE_URL must not point to localhost in production-like environments.",
  ]);
});

test("validateWebAppConfig rejects demo token in production-like env", () => {
  const issues = validateWebAppConfig({
    appEnv: "staging",
    apiBaseUrl: "https://api.example.test/v1",
    demoAccessToken: "demo-token",
  });

  assert.deepEqual(issues, [
    "NEXT_PUBLIC_DEMO_ACCESS_TOKEN must not be set in production-like environments.",
  ]);
});

test("isProductionLike recognizes production aliases", () => {
  assert.equal(isProductionLike("production"), true);
  assert.equal(isProductionLike("prod"), true);
  assert.equal(isProductionLike("staging"), true);
  assert.equal(isProductionLike("local"), false);
});
