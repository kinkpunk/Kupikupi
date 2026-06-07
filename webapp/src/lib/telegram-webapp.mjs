const ACCESS_TOKEN_KEY = "kupikupi.accessToken";
const REFRESH_TOKEN_KEY = "kupikupi.refreshToken";

export function getTelegramInitData() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.Telegram?.WebApp?.initData || "";
}

export function notifyTelegramReady() {
  if (typeof window === "undefined") {
    return;
  }
  window.Telegram?.WebApp?.ready?.();
}

export function resolveInitialAuthSource({ initData, storedTokens, demoAccessToken }) {
  if (initData) {
    return {
      mode: "telegram",
      initData,
    };
  }
  if (storedTokens?.accessToken) {
    return {
      mode: "stored",
      accessToken: storedTokens.accessToken,
      refreshToken: storedTokens.refreshToken || "",
    };
  }
  if (demoAccessToken) {
    return {
      mode: "demo",
      accessToken: demoAccessToken,
      refreshToken: "",
    };
  }
  return {
    mode: "missing",
  };
}

export function loadStoredTokens(storage = safeSessionStorage()) {
  if (!storage) {
    return { accessToken: "", refreshToken: "" };
  }
  return {
    accessToken: storage.getItem(ACCESS_TOKEN_KEY) || "",
    refreshToken: storage.getItem(REFRESH_TOKEN_KEY) || "",
  };
}

export function storeTokens(tokens, storage = safeSessionStorage()) {
  if (!storage) {
    return;
  }
  storage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  storage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function clearStoredTokens(storage = safeSessionStorage()) {
  if (!storage) {
    return;
  }
  storage.removeItem(ACCESS_TOKEN_KEY);
  storage.removeItem(REFRESH_TOKEN_KEY);
}

function safeSessionStorage() {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage;
}
