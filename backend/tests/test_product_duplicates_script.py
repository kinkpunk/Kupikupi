import csv
import json

import httpx

from scripts.product_duplicates import list_duplicate_candidates, merge_duplicate_product


def test_product_duplicates_script_lists_candidates(capsys) -> None:
    client = FakeDuplicateReviewClient(
        [
            httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "category_id": "category-1",
                            "brand_id": "brand-1",
                            "normalized_identity": "gt-2000 13",
                            "products": [
                                {
                                    "product_id": "product-1",
                                    "name": "ASICS GT-2000 13",
                                    "model": "GT-2000 13",
                                    "sku": "ASICS-GT-2000-A",
                                },
                                {
                                    "product_id": "product-2",
                                    "name": "Asics GT 2000 13",
                                    "model": "GT-2000 13",
                                    "sku": "ASICS-GT-2000-B",
                                },
                            ],
                        }
                    ]
                },
            )
        ]
    )

    exit_code = list_duplicate_candidates(
        api_base_url="https://api.example.test/v1",
        access_token="admin-token",
        limit=25,
        client=client,
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["count"] == 1
    assert output["items"][0]["normalized_identity"] == "gt-2000 13"
    assert client.requests == [
        {
            "method": "GET",
            "url": "https://api.example.test/v1/admin/product-duplicate-candidates?limit=25",
            "headers": {"Authorization": "Bearer admin-token"},
            "json": None,
        }
    ]


def test_product_duplicates_script_merges_product(capsys) -> None:
    client = FakeDuplicateReviewClient(
        [
            httpx.Response(
                200,
                json={
                    "target_product_id": "target-product",
                    "source_product_id": "source-product",
                    "offers_moved": 2,
                },
            )
        ]
    )

    exit_code = merge_duplicate_product(
        api_base_url="https://api.example.test/v1/",
        access_token="admin-token",
        source_product_id="source-product",
        target_product_id="target-product",
        client=client,
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["target_product_id"] == "target-product"
    assert client.requests == [
        {
            "method": "POST",
            "url": "https://api.example.test/v1/admin/products/source-product/merge",
            "headers": {"Authorization": "Bearer admin-token"},
            "json": {"target_product_id": "target-product"},
        }
    ]


def test_product_duplicates_script_reports_api_error(capsys) -> None:
    client = FakeDuplicateReviewClient([httpx.Response(403, json={"detail": "Forbidden"})])

    exit_code = list_duplicate_candidates(
        api_base_url="https://api.example.test/v1",
        access_token="bad-token",
        limit=50,
        client=client,
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert output == {"status_code": 403, "error": {"detail": "Forbidden"}}


def test_product_duplicates_script_writes_csv_output(tmp_path, capsys) -> None:
    output_path = tmp_path / "duplicates.csv"
    client = FakeDuplicateReviewClient(
        [
            httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "category_id": "category-1",
                            "brand_id": None,
                            "normalized_identity": "gt-2000 13",
                            "products": [
                                {
                                    "product_id": "product-1",
                                    "name": "ASICS GT-2000 13",
                                    "model": "GT-2000 13",
                                    "sku": "ASICS-GT-2000-A",
                                },
                                {
                                    "product_id": "product-2",
                                    "name": "Asics GT 2000 13",
                                    "model": "GT-2000 13",
                                    "sku": "ASICS-GT-2000-B",
                                },
                            ],
                        }
                    ]
                },
            )
        ]
    )

    exit_code = list_duplicate_candidates(
        api_base_url="https://api.example.test/v1",
        access_token="admin-token",
        limit=50,
        output_format="csv",
        output_path=output_path,
        client=client,
    )

    output = json.loads(capsys.readouterr().out)
    rows = list(csv.DictReader(output_path.read_text(encoding="utf-8").splitlines()))
    assert exit_code == 0
    assert output == {"count": 1, "output": str(output_path)}
    assert len(rows) == 2
    assert rows[0]["group_index"] == "1"
    assert rows[0]["product_id"] == "product-1"
    assert rows[1]["product_id"] == "product-2"


class FakeDuplicateReviewClient:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = responses
        self.requests: list[dict[str, object]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, str] | None = None,
    ) -> httpx.Response:
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "json": json,
            }
        )
        if not self._responses:
            raise AssertionError(f"Unexpected request: {method} {url}")
        return self._responses.pop(0)
