export class ApiError extends Error {
  constructor(message, { status } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * @typedef {object} ApiClientOptions
 * @property {string} baseUrl
 * @property {string} [accessToken]
 * @property {() => string} [getAccessToken]
 * @property {typeof fetch} [fetchImpl]
 */

/**
 * @param {ApiClientOptions} options
 */
export function createApiClient({ baseUrl, accessToken, getAccessToken, fetchImpl = fetch }) {
  const normalizedBaseUrl = baseUrl.replace(/\/+$/, "");

  function resolveAccessToken() {
    if (typeof getAccessToken === "function") {
      return getAccessToken();
    }
    return accessToken;
  }

  async function request(path, { method = "GET", body } = {}) {
    const token = resolveAccessToken();
    if (!token) {
      throw new ApiError("Access token is not configured.");
    }

    const response = await fetchImpl(`${normalizedBaseUrl}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });

    if (!response.ok) {
      throw new ApiError(`Backend returned ${response.status}.`, {
        status: response.status,
      });
    }

    if (response.status === 204) {
      return null;
    }

    return response.json();
  }

  return {
    authenticateTelegram(initData) {
      return authRequest("/auth/telegram", {
        init_data: initData,
      });
    },
    refreshToken(refreshToken) {
      return authRequest("/auth/refresh", {
        refresh_token: refreshToken,
      });
    },
    createShoppingRequest(text) {
      return request("/shopping-requests", {
        method: "POST",
        body: {
          text,
          create_watchlist_after_confirmation: false,
        },
      });
    },
    confirmWatchlistFromShoppingRequest(requestId) {
      return request(`/shopping-requests/${requestId}/watchlist`, {
        method: "POST",
      });
    },
    listRecommendations(requestId) {
      return request(`/shopping-requests/${requestId}/recommendations`);
    },
    /**
     * @param {string} productId
     * @param {{ size?: string; inStock?: boolean }} [options]
     */
    listProductOffers(productId, { size, inStock = true } = {}) {
      const params = new URLSearchParams();
      if (size) {
        params.set("size", size);
      }
      if (inStock !== undefined) {
        params.set("in_stock", String(inStock));
      }
      const query = params.toString();
      return request(`/products/${productId}/offers${query ? `?${query}` : ""}`);
    },
    getPriceHistory(productId, { period = "90d" } = {}) {
      const params = new URLSearchParams({ period });
      return request(`/price-history/${productId}?${params.toString()}`);
    },
    listNotifications({ limit = 5, offset = 0 } = {}) {
      const params = new URLSearchParams({
        limit: String(limit),
        offset: String(offset),
      });
      return request(`/notifications?${params.toString()}`);
    },
    listShoppingRequests({ limit = 10, offset = 0 } = {}) {
      const params = new URLSearchParams({
        limit: String(limit),
        offset: String(offset),
      });
      return request(`/shopping-requests?${params.toString()}`);
    },
    listWatchlists({ limit = 10, offset = 0, archived = false } = {}) {
      const params = new URLSearchParams({
        limit: String(limit),
        offset: String(offset),
        archived: String(archived),
      });
      return request(`/watchlists?${params.toString()}`);
    },
    pauseWatchlist(watchlistId) {
      return request(`/watchlists/${watchlistId}/pause`, {
        method: "POST",
      });
    },
    resumeWatchlist(watchlistId) {
      return request(`/watchlists/${watchlistId}`, {
        method: "PUT",
        body: {
          active: true,
          archived: false,
        },
      });
    },
    archiveWatchlist(watchlistId) {
      return request(`/watchlists/${watchlistId}/archive`, {
        method: "POST",
      });
    },
    listProductDuplicateCandidates({ limit = 50 } = {}) {
      const params = new URLSearchParams({
        limit: String(limit),
      });
      return request(`/admin/product-duplicate-candidates?${params.toString()}`);
    },
    mergeDuplicateProduct(sourceProductId, targetProductId) {
      return request(`/admin/products/${sourceProductId}/merge`, {
        method: "POST",
        body: {
          target_product_id: targetProductId,
        },
      });
    },
  };

  async function authRequest(path, body) {
    const response = await fetchImpl(`${normalizedBaseUrl}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new ApiError(`Backend returned ${response.status}.`, {
        status: response.status,
      });
    }

    return response.json();
  }
}
