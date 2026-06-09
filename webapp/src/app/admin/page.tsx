"use client";

import { FormEvent, useMemo, useState } from "react";
import { createApiClient } from "../../lib/api-client.mjs";
import { getWebAppConfig } from "../../lib/runtime-config.mjs";
import type {
  ProductDuplicateCandidateGroup,
  ProductMergeResult,
  SourceConfig,
  Store,
  SyncRun,
  SyncRunItem,
} from "../../lib/types";

type AdminStatus = "idle" | "loading" | "merging" | "syncing" | "success" | "error";

const adminTokenStorageKey = "kupikupi_admin_access_token";
const webAppConfig = getWebAppConfig();

export default function AdminPage() {
  const [adminToken, setAdminToken] = useState(() => loadAdminToken());
  const [status, setStatus] = useState<AdminStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [groups, setGroups] = useState<ProductDuplicateCandidateGroup[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [sourceConfigsByStore, setSourceConfigsByStore] = useState<Record<string, SourceConfig[]>>({});
  const [syncRuns, setSyncRuns] = useState<SyncRun[]>([]);
  const [syncItemsByRun, setSyncItemsByRun] = useState<Record<string, SyncRunItem[]>>({});
  const [targetsByGroup, setTargetsByGroup] = useState<Record<string, string>>({});
  const [lastMerge, setLastMerge] = useState<ProductMergeResult | null>(null);
  const [lastSyncRun, setLastSyncRun] = useState<SyncRun | null>(null);

  const api = useMemo(
    () =>
      createApiClient({
        baseUrl: webAppConfig.apiBaseUrl,
        accessToken: adminToken,
      }),
    [adminToken],
  );

  async function handleLoad(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setStatus("loading");
    setError(null);
    setLastMerge(null);
    setLastSyncRun(null);

    try {
      persistAdminToken(adminToken);
      const [duplicatesResponse, storesResponse, syncRunsResponse] = (await Promise.all([
        api.listProductDuplicateCandidates({ limit: 100 }),
        api.listStores(),
        api.listSyncRuns(),
      ])) as [
        { items: ProductDuplicateCandidateGroup[] },
        { items: Store[] },
        { items: SyncRun[] },
      ];
      const sourceConfigsEntries = await Promise.all(
        storesResponse.items.map(async (store) => {
          const response = (await api.listStoreSourceConfigs(store.id)) as {
            items: SourceConfig[];
          };
          return [store.id, response.items] as const;
        }),
      );
      setGroups(duplicatesResponse.items);
      setStores(storesResponse.items);
      setSourceConfigsByStore(Object.fromEntries(sourceConfigsEntries));
      setSyncRuns(syncRunsResponse.items);
      setTargetsByGroup(defaultTargets(duplicatesResponse.items));
      setStatus("success");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось загрузить данные оператора.");
      setStatus("error");
    }
  }

  async function handleMerge(group: ProductDuplicateCandidateGroup, sourceProductId: string) {
    const targetProductId = targetsByGroup[groupKey(group)];
    if (!targetProductId || sourceProductId === targetProductId) {
      return;
    }

    setStatus("merging");
    setError(null);

    try {
      const result = (await api.mergeDuplicateProduct(
        sourceProductId,
        targetProductId,
      )) as ProductMergeResult;
      setLastMerge(result);
      await handleLoad();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось объединить товары.");
      setStatus("error");
    }
  }

  async function handleTriggerSync(sourceConfigId: string) {
    setStatus("syncing");
    setError(null);
    setLastSyncRun(null);

    try {
      const syncRun = (await api.triggerSourceConfigSync(sourceConfigId)) as SyncRun;
      setLastSyncRun(syncRun);
      await handleLoad();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось запустить синхронизацию.");
      setStatus("error");
    }
  }

  async function handleLoadSyncRunItems(syncRunId: string) {
    setStatus("loading");
    setError(null);

    try {
      const response = (await api.listSyncRunItems(syncRunId)) as { items: SyncRunItem[] };
      setSyncItemsByRun((current) => ({
        ...current,
        [syncRunId]: response.items,
      }));
      setStatus("success");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось загрузить детали sync run.");
      setStatus("error");
    }
  }

  return (
    <main className="admin-shell">
      <header className="admin-hero">
        <div>
          <p className="eyebrow">Kupikupi Admin</p>
          <h1>Duplicate review</h1>
        </div>
        <div className="status-pill">{adminStatusLabel(status)}</div>
      </header>

      <form className="admin-token-form" onSubmit={handleLoad}>
        <label htmlFor="admin-token">Admin access token</label>
        <div>
          <input
            id="admin-token"
            autoComplete="off"
            spellCheck={false}
            type="password"
            value={adminToken}
            onChange={(event) => setAdminToken(event.target.value)}
            placeholder="Paste staging admin token"
          />
          <button type="submit" disabled={status === "loading" || adminToken.trim().length < 8}>
            {status === "loading" ? "Loading..." : "Load groups"}
          </button>
        </div>
      </form>

      {error ? <p className="error-text admin-alert">{error}</p> : null}
      {lastMerge ? (
        <p className="success-text admin-alert">
          Merged {shortId(lastMerge.source_product_id)} into {shortId(lastMerge.target_product_id)}.
        </p>
      ) : null}
      {lastSyncRun ? (
        <p className="success-text admin-alert">
          Sync run {shortId(lastSyncRun.id)} finished with {lastSyncRun.status}.
        </p>
      ) : null}

      <section className="admin-review-list">
        <div className="section-heading compact-heading">
          <h2>Stores and source configs</h2>
          <p>{stores.length} stores loaded for staging operations.</p>
        </div>

        {stores.length > 0 ? (
          <div className="list-stack">
            {stores.map((store) => (
              <article className="ops-group" key={store.id}>
                <div className="ops-group-header">
                  <div>
                    <strong>{store.name}</strong>
                    <span>
                      {store.country} · {store.active ? "active" : "inactive"} ·{" "}
                      {store.delivers_to_cz ? "CZ delivery" : "no CZ delivery"}
                    </span>
                  </div>
                  <a href={store.url} rel="noreferrer" target="_blank">
                    Store
                  </a>
                </div>

                {(sourceConfigsByStore[store.id] || []).length > 0 ? (
                  <div className="ops-table">
                    {(sourceConfigsByStore[store.id] || []).map((sourceConfig) => (
                      <div className="ops-row" key={sourceConfig.id}>
                        <div>
                          <strong>{sourceConfig.source_type}</strong>
                          <span>{sourceConfig.endpoint_url || "no endpoint url"}</span>
                        </div>
                        <span className={sourceConfig.active ? "state-pill" : "state-pill muted-state"}>
                          {sourceConfig.active ? "active" : "inactive"}
                        </span>
                        <span>{formatDateTime(sourceConfig.last_sync_at) || "never synced"}</span>
                        <button
                          className="small-button"
                          type="button"
                          disabled={!sourceConfig.active || status === "syncing"}
                          onClick={() => handleTriggerSync(sourceConfig.id)}
                        >
                          Sync
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="empty-state">No source configs for this store.</p>
                )}
              </article>
            ))}
          </div>
        ) : (
          <p className="empty-state">Load admin data to see stores and source configs.</p>
        )}
      </section>

      <section className="admin-review-list">
        <div className="section-heading compact-heading">
          <h2>Recent sync runs</h2>
          <p>{syncRuns.length} runs returned by the backend.</p>
        </div>

        {syncRuns.length > 0 ? (
          <div className="list-stack">
            {syncRuns.map((syncRun) => (
              <article className="ops-group" key={syncRun.id}>
                <div className="sync-run-row">
                  <div>
                    <strong>
                      {syncRun.source_type} · {syncRun.status}
                    </strong>
                    <span>
                      {syncRun.offers_seen} offers · {syncRun.products_seen} products ·{" "}
                      {syncRun.failed_offers} failed · {formatDateTime(syncRun.started_at)}
                    </span>
                    {syncRun.error_message ? <span>{syncRun.error_message}</span> : null}
                  </div>
                  <button
                    className="small-button muted-button"
                    type="button"
                    disabled={status === "loading"}
                    onClick={() => handleLoadSyncRunItems(syncRun.id)}
                  >
                    Items
                  </button>
                </div>

                {syncItemsByRun[syncRun.id] ? (
                  <div className="sync-items">
                    {syncItemsByRun[syncRun.id].length > 0 ? (
                      syncItemsByRun[syncRun.id].map((item) => (
                        <div className="sync-item" key={item.id}>
                          <strong>{item.external_id || shortId(item.id)}</strong>
                          <span>
                            {item.status}
                            {item.error_message ? ` · ${item.error_message}` : ""}
                          </span>
                        </div>
                      ))
                    ) : (
                      <p className="empty-state">No items recorded for this sync run.</p>
                    )}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        ) : (
          <p className="empty-state">Load admin data to see sync run history.</p>
        )}
      </section>

      <section className="admin-review-list">
        <div className="section-heading compact-heading">
          <h2>Candidate groups</h2>
          <p>{groups.length} groups need operator review.</p>
        </div>

        {groups.length > 0 ? (
          <div className="list-stack">
            {groups.map((group) => (
              <article className="duplicate-group" key={groupKey(group)}>
                <div className="duplicate-group-header">
                  <div>
                    <strong>{group.normalized_identity}</strong>
                    <span>
                      {group.products.length} products · category {shortId(group.category_id)}
                    </span>
                  </div>
                  <label>
                    Canonical
                    <select
                      value={targetsByGroup[groupKey(group)] || ""}
                      onChange={(event) =>
                        setTargetsByGroup((current) => ({
                          ...current,
                          [groupKey(group)]: event.target.value,
                        }))
                      }
                    >
                      {group.products.map((product) => (
                        <option key={product.product_id} value={product.product_id}>
                          {product.name}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                <div className="duplicate-products">
                  {group.products.map((product) => {
                    const isTarget = product.product_id === targetsByGroup[groupKey(group)];
                    return (
                      <div className="duplicate-product" key={product.product_id}>
                        <div>
                          <strong>{product.name}</strong>
                          <span>
                            {product.model || "no model"} · {product.sku || "no sku"} ·{" "}
                            {shortId(product.product_id)}
                          </span>
                        </div>
                        <button
                          className={isTarget ? "small-button muted-button" : "small-button"}
                          type="button"
                          disabled={isTarget || status === "merging"}
                          onClick={() => handleMerge(group, product.product_id)}
                        >
                          {isTarget ? "Canonical" : "Merge"}
                        </button>
                      </div>
                    );
                  })}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="empty-state">Load candidates to start reviewing duplicate products.</p>
        )}
      </section>
    </main>
  );
}

function loadAdminToken() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(adminTokenStorageKey) || "";
}

function persistAdminToken(token: string) {
  if (typeof window === "undefined") {
    return;
  }
  if (token.trim()) {
    window.localStorage.setItem(adminTokenStorageKey, token.trim());
  } else {
    window.localStorage.removeItem(adminTokenStorageKey);
  }
}

function defaultTargets(groups: ProductDuplicateCandidateGroup[]) {
  return Object.fromEntries(
    groups
      .filter((group) => group.products.length > 0)
      .map((group) => [groupKey(group), group.products[0].product_id]),
  );
}

function groupKey(group: ProductDuplicateCandidateGroup) {
  return `${group.category_id}:${group.brand_id || "none"}:${group.normalized_identity}`;
}

function shortId(value: string) {
  return value.slice(0, 8);
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "";
  }
  return new Intl.DateTimeFormat("ru", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function adminStatusLabel(status: AdminStatus) {
  if (status === "loading") {
    return "Loading";
  }
  if (status === "merging") {
    return "Merging";
  }
  if (status === "syncing") {
    return "Syncing";
  }
  if (status === "success") {
    return "Ready";
  }
  if (status === "error") {
    return "Error";
  }
  return "Idle";
}
