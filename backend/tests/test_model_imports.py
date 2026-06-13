import subprocess
import sys


def test_catalog_models_can_be_imported_in_fresh_process() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "from app.domains.catalog.models import Product"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
