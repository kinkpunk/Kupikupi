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
    supportContactUrl: "",
    privacyPolicyUrl: "",
    termsUrl: "",
  });
});

test("validateWebAppConfig accepts local localhost API", () => {
  const issues = validateWebAppConfig({
    appEnv: "local",
    apiBaseUrl: "http://localhost:8000/v1",
    demoAccessToken: "demo-token",
    supportContactUrl: "mailto:support@example.test",
    privacyPolicyUrl: "https://app.example.test/privacy",
    termsUrl: "https://app.example.test/terms",
  });

  assert.deepEqual(issues, []);
});

test("validateWebAppConfig rejects invalid API URL", () => {
  const issues = validateWebAppConfig({
    appEnv: "local",
    apiBaseUrl: "/v1",
    demoAccessToken: "",
    supportContactUrl: "",
    privacyPolicyUrl: "",
    termsUrl: "",
  });

  assert.deepEqual(issues, ["NEXT_PUBLIC_API_BASE_URL must be an absolute http(s) URL."]);
});

test("validateWebAppConfig rejects localhost API in production-like env", () => {
  const issues = validateWebAppConfig({
    appEnv: "production",
    apiBaseUrl: "http://localhost:8000/v1",
    demoAccessToken: "",
    supportContactUrl: "",
    privacyPolicyUrl: "",
    termsUrl: "",
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
    supportContactUrl: "",
    privacyPolicyUrl: "",
    termsUrl: "",
  });

  assert.deepEqual(issues, [
    "NEXT_PUBLIC_DEMO_ACCESS_TOKEN must not be set in production-like environments.",
  ]);
});

test("validateWebAppConfig rejects invalid public contact URLs", () => {
  const issues = validateWebAppConfig({
    appEnv: "local",
    apiBaseUrl: "http://localhost:8000/v1",
    demoAccessToken: "",
    supportContactUrl: "telegram-user",
    privacyPolicyUrl: "/privacy",
    termsUrl: "/terms",
  });

  assert.deepEqual(issues, [
    "NEXT_PUBLIC_SUPPORT_CONTACT_URL must be an absolute http(s) or mailto URL.",
    "NEXT_PUBLIC_PRIVACY_POLICY_URL must be an absolute http(s) or mailto URL.",
    "NEXT_PUBLIC_TERMS_URL must be an absolute http(s) or mailto URL.",
  ]);
});

test("isProductionLike recognizes production aliases", () => {
  assert.equal(isProductionLike("production"), true);
  assert.equal(isProductionLike("prod"), true);
  assert.equal(isProductionLike("staging"), true);
  assert.equal(isProductionLike("local"), false);
});
