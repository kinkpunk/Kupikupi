export class ApiError extends Error {
  constructor(message, { status } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function createApiClient({ baseUrl, accessToken, fetchImpl = fetch }) {
  const normalizedBaseUrl = baseUrl.replace(/\/+$/, "");

  async function request(path, { method = "GET", body } = {}) {
    if (!accessToken) {
      throw new ApiError("Access token is not configured.");
    }

    const response = await fetchImpl(`${normalizedBaseUrl}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${accessToken}`,
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
  };
}
