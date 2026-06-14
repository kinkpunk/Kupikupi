"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { createApiClient } from "../lib/api-client.mjs";
import { getWebAppConfig, validateWebAppConfig } from "../lib/runtime-config.mjs";
import {
  clearStoredTokens,
  getShoppingRequestId,
  getTelegramInitData,
  loadStoredTokens,
  notifyTelegramReady,
  resolveInitialAuthSource,
  storeTokens,
} from "../lib/telegram-webapp.mjs";
import type {
  AuthResponse,
  Category,
  Notification,
  Offer,
  PaginatedResponse,
  PriceHistory,
  Recommendation,
  ShoppingRequest,
  ShoppingRequestConstraintDraft,
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

type EditMode = "text" | "constraints" | null;

const exampleText =
  "I need waterproof trail running shoes for muddy weekend runs, EU size 42, under 170 EUR.";
const webAppConfig = getWebAppConfig();
const apiBaseUrl = webAppConfig.apiBaseUrl;
const supportContactUrl = webAppConfig.supportContactUrl;
const privacyPolicyUrl = webAppConfig.privacyPolicyUrl;
const termsUrl = webAppConfig.termsUrl;
const emptyConstraintDraft: ShoppingRequestConstraintDraft = {
  category: "",
  use_case: "",
  size_value: "",
  size_system: "",
  preferred_brand: "",
  color: "",
  max_price: "",
  max_price_currency: "EUR",
};

export default function Home() {
  const [text, setText] = useState(exampleText);
  const [status, setStatus] = useState<Status>("authenticating");
  const [error, setError] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState("");
  const [refreshToken, setRefreshToken] = useState("");
  const [authMode, setAuthMode] = useState<"telegram" | "demo" | "stored" | "missing">("missing");
  const [request, setRequest] = useState<ShoppingRequest | null>(null);
  const [editMode, setEditMode] = useState<EditMode>(null);
  const [constraintDraft, setConstraintDraft] =
    useState<ShoppingRequestConstraintDraft>(emptyConstraintDraft);
  const [categories, setCategories] = useState<Category[]>([]);
  const [watchlist, setWatchlist] = useState<Watchlist | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [offersByProduct, setOffersByProduct] = useState<Record<string, Offer[]>>({});
  const [priceHistoryByProduct, setPriceHistoryByProduct] = useState<Record<string, PriceHistory>>({});
  const [recentRequests, setRecentRequests] = useState<ShoppingRequest[]>([]);
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [archivedWatchlists, setArchivedWatchlists] = useState<Watchlist[]>([]);
  const [watchlistView, setWatchlistView] = useState<"active" | "archived">("active");
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
      const requestId = getShoppingRequestId();
      if (requestId) {
        void loadShoppingRequest(requestId);
      }
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
      const [
        requestsResponse,
        watchlistsResponse,
        archivedWatchlistsResponse,
        notificationsResponse,
        categoriesResponse,
      ] = await Promise.all([
        withAuthRetry((client) => client.listShoppingRequests({ limit: 5 })),
        withAuthRetry((client) => client.listWatchlists({ limit: 5 })),
        withAuthRetry((client) => client.listWatchlists({ limit: 20, archived: true })),
        withAuthRetry((client) => client.listNotifications({ limit: 5 })),
        withAuthRetry((client) => client.listCategories()),
      ]);
      setRecentRequests((requestsResponse as PaginatedResponse<ShoppingRequest>).items);
      setWatchlists((watchlistsResponse as PaginatedResponse<Watchlist>).items);
      setArchivedWatchlists(
        (archivedWatchlistsResponse as PaginatedResponse<Watchlist>).items,
      );
      setNotifications((notificationsResponse as PaginatedResponse<Notification>).items);
      setCategories(categoriesResponse as Category[]);
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
      const saved = (await withAuthRetry((client) =>
        request && editMode === "text"
          ? client.updateShoppingRequest(request.id, {
              text,
            })
          : client.createShoppingRequest(text),
      )) as ShoppingRequest;
      setRequest(saved);
      setConstraintDraft(constraintsToDraft(saved));
      setEditMode(null);
      await loadRecommendations(saved.id, saved.constraints?.size_value);
      setStatus("success");
      await refreshDashboard();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : editMode
            ? "Не удалось сохранить изменения."
            : "Не удалось создать запрос.",
      );
      setStatus("error");
    }
  }

  async function handleSaveConstraints() {
    if (!request || editMode !== "constraints") {
      return;
    }

    setStatus("submitting");
    setError(null);
    try {
      const saved = (await withAuthRetry((client) =>
        client.updateShoppingRequest(request.id, {
          text: request.raw_text,
          constraints: constraintDraftPayload(constraintDraft),
        }),
      )) as ShoppingRequest;
      setRequest(saved);
      setConstraintDraft(constraintsToDraft(saved));
      setEditMode(null);
      setRecommendations([]);
      setOffersByProduct({});
      setPriceHistoryByProduct({});
      await loadRecommendations(saved.id, saved.constraints?.size_value);
      setStatus("success");
      await refreshDashboard();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось сохранить параметры.");
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

  async function loadShoppingRequest(requestId: string) {
    setStatus("loading");
    setError(null);
    try {
      const selected = (await withAuthRetry((client) =>
        client.getShoppingRequest(requestId),
      )) as ShoppingRequest;
      setText(selected.raw_text);
      setRequest(selected);
      setConstraintDraft(constraintsToDraft(selected));
      setWatchlist(null);
      setEditMode(null);
      await loadRecommendations(selected.id, selected.constraints?.size_value);
      setStatus("idle");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось загрузить запрос.");
      setStatus("error");
    }
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

  function handleNewRequest() {
    setText(exampleText);
    setRequest(null);
    setWatchlist(null);
    setRecommendations([]);
    setOffersByProduct({});
    setPriceHistoryByProduct({});
    setEditMode(null);
    setConstraintDraft(emptyConstraintDraft);
  }

  function startEditingRequest(mode: Exclude<EditMode, null>) {
    if (!request?.editable) {
      return;
    }
    setConstraintDraft(constraintsToDraft(request));
    setEditMode(mode);
  }

  function updateConstraintDraft(
    field: keyof ShoppingRequestConstraintDraft,
    value: string,
  ) {
    setConstraintDraft((current) => ({ ...current, [field]: value }));
  }

  async function handleWatchlistAction(
    action: "pause" | "resume" | "archive" | "restore",
    watchlistId: string,
  ) {
    setStatus("updating");
    setError(null);

    try {
      if (action === "pause") {
        await withAuthRetry((client) => client.pauseWatchlist(watchlistId));
      } else if (action === "resume") {
        await withAuthRetry((client) => client.resumeWatchlist(watchlistId));
      } else if (action === "restore") {
        await withAuthRetry((client) => client.restoreWatchlist(watchlistId));
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

        <form className="request-form" id="request-form" onSubmit={handleSubmit}>
          <label htmlFor="request-text">Что ищем</label>
          <textarea
            id="request-text"
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={5}
            placeholder={exampleText}
            readOnly={Boolean(request) && editMode !== "text"}
            disabled={editMode === "constraints"}
          />
          <div className="form-actions">
            {request && editMode === null && request.editable ? (
              <button
                className="muted-button"
                type="button"
                onClick={() => startEditingRequest("text")}
              >
                Редактировать запрос
              </button>
            ) : !request || editMode === "text" ? (
              <button
                type="submit"
                disabled={!accessToken || status === "submitting" || text.trim().length < 8}
              >
                {status === "submitting"
                  ? "Сохраняю..."
                  : editMode === "text"
                    ? "Сохранить запрос"
                    : "Разобрать запрос"}
              </button>
            ) : null}
            {request ? (
              <button
                className="text-button"
                type="button"
                onClick={handleNewRequest}
                disabled={editMode === "constraints"}
              >
                Новый запрос
              </button>
            ) : null}
          </div>
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

        {request && editMode === "constraints" ? (
          <div className="constraint-editor">
            <label>
              Категория
              <select
                value={constraintDraft.category}
                onChange={(event) =>
                  updateConstraintDraft("category", event.target.value)
                }
              >
                <option value="">Не выбрана</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.slug}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Назначение
              <input
                value={constraintDraft.use_case}
                onChange={(event) =>
                  updateConstraintDraft("use_case", event.target.value)
                }
                placeholder="daily training"
              />
            </label>
            <div className="constraint-row">
              <label>
                Размер
                <input
                  value={constraintDraft.size_value}
                  onChange={(event) =>
                    updateConstraintDraft("size_value", event.target.value)
                  }
                  placeholder="42"
                />
              </label>
              <label>
                Система
                <select
                  value={constraintDraft.size_system}
                  onChange={(event) =>
                    updateConstraintDraft("size_system", event.target.value)
                  }
                >
                  <option value="">Не выбрана</option>
                  <option value="EU">EU</option>
                  <option value="US">US</option>
                  <option value="UK">UK</option>
                  <option value="INT">INT</option>
                </select>
              </label>
            </div>
            <div className="constraint-row">
              <label>
                Бренд
                <input
                  value={constraintDraft.preferred_brand}
                  onChange={(event) =>
                    updateConstraintDraft("preferred_brand", event.target.value)
                  }
                  placeholder="New Balance"
                />
              </label>
              <label>
                Цвет
                <input
                  value={constraintDraft.color}
                  onChange={(event) =>
                    updateConstraintDraft("color", event.target.value)
                  }
                  placeholder="green"
                />
              </label>
            </div>
            <div className="constraint-row">
              <label>
                Бюджет
                <input
                  min="0"
                  step="0.01"
                  type="number"
                  value={constraintDraft.max_price}
                  onChange={(event) =>
                    updateConstraintDraft("max_price", event.target.value)
                  }
                />
              </label>
              <label>
                Валюта
                <select
                  value={constraintDraft.max_price_currency}
                  onChange={(event) =>
                    updateConstraintDraft("max_price_currency", event.target.value)
                  }
                >
                  <option value="EUR">EUR</option>
                  <option value="CZK">CZK</option>
                  <option value="USD">USD</option>
                  <option value="GBP">GBP</option>
                </select>
              </label>
            </div>
            <button
              type="button"
              onClick={handleSaveConstraints}
              disabled={status === "submitting" || text.trim().length < 8}
            >
              {status === "submitting" ? "Сохраняю..." : "Сохранить параметры"}
            </button>
          </div>
        ) : request ? (
          <div className="summary-grid">
            <SummaryItem label="Статус" value={request.status} />
            <SummaryItem label="Категория" value={constraints?.category} />
            <SummaryItem label="Назначение" value={constraints?.use_case} />
            <SummaryItem label="Размер" value={constraints?.size_value} />
            <SummaryItem
              label="Бюджет"
              value={formatMoney(request.budget_amount, request.display_currency)}
            />
            {request.editable && !watchlist ? (
              <button
                className="small-button muted-button summary-edit-button"
                type="button"
                onClick={() => startEditingRequest("constraints")}
              >
                Изменить параметры
              </button>
            ) : null}
          </div>
        ) : (
          <p className="empty-state">Отправь запрос, чтобы увидеть распознанные параметры.</p>
        )}

        {request && request.editable && !watchlist && editMode === null ? (
          <button
            className="secondary-button"
            type="button"
            onClick={handleConfirmWatchlist}
            disabled={!accessToken || status === "confirming"}
          >
            {status === "confirming" ? "Создаю список..." : "Подтвердить список"}
          </button>
        ) : null}

        {request && !request.editable ? (
          <p className="locked-text">
            Запрос уже подтвержден и используется активной или архивной позицией.
          </p>
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
                  <button
                    className="small-button muted-button"
                    type="button"
                    onClick={() => void loadShoppingRequest(item.id)}
                  >
                    Открыть
                  </button>
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
            <h2>Позиции</h2>
            <p>Управление позициями для поиска выгодных предложений.</p>
          </div>
          <div className="segmented-control" aria-label="Фильтр списков">
            <button
              className={watchlistView === "active" ? "selected" : ""}
              type="button"
              onClick={() => setWatchlistView("active")}
            >
              Активные позиции {watchlists.length}
            </button>
            <button
              className={watchlistView === "archived" ? "selected" : ""}
              type="button"
              onClick={() => setWatchlistView("archived")}
            >
              Архив {archivedWatchlists.length}
            </button>
          </div>
          {watchlistView === "active" && watchlists.length > 0 ? (
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
          ) : watchlistView === "active" ? (
            <p className="empty-state">Активных позиций пока нет.</p>
          ) : archivedWatchlists.length > 0 ? (
            <div className="list-stack">
              {archivedWatchlists.map((item) => (
                <article className="list-item watchlist-item" key={item.id}>
                  <div>
                    <strong>{watchlistTitle(item)}</strong>
                    <span>{watchlistDescription(item)}</span>
                  </div>
                  <button
                    className="small-button"
                    type="button"
                    onClick={() => handleWatchlistAction("restore", item.id)}
                    disabled={status === "updating"}
                  >
                    Восстановить
                  </button>
                </article>
              ))}
            </div>
          ) : (
            <p className="empty-state">Архив пуст.</p>
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

function constraintsToDraft(
  request: ShoppingRequest,
): ShoppingRequestConstraintDraft {
  const constraints = request.constraints;
  return {
    category: constraints?.category || "",
    use_case: constraints?.use_case || "",
    size_value: constraints?.size_value || "",
    size_system: constraints?.size_system || "",
    preferred_brand: constraints?.preferred_brand || "",
    color: constraints?.color || "",
    max_price:
      constraints?.max_price !== null && constraints?.max_price !== undefined
        ? String(constraints.max_price)
        : "",
    max_price_currency:
      constraints?.max_price_currency || request.display_currency || "EUR",
  };
}

function constraintDraftPayload(draft: ShoppingRequestConstraintDraft) {
  return {
    category: draft.category || null,
    use_case: draft.use_case || null,
    size_value: draft.size_value || null,
    size_system: draft.size_system || null,
    preferred_brand: draft.preferred_brand || null,
    color: draft.color || null,
    max_price: draft.max_price === "" ? null : Number(draft.max_price),
    max_price_currency: draft.max_price_currency || null,
  };
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
  return watchlist.category || watchlist.model || "Позиция";
}

function watchlistDescription(watchlist: Watchlist) {
  const parts = [
    `создана ${formatDate(watchlist.created_at)}`,
    watchlist.archived ? "архив" : watchlist.active ? "активна" : "пауза",
    watchlist.size_value ? `размер ${watchlist.size_value}` : null,
    formatMoney(watchlist.target_price, watchlist.target_price_currency),
  ].filter(Boolean);
  return parts.join(" · ");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
  }).format(new Date(value));
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
