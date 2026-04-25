from __future__ import annotations

import argparse
import csv
import json
import math
from array import array
from collections import Counter
from pathlib import Path
from typing import Any


SOURCE_LABEL = "CMS Medicare Physician & Other Practitioners by Provider and Service, 2023"


class CodeStats:
    def __init__(self) -> None:
        self.description = ""
        self.row_count = 0
        self.submitted_charges = array("d")
        self.allowed_amounts = array("d")
        self.beneficiary_counts = array("I")
        self.total_beneficiaries = 0
        self.total_services = 0.0
        self.provider_types: Counter[str] = Counter()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build compact HCPCS benchmark JSON from the public CMS provider-service CSV."
    )
    parser.add_argument("csv_path", type=Path, help="Path to MUP_PHY_R25_P05_V20_D23_Prov_Svc.csv")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reference/cms_benchmarks.json"),
        help="Benchmark JSON output path.",
    )
    parser.add_argument(
        "--seed",
        type=Path,
        default=Path("data/reference/cms_benchmarks.json"),
        help="Existing benchmark JSON to preserve manual fields such as allowed_taxonomies.",
    )
    parser.add_argument(
        "--min-rows",
        type=int,
        default=10,
        help="Skip HCPCS codes with fewer provider-service rows unless they already exist in the seed file.",
    )
    return parser.parse_args()


def parse_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def parse_int(value: str | None) -> int | None:
    parsed = parse_float(value)
    if parsed is None:
        return None
    return int(parsed)


def percentile(values: array[Any], quantile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = max(0, math.ceil((quantile / 100) * len(sorted_values)) - 1)
    return float(sorted_values[index])


def load_seed(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    rows = json.loads(path.read_text())
    return {row["procedure_code"]: row for row in rows if "procedure_code" in row}


def build_stats(csv_path: Path) -> dict[str, CodeStats]:
    stats_by_code: dict[str, CodeStats] = {}
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=1):
            code = (row.get("HCPCS_Cd") or "").strip()
            if not code:
                continue

            stats = stats_by_code.setdefault(code, CodeStats())
            stats.row_count += 1
            if not stats.description:
                stats.description = (row.get("HCPCS_Desc") or "").strip()

            submitted_charge = parse_float(row.get("Avg_Sbmtd_Chrg"))
            if submitted_charge is not None:
                stats.submitted_charges.append(submitted_charge)

            allowed_amount = parse_float(row.get("Avg_Mdcr_Alowd_Amt"))
            if allowed_amount is not None:
                stats.allowed_amounts.append(allowed_amount)

            beneficiaries = parse_int(row.get("Tot_Benes"))
            if beneficiaries is not None:
                stats.beneficiary_counts.append(beneficiaries)
                stats.total_beneficiaries += beneficiaries

            services = parse_float(row.get("Tot_Srvcs"))
            if services is not None:
                stats.total_services += services

            provider_type = (row.get("Rndrng_Prvdr_Type") or "").strip()
            if provider_type:
                stats.provider_types[provider_type] += 1

            if row_number % 1_000_000 == 0:
                print(f"Processed {row_number:,} CMS rows...")
    return stats_by_code


def build_rows(
    stats_by_code: dict[str, CodeStats],
    seed_by_code: dict[str, dict[str, Any]],
    min_rows: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for code, stats in sorted(stats_by_code.items()):
        seed = seed_by_code.get(code, {})
        if stats.row_count < min_rows and not seed:
            continue

        rows.append(
            {
                "procedure_code": code,
                "description": stats.description or seed.get("description", ""),
                "allowed_taxonomies": seed.get("allowed_taxonomies", []),
                "p90_amount": round(percentile(stats.submitted_charges, 90), 2),
                "p90_allowed_amount": round(percentile(stats.allowed_amounts, 90), 2),
                "p90_patient_count": int(math.ceil(percentile(stats.beneficiary_counts, 90))),
                "row_count": stats.row_count,
                "total_beneficiaries": stats.total_beneficiaries,
                "total_services": round(stats.total_services, 2),
                "common_provider_types": [
                    {"provider_type": provider_type, "rows": count}
                    for provider_type, count in stats.provider_types.most_common(5)
                ],
                "amount_basis": "Avg_Sbmtd_Chrg",
                "patient_count_basis": "Tot_Benes",
                "source": SOURCE_LABEL,
            }
        )

    for code, seed in sorted(seed_by_code.items()):
        if code not in stats_by_code:
            rows.append(seed)

    return sorted(rows, key=lambda row: row["procedure_code"])


def main() -> None:
    args = parse_args()
    seed_by_code = load_seed(args.seed)
    stats_by_code = build_stats(args.csv_path)
    rows = build_rows(stats_by_code, seed_by_code, args.min_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, indent=2) + "\n")
    print(f"Wrote {len(rows):,} CMS benchmark rows to {args.output}")


if __name__ == "__main__":
    main()
