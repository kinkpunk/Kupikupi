"use client";

import { FormEvent, useMemo, useState } from "react";
import { createApiClient } from "../lib/api-client.mjs";
import type { ShoppingRequest, Watchlist } from "../lib/types";

type Status = "idle" | "submitting" | "confirming" | "success" | "error";

const exampleText =
  "Хочу беговые кроссовки для ежедневных тренировок. Размер 41. Бюджет 150 евро.";

export default function Home() {
  const [text, setText] = useState(exampleText);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [request, setRequest] = useState<ShoppingRequest | null>(null);
  const [watchlist, setWatchlist] = useState<Watchlist | null>(null);

  const api = useMemo(
    () =>
      createApiClient({
        baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/v1",
        accessToken: process.env.NEXT_PUBLIC_DEMO_ACCESS_TOKEN ?? "",
      }),
    [],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("submitting");
    setError(null);
    setWatchlist(null);

    try {
      const created = (await api.createShoppingRequest(text)) as ShoppingRequest;
      setRequest(created);
      setStatus("success");
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
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось подтвердить список.");
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

function statusLabel(status: Status) {
  if (status === "submitting") {
    return "Разбор";
  }
  if (status === "confirming") {
    return "Подтверждение";
  }
  if (status === "error") {
    return "Ошибка";
  }
  if (status === "success") {
    return "Готово";
  }
  return "MVP";
}
