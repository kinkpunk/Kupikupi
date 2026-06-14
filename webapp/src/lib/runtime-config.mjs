const DEFAULT_API_BASE_URL = "http://localhost:8000/v1";

export function getWebAppConfig(env = getPublicEnvironment()) {
  const appEnv = env.NEXT_PUBLIC_APP_ENV || "local";
  return {
    appEnv,
    apiBaseUrl: env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL,
    demoAccessToken: env.NEXT_PUBLIC_DEMO_ACCESS_TOKEN || "",
    supportContactUrl: env.NEXT_PUBLIC_SUPPORT_CONTACT_URL || "",
    privacyPolicyUrl: env.NEXT_PUBLIC_PRIVACY_POLICY_URL || "",
    termsUrl: env.NEXT_PUBLIC_TERMS_URL || "",
  };
}

function getPublicEnvironment() {
  return {
    NEXT_PUBLIC_APP_ENV: process.env.NEXT_PUBLIC_APP_ENV,
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
    NEXT_PUBLIC_DEMO_ACCESS_TOKEN: process.env.NEXT_PUBLIC_DEMO_ACCESS_TOKEN,
    NEXT_PUBLIC_SUPPORT_CONTACT_URL: process.env.NEXT_PUBLIC_SUPPORT_CONTACT_URL,
    NEXT_PUBLIC_PRIVACY_POLICY_URL: process.env.NEXT_PUBLIC_PRIVACY_POLICY_URL,
    NEXT_PUBLIC_TERMS_URL: process.env.NEXT_PUBLIC_TERMS_URL,
  };
}

export function validateWebAppConfig(config) {
  const issues = [];
  let parsedApiUrl;
  const isSameOriginApiUrl = config.apiBaseUrl.startsWith("/");
  if (!isSameOriginApiUrl) {
    try {
      parsedApiUrl = new URL(config.apiBaseUrl);
    } catch {
      issues.push(
        "NEXT_PUBLIC_API_BASE_URL must be an absolute http(s) URL or root-relative path.",
      );
    }

    if (parsedApiUrl && !["http:", "https:"].includes(parsedApiUrl.protocol)) {
      issues.push(
        "NEXT_PUBLIC_API_BASE_URL must be an absolute http(s) URL or root-relative path.",
      );
    }
  }
  if (config.supportContactUrl && !isAllowedPublicUrl(config.supportContactUrl)) {
    issues.push("NEXT_PUBLIC_SUPPORT_CONTACT_URL must be an absolute http(s) or mailto URL.");
  }
  if (config.privacyPolicyUrl && !isAllowedPublicUrl(config.privacyPolicyUrl)) {
    issues.push("NEXT_PUBLIC_PRIVACY_POLICY_URL must be an absolute http(s) or mailto URL.");
  }
  if (config.termsUrl && !isAllowedPublicUrl(config.termsUrl)) {
    issues.push("NEXT_PUBLIC_TERMS_URL must be an absolute http(s) or mailto URL.");
  }

  if (isProductionLike(config.appEnv)) {
    const hostname = parsedApiUrl?.hostname;
    if (hostname === "localhost" || hostname === "127.0.0.1") {
      issues.push("NEXT_PUBLIC_API_BASE_URL must not point to localhost in production-like environments.");
    }
    if (config.demoAccessToken) {
      issues.push("NEXT_PUBLIC_DEMO_ACCESS_TOKEN must not be set in production-like environments.");
    }
  }

  return issues;
}

export function isProductionLike(appEnv) {
  return ["production", "prod", "staging"].includes(String(appEnv).toLowerCase());
}

function isAllowedPublicUrl(value) {
  try {
    const parsed = new URL(value);
    return ["http:", "https:", "mailto:"].includes(parsed.protocol);
  } catch {
    return false;
  }
}
