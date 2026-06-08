import argparse
from pathlib import Path


def build_allowlist_value(raw_values: list[str]) -> str:
    ids = set()
    for raw_value in raw_values:
        for item in raw_value.replace("\n", ",").split(","):
            normalized = item.strip()
            if not normalized:
                continue
            if not normalized.isdecimal():
                raise ValueError(f"Telegram ID must be numeric: {normalized}")
            ids.add(int(normalized))
    return ",".join(str(item) for item in sorted(ids))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build TELEGRAM_ALLOWED_USER_IDS for Kupikupi closed tests."
    )
    parser.add_argument("telegram_ids", nargs="*", help="Telegram numeric IDs or comma lists.")
    parser.add_argument("--file", type=Path, help="File with comma/newline separated Telegram IDs.")
    parser.add_argument(
        "--env-name",
        default="TELEGRAM_ALLOWED_USER_IDS",
        help="Environment variable name to print.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_values = list(args.telegram_ids)
    if args.file is not None:
        raw_values.append(args.file.read_text(encoding="utf-8"))
    if not raw_values:
        print("Provide Telegram IDs as arguments or with --file.")
        raise SystemExit(2)

    try:
        value = build_allowlist_value(raw_values)
    except ValueError as exc:
        print(str(exc))
        raise SystemExit(1) from exc

    print(f'{args.env_name}="{value}"')


if __name__ == "__main__":
    main()
