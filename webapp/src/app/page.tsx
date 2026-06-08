"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { createApiClient } from "../lib/api-client.mjs";
import { getWebAppConfig, validateWebAppConfig } from "../lib/runtime-config.mjs";
import {
  clearStoredTokens,
  getTelegramInitData,
  loadStoredTokens,
  notifyTelegramReady,
  resolveInitialAuthSource,
  storeTokens,
} from "../lib/telegram-webapp.mjs";
import type {
  AuthResponse,
  Notification,
  Offer,
  PaginatedResponse,
  PriceHistory,
  Recommendation,
  ShoppingRequest,
  Watchlist,
} from "../lib/types";

type Status =
  | "idle"
  | "authenticating"
  | "loading"
  | "submitting"
  | "confirming"
  | "updating"
  | "success"
  | "error";

const exampleText =
  "Хочу беговые кроссовки для ежедневных тренировок. Размер 41. Бюджет 150 евро.";
const webAppConfig = getWebAppConfig();
const apiBaseUrl = webAppConfig.apiBaseUrl;
const supportContactUrl = webAppConfig.supportContactUrl;
const privacyPolicyUrl = webAppConfig.privacyPolicyUrl;
const termsUrl = webAppConfig.termsUrl;

export default function Home() {
  const [text, setText] = useState(exampleText);
  const [status, setStatus] = useState<Status>("authenticating");
  const [error, setError] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState("");
  const [refreshToken, setRefreshToken] = useState("");
  const [authMode, setAuthMode] = useState<"telegram" | "demo" | "stored" | "missing">("missing");
  const [request, setRequest] = useState<ShoppingRequest | null>(null);
  const [watchlist, setWatchlist] = useState<Watchlist | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [offersByProduct, setOffersByProduct] = useState<Record<string, Offer[]>>({});
  const [priceHistoryByProduct, setPriceHistoryByProduct] = useState<Record<string, PriceHistory>>({});
  const [recentRequests, setRecentRequests] = useState<ShoppingRequest[]>([]);
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const demoAccessToken = webAppConfig.demoAccessToken;
  const api = useMemo(
    () =>
      createApiClient({
        baseUrl: apiBaseUrl,
        accessToken,
      }),
    [accessToken],
  );

  useEffect(() => {
    notifyTelegramReady();
    const configurationIssues = validateWebAppConfig(webAppConfig);
    if (configurationIssues.length > 0) {
      setAuthMode("missing");
      setError(configurationIssues.join(" "));
      setStatus("error");
      return;
    }

    const authSource = resolveInitialAuthSource({
      initData: getTelegramInitData(),
      storedTokens: loadStoredTokens(),
      demoAccessToken,
    });

    if (authSource.mode === "telegram") {
      void authenticateWithTelegram(authSource.initData);
      return;
    }

    if (authSource.mode === "stored") {
      setAccessToken(authSource.accessToken);
      setRefreshToken(authSource.refreshToken);
      setAuthMode("stored");
      setStatus("idle");
      return;
    }

    if (authSource.mode === "demo") {
      setAccessToken(authSource.accessToken);
      setRefreshToken(authSource.refreshToken);
      setAuthMode("demo");
      setStatus("idle");
      return;
    }

    setAuthMode("missing");
    setError("Открой WebApp из Telegram или укажи NEXT_PUBLIC_DEMO_ACCESS_TOKEN для локального теста.");
    setStatus("error");
  }, []);

  useEffect(() => {
    if (accessToken) {
      void refreshDashboard();
    }
  }, [accessToken]);

  async function authenticateWithTelegram(initData: string) {
    setStatus("authenticating");
    setError(null);

    try {
      const authApi = createApiClient({
        baseUrl: apiBaseUrl,
        accessToken: "",
      });
      const response = (await authApi.authenticateTelegram(initData)) as AuthResponse;
      storeTokens(response.tokens);
      setAccessToken(response.tokens.access_token);
      setRefreshToken(response.tokens.refresh_token);
      setAuthMode("telegram");
      setStatus("idle");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось авторизоваться через Telegram.");
      setAuthMode("missing");
      setStatus("error");
    }
  }

  async function refreshDashboard() {
    if (!accessToken) {
      return;
    }

    setStatus((current) => (current === "idle" ? "loading" : current));
    setError(null);

    try {
      const [requestsResponse, watchlistsResponse, notificationsResponse] = await Promise.all([
        withAuthRetry((client) => client.listShoppingRequests({ limit: 5 })),
        withAuthRetry((client) => client.listWatchlists({ limit: 5 })),
        withAuthRetry((client) => client.listNotifications({ limit: 5 })),
      ]);
      setRecentRequests((requestsResponse as PaginatedResponse<ShoppingRequest>).items);
      setWatchlists((watchlistsResponse as PaginatedResponse<Watchlist>).items);
      setNotifications((notificationsResponse as PaginatedResponse<Notification>).items);
      setStatus((current) => (current === "loading" ? "idle" : current));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось загрузить данные.");
      setStatus("error");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("submitting");
    setError(null);
    setWatchlist(null);
    setRecommendations([]);
    setOffersByProduct({});
    setPriceHistoryByProduct({});

    try {
      const created = (await withAuthRetry((client) => client.createShoppingRequest(text))) as ShoppingRequest;
      setRequest(created);
      await loadRecommendations(created.id, created.constraints?.size_value);
      setStatus("success");
      await refreshDashboard();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось создать запрос.");
      setStatus("error");
    }
  }

  async function loadRecommendations(requestId: string, size?: string | null) {
    const response = (await withAuthRetry((client) =>
      client.listRecommendations(requestId),
    )) as { items: Recommendation[] };
    setRecommendations(response.items);
    await Promise.all([
      loadRecommendationOffers(response.items, size),
      loadRecommendationPriceHistory(response.items),
    ]);
  }

  async function loadRecommendationOffers(items: Recommendation[], size?: string | null) {
    const offersEntries = await Promise.all(
      items.map(async (item) => {
        const response = (await withAuthRetry((client) =>
          client.listProductOffers(item.product.id, { size: size ?? undefined }),
        )) as PaginatedResponse<Offer>;
        return [item.product.id, response.items] as const;
      }),
    );
    setOffersByProduct(Object.fromEntries(offersEntries));
  }

  async function loadRecommendationPriceHistory(items: Recommendation[]) {
    const historyEntries = await Promise.all(
      items.map(async (item) => {
        const response = (await withAuthRetry((client) =>
          client.getPriceHistory(item.product.id, { period: "90d" }),
        )) as PriceHistory;
        return [item.product.id, response] as const;
      }),
    );
    setPriceHistoryByProduct(Object.fromEntries(historyEntries));
  }

  async function handleConfirmWatchlist() {
    if (!request) {
      return;
    }

    setStatus("confirming");
    setError(null);

    try {
      const created = (await withAuthRetry((client) =>
        client.confirmWatchlistFromShoppingRequest(request.id),
      )) as Watchlist;
      setWatchlist(created);
      setStatus("success");
      await refreshDashboard();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось подтвердить список.");
      setStatus("error");
    }
  }

  async function handleWatchlistAction(action: "pause" | "resume" | "archive", watchlistId: string) {
    setStatus("updating");
    setError(null);

    try {
      if (action === "pause") {
        await withAuthRetry((client) => client.pauseWatchlist(watchlistId));
      } else if (action === "resume") {
        await withAuthRetry((client) => client.resumeWatchlist(watchlistId));
      } else {
        await withAuthRetry((client) => client.archiveWatchlist(watchlistId));
      }
      setStatus("success");
      await refreshDashboard();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось обновить список.");
      setStatus("error");
    }
  }

  async function withAuthRetry<T>(
    operation: (client: ReturnType<typeof createApiClient>) => Promise<T>,
  ): Promise<T> {
    try {
      return await operation(api);
    } catch (caught) {
      if (!isUnauthorizedError(caught) || !refreshToken) {
        throw caught;
      }

      const authApi = createApiClient({
        baseUrl: apiBaseUrl,
        accessToken: "",
      });
      try {
        const tokens = await authApi.refreshToken(refreshToken);
        storeTokens(tokens);
        setAccessToken(tokens.access_token);
        setRefreshToken(tokens.refresh_token);
        setAuthMode("stored");
        const retryApi = createApiClient({
          baseUrl: apiBaseUrl,
          accessToken: tokens.access_token,
        });
        return await operation(retryApi);
      } catch (refreshError) {
        clearStoredTokens();
        setAccessToken("");
        setRefreshToken("");
        setAuthMode("missing");
        throw refreshError;
      }
    }
  }

  const constraints = request?.constraints;

  return (
    <main className="app-shell">
      <section className="request-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">Kupikupi</p>
            <h1>Персональный агент покупок</h1>
          </div>
          <div className="status-stack">
            <div className="status-pill">{statusLabel(status)}</div>
            <span>{authModeLabel(authMode)}</span>
          </div>
        </header>

        <form className="request-form" onSubmit={handleSubmit}>
          <label htmlFor="request-text">Что ищем</label>
          <textarea
            id="request-text"
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={5}
            placeholder={exampleText}
          />
          <button
            type="submit"
            disabled={!accessToken || status === "submitting" || text.trim().length < 8}
          >
            {status === "submitting" ? "Создаю запрос..." : "Разобрать запрос"}
          </button>
        </form>

        {error ? <p className="error-text">{error}</p> : null}

        <footer className="trust-footer">
          <span>Закрытый тест Kupikupi</span>
          <div>
            {supportContactUrl ? (
              <a href={supportContactUrl} rel="noreferrer" target="_blank">
                Поддержка
              </a>
            ) : null}
            {privacyPolicyUrl ? (
              <a href={privacyPolicyUrl} rel="noreferrer" target="_blank">
                Privacy
              </a>
            ) : null}
            {termsUrl ? (
              <a href={termsUrl} rel="noreferrer" target="_blank">
                Terms
              </a>
            ) : null}
          </div>
        </footer>
      </section>

      <section className="result-panel">
        <div className="section-heading">
          <h2>Результат разбора</h2>
          <p>Список покупок создается только после подтверждения.</p>
        </div>

        {request ? (
          <div className="summary-grid">
            <SummaryItem label="Статус" value={request.status} />
            <SummaryItem label="Категория" value={constraints?.category} />
            <SummaryItem label="Назначение" value={constraints?.use_case} />
            <SummaryItem label="Размер" value={constraints?.size_value} />
            <SummaryItem
              label="Бюджет"
              value={formatMoney(request.budget_amount, request.display_currency)}
            />
          </div>
        ) : (
          <p className="empty-state">Отправь запрос, чтобы увидеть распознанные параметры.</p>
        )}

        {request && !watchlist ? (
          <button
            className="secondary-button"
            type="button"
            onClick={handleConfirmWatchlist}
            disabled={!accessToken || status === "confirming"}
          >
            {status === "confirming" ? "Создаю список..." : "Подтвердить список"}
          </button>
        ) : null}

        {watchlist ? (
          <p className="success-text">
            Список создан: {watchlist.id.slice(0, 8)}. Уведомления будут приходить в Telegram.
          </p>
        ) : null}

        {request ? (
          <section className="dashboard-section">
            <div className="section-heading compact-heading">
              <h2>Рекомендации</h2>
              <p>Подходящие модели по распознанным параметрам.</p>
            </div>
            {recommendations.length > 0 ? (
              <div className="list-stack">
                {recommendations.map((item) => (
                  <article className="recommendation-item" key={item.id}>
                    <div className="recommendation-content">
                      <div>
                        <strong>{item.product.name}</strong>
                        <span>{recommendationDescription(item)}</span>
                      </div>
                      <PriceHistorySummary history={priceHistoryByProduct[item.product.id]} />
                      <OfferList offers={offersByProduct[item.product.id] ?? []} />
                    </div>
                    <div className="score-pill">{formatScore(item.score)}</div>
                  </article>
                ))}
              </div>
            ) : (
              <p className="empty-state">Пока нет рекомендаций для этого запроса.</p>
            )}
          </section>
        ) : null}

        <section className="dashboard-section">
          <div className="section-heading compact-heading">
            <h2>Последние запросы</h2>
            <p>История того, что уже разобрал агент.</p>
          </div>
          {recentRequests.length > 0 ? (
            <div className="list-stack">
              {recentRequests.map((item) => (
                <article className="list-item" key={item.id}>
                  <div>
                    <strong>{item.raw_text}</strong>
                    <span>{requestDescription(item)}</span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="empty-state">Пока нет сохраненных запросов.</p>
          )}
        </section>

        <section className="dashboard-section">
          <div className="section-heading compact-heading">
            <h2>Уведомления</h2>
            <p>Последние сигналы, которые агент подготовил для Telegram.</p>
          </div>
          {notifications.length > 0 ? (
            <div className="list-stack">
              {notifications.map((item) => (
                <article className="notification-item" key={item.id}>
                  <div>
                    <strong>{notificationTitle(item)}</strong>
                    <span>{item.message}</span>
                  </div>
                  <span className="notification-time">{formatDateTime(item.sent_at || item.created_at)}</span>
                </article>
              ))}
            </div>
          ) : (
            <p className="empty-state">Уведомлений пока нет.</p>
          )}
        </section>

        <section className="dashboard-section">
          <div className="section-heading compact-heading">
            <h2>Активные списки</h2>
            <p>Управление списками покупок без выхода из WebApp.</p>
          </div>
          {watchlists.length > 0 ? (
            <div className="list-stack">
              {watchlists.map((item) => (
                <article className="list-item watchlist-item" key={item.id}>
                  <div>
                    <strong>{watchlistTitle(item)}</strong>
                    <span>{watchlistDescription(item)}</span>
                  </div>
                  <div className="button-row">
                    {item.active ? (
                      <button
                        className="small-button muted-button"
                        type="button"
                        onClick={() => handleWatchlistAction("pause", item.id)}
                        disabled={status === "updating"}
                      >
                        Пауза
                      </button>
                    ) : (
                      <button
                        className="small-button"
                        type="button"
                        onClick={() => handleWatchlistAction("resume", item.id)}
                        disabled={status === "updating"}
                      >
                        Возобновить
                      </button>
                    )}
                    <button
                      className="small-button danger-button"
                      type="button"
                      onClick={() => handleWatchlistAction("archive", item.id)}
                      disabled={status === "updating"}
                    >
                      Архив
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="empty-state">Активных списков пока нет.</p>
          )}
        </section>
      </section>
    </main>
  );
}

function SummaryItem({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="summary-item">
      <span>{label}</span>
      <strong>{value || "Не указано"}</strong>
    </div>
  );
}

function formatMoney(amount?: number | null, currency?: string | null) {
  if (!amount) {
    return null;
  }
  return `${amount.toLocaleString("ru-RU")} ${currency || "EUR"}`;
}

function requestDescription(request: ShoppingRequest) {
  const parts = [
    request.status,
    request.constraints?.category,
    request.constraints?.size_value ? `размер ${request.constraints.size_value}` : null,
    formatMoney(request.budget_amount, request.display_currency),
  ].filter(Boolean);
  return parts.join(" · ");
}

function recommendationDescription(recommendation: Recommendation) {
  const parts = [
    recommendation.product.model,
    recommendation.product.sku ? `SKU ${recommendation.product.sku}` : null,
    recommendation.reason,
  ].filter(Boolean);
  return parts.join(" · ");
}

function OfferList({ offers }: { offers: Offer[] }) {
  if (offers.length === 0) {
    return <span className="offer-empty">Предложений в наличии пока нет.</span>;
  }

  return (
    <div className="offer-stack">
      {offers.slice(0, 3).map((offer) => (
        <a
          className="offer-row"
          href={offer.product_url}
          key={offer.id}
          rel="noreferrer"
          target="_blank"
        >
          <span>{formatOfferPrice(offer)}</span>
          <strong>{offer.availability}</strong>
        </a>
      ))}
    </div>
  );
}

function PriceHistorySummary({ history }: { history?: PriceHistory }) {
  if (!history) {
    return <span className="price-history-empty">История цены загружается.</span>;
  }

  if (!history.analytics && history.points.length === 0) {
    return <span className="price-history-empty">Истории цены пока нет.</span>;
  }

  const analytics = history.analytics;
  return (
    <div className="price-history-row">
      <span>90 дней: {formatEur(analytics?.eur_min_90d)}</span>
      <span>Минимум: {formatEur(analytics?.eur_min_all_time)}</span>
      <span>{history.points.length} точек</span>
    </div>
  );
}

function formatOfferPrice(offer: Offer) {
  const sourcePrice = `${offer.source_price.toLocaleString("ru-RU")} ${offer.source_currency}`;
  if (offer.source_currency === "EUR") {
    return sourcePrice;
  }
  return `${sourcePrice} · ${offer.eur_price.toLocaleString("ru-RU")} EUR`;
}

function formatEur(amount?: number | null) {
  if (!amount) {
    return "нет данных";
  }
  return `${amount.toLocaleString("ru-RU")} EUR`;
}

function formatScore(score: number) {
  return score.toLocaleString("ru-RU", {
    maximumFractionDigits: 1,
    minimumFractionDigits: 0,
  });
}

function watchlistTitle(watchlist: Watchlist) {
  return watchlist.model || watchlist.category || watchlist.type;
}

function watchlistDescription(watchlist: Watchlist) {
  const parts = [
    watchlist.id.slice(0, 8),
    watchlist.active ? "активен" : "пауза",
    watchlist.size_value ? `размер ${watchlist.size_value}` : null,
    formatMoney(watchlist.target_price, watchlist.target_price_currency),
  ].filter(Boolean);
  return parts.join(" · ");
}

function notificationTitle(notification: Notification) {
  return `${notification.type} · ${notification.status}`;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusLabel(status: Status) {
  if (status === "authenticating") {
    return "Вход";
  }
  if (status === "loading") {
    return "Загрузка";
  }
  if (status === "submitting") {
    return "Разбор";
  }
  if (status === "confirming") {
    return "Подтверждение";
  }
  if (status === "updating") {
    return "Обновление";
  }
  if (status === "error") {
    return "Ошибка";
  }
  if (status === "success") {
    return "Готово";
  }
  return "MVP";
}

function authModeLabel(authMode: "telegram" | "demo" | "stored" | "missing") {
  if (authMode === "telegram") {
    return "Telegram";
  }
  if (authMode === "stored") {
    return "Сессия";
  }
  if (authMode === "demo") {
    return "Demo token";
  }
  return "Нет входа";
}

function isUnauthorizedError(error: unknown) {
  return error instanceof Error && "status" in error && error.status === 401;
}
