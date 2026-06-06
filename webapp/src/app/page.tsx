"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { createApiClient } from "../lib/api-client.mjs";
import type { PaginatedResponse, ShoppingRequest, Watchlist } from "../lib/types";

type Status = "idle" | "loading" | "submitting" | "confirming" | "updating" | "success" | "error";

const exampleText =
  "Хочу беговые кроссовки для ежедневных тренировок. Размер 41. Бюджет 150 евро.";

export default function Home() {
  const [text, setText] = useState(exampleText);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [request, setRequest] = useState<ShoppingRequest | null>(null);
  const [watchlist, setWatchlist] = useState<Watchlist | null>(null);
  const [recentRequests, setRecentRequests] = useState<ShoppingRequest[]>([]);
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);

  const api = useMemo(
    () =>
      createApiClient({
        baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/v1",
        accessToken: process.env.NEXT_PUBLIC_DEMO_ACCESS_TOKEN ?? "",
      }),
    [],
  );

  useEffect(() => {
    void refreshDashboard();
  }, []);

  async function refreshDashboard() {
    setStatus((current) => (current === "idle" ? "loading" : current));
    setError(null);

    try {
      const [requestsResponse, watchlistsResponse] = await Promise.all([
        api.listShoppingRequests({ limit: 5 }),
        api.listWatchlists({ limit: 5 }),
      ]);
      setRecentRequests((requestsResponse as PaginatedResponse<ShoppingRequest>).items);
      setWatchlists((watchlistsResponse as PaginatedResponse<Watchlist>).items);
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

    try {
      const created = (await api.createShoppingRequest(text)) as ShoppingRequest;
      setRequest(created);
      setStatus("success");
      await refreshDashboard();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось создать запрос.");
      setStatus("error");
    }
  }

  async function handleConfirmWatchlist() {
    if (!request) {
      return;
    }

    setStatus("confirming");
    setError(null);

    try {
      const created = (await api.confirmWatchlistFromShoppingRequest(request.id)) as Watchlist;
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
        await api.pauseWatchlist(watchlistId);
      } else if (action === "resume") {
        await api.resumeWatchlist(watchlistId);
      } else {
        await api.archiveWatchlist(watchlistId);
      }
      setStatus("success");
      await refreshDashboard();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось обновить список.");
      setStatus("error");
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
          <div className="status-pill">{statusLabel(status)}</div>
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
          <button type="submit" disabled={status === "submitting" || text.trim().length < 8}>
            {status === "submitting" ? "Создаю запрос..." : "Разобрать запрос"}
          </button>
        </form>

        {error ? <p className="error-text">{error}</p> : null}
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
            disabled={status === "confirming"}
          >
            {status === "confirming" ? "Создаю список..." : "Подтвердить список"}
          </button>
        ) : null}

        {watchlist ? (
          <p className="success-text">
            Список создан: {watchlist.id.slice(0, 8)}. Уведомления будут приходить в Telegram.
          </p>
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

function statusLabel(status: Status) {
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
