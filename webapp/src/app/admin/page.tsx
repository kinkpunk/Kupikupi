"use client";

import { FormEvent, useMemo, useState } from "react";
import { createApiClient } from "../../lib/api-client.mjs";
import { getWebAppConfig } from "../../lib/runtime-config.mjs";
import type {
  ProductDuplicateCandidateGroup,
  ProductMergeResult,
} from "../../lib/types";

type AdminStatus = "idle" | "loading" | "merging" | "success" | "error";

const adminTokenStorageKey = "kupikupi_admin_access_token";
const webAppConfig = getWebAppConfig();

export default function AdminPage() {
  const [adminToken, setAdminToken] = useState(() => loadAdminToken());
  const [status, setStatus] = useState<AdminStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [groups, setGroups] = useState<ProductDuplicateCandidateGroup[]>([]);
  const [targetsByGroup, setTargetsByGroup] = useState<Record<string, string>>({});
  const [lastMerge, setLastMerge] = useState<ProductMergeResult | null>(null);

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

    try {
      persistAdminToken(adminToken);
      const response = (await api.listProductDuplicateCandidates({
        limit: 100,
      })) as { items: ProductDuplicateCandidateGroup[] };
      setGroups(response.items);
      setTargetsByGroup(defaultTargets(response.items));
      setStatus("success");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось загрузить дубликаты.");
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

function adminStatusLabel(status: AdminStatus) {
  if (status === "loading") {
    return "Loading";
  }
  if (status === "merging") {
    return "Merging";
  }
  if (status === "success") {
    return "Ready";
  }
  if (status === "error") {
    return "Error";
  }
  return "Idle";
}
