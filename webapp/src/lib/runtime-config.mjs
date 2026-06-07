const DEFAULT_API_BASE_URL = "http://localhost:8000/v1";

export function getWebAppConfig(env = process.env) {
  const appEnv = env.NEXT_PUBLIC_APP_ENV || "local";
  return {
    appEnv,
    apiBaseUrl: env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL,
    demoAccessToken: env.NEXT_PUBLIC_DEMO_ACCESS_TOKEN || "",
  };
}

export function validateWebAppConfig(config) {
  const issues = [];
  let parsedApiUrl;
  try {
    parsedApiUrl = new URL(config.apiBaseUrl);
  } catch {
    issues.push("NEXT_PUBLIC_API_BASE_URL must be an absolute http(s) URL.");
  }

  if (
    parsedApiUrl &&
    !["http:", "https:"].includes(parsedApiUrl.protocol)
  ) {
    issues.push("NEXT_PUBLIC_API_BASE_URL must be an absolute http(s) URL.");
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
