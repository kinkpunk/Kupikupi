import argparse
import json
import os
from typing import Protocol

import httpx


class DuplicateReviewClient(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, str] | None = None,
    ) -> httpx.Response:
        pass


def list_duplicate_candidates(
    *,
    api_base_url: str,
    access_token: str,
    limit: int,
    client: DuplicateReviewClient | None = None,
) -> int:
    with _client_context(client) as active_client:
        response = active_client.request(
            "GET",
            _url(api_base_url, f"/admin/product-duplicate-candidates?limit={limit}"),
            headers=_headers(access_token),
        )
    if response.status_code != 200:
        print(_error_report(response))
        return 1

    payload = response.json()
    items = payload.get("items", [])
    print(json.dumps({"count": len(items), "items": items}, ensure_ascii=False, indent=2))
    return 0


def merge_duplicate_product(
    *,
    api_base_url: str,
    access_token: str,
    source_product_id: str,
    target_product_id: str,
    client: DuplicateReviewClient | None = None,
) -> int:
    with _client_context(client) as active_client:
        response = active_client.request(
            "POST",
            _url(api_base_url, f"/admin/products/{source_product_id}/merge"),
            headers=_headers(access_token),
            json={"target_product_id": target_product_id},
        )
    if response.status_code not in {200, 201, 202}:
        print(_error_report(response))
        return 1

    print(json.dumps(response.json(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review and merge Kupikupi product duplicates.")
    parser.add_argument(
        "--api-base-url",
        default=os.environ.get("KUPIKUPI_API_BASE_URL", ""),
        help="Backend API base URL, for example https://api.staging.kupikupi.example/v1.",
    )
    parser.add_argument(
        "--access-token",
        default=os.environ.get("KUPIKUPI_ADMIN_ACCESS_TOKEN", ""),
        help="Admin access token. Defaults to KUPIKUPI_ADMIN_ACCESS_TOKEN.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list", help="List duplicate candidates.")
    list_parser.add_argument("--limit", type=int, default=50)
    merge_parser = subparsers.add_parser("merge", help="Merge one source product into a target.")
    merge_parser.add_argument("--source-product-id", required=True)
    merge_parser.add_argument("--target-product-id", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.api_base_url.strip():
        print("Provide --api-base-url or KUPIKUPI_API_BASE_URL.")
        raise SystemExit(2)
    if not args.access_token.strip():
        print("Provide --access-token or KUPIKUPI_ADMIN_ACCESS_TOKEN.")
        raise SystemExit(2)

    if args.command == "list":
        raise SystemExit(
            list_duplicate_candidates(
                api_base_url=args.api_base_url,
                access_token=args.access_token,
                limit=args.limit,
            )
        )
    raise SystemExit(
        merge_duplicate_product(
            api_base_url=args.api_base_url,
            access_token=args.access_token,
            source_product_id=args.source_product_id,
            target_product_id=args.target_product_id,
        )
    )


def _url(api_base_url: str, path: str) -> str:
    return f"{api_base_url.rstrip('/')}{path}"


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _error_report(response: httpx.Response) -> str:
    try:
        detail = response.json()
    except ValueError:
        detail = response.text
    return json.dumps(
        {"status_code": response.status_code, "error": detail},
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


class _client_context:
    def __init__(self, client: DuplicateReviewClient | None) -> None:
        self._provided_client = client
        self._created_client: httpx.Client | None = None

    def __enter__(self) -> DuplicateReviewClient:
        if self._provided_client is not None:
            return self._provided_client
        self._created_client = httpx.Client(timeout=15)
        return self._created_client

    def __exit__(self, *_args) -> None:
        if self._created_client is not None:
            self._created_client.close()


if __name__ == "__main__":
    main()
