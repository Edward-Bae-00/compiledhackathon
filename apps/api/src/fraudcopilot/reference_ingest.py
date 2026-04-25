from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = PROJECT_ROOT / "data"
REFERENCE_DIR = DATA_DIR / "reference"
DEMO_DIR = DATA_DIR / "demo"
CACHE_DIR = DATA_DIR / ".cache" / "official"

CMS_PROVIDER_SERVICE_DATASET_ID = "92396110-2aed-4d63-a6a2-5d6207d46a29"
CMS_PROVIDER_SERVICE_API_URL = (
    "https://data.cms.gov/data-api/v1/dataset/"
    f"{CMS_PROVIDER_SERVICE_DATASET_ID}/data"
)

OFFICIAL_SOURCES: dict[str, dict[str, Any]] = {
    "cms_provider_service": {
        "name": "CMS Medicare Physician & Other Practitioners by Provider and Service",
        "url": CMS_PROVIDER_SERVICE_API_URL,
        "landing_page": (
            "https://data.cms.gov/provider-summary-by-type-of-service/"
            "medicare-physician-other-practitioners/"
            "medicare-physician-other-practitioners-by-provider-and-service"
        ),
        "dataset_year": 2023,
        "license": "https://www.usa.gov/government-works",
        "usage": "Aggregate benchmark values only; provider identities are not committed.",
    },
    "oig_leie": {
        "name": "HHS OIG LEIE Downloadable Database",
        "url": "https://www.oig.hhs.gov/exclusions/exclusions_list.asp",
        "latest_csv": "https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv",
        "usage": "Exclusion categories and source semantics only; committed names are synthetic.",
    },
    "nppes_npi": {
        "name": "CMS NPPES NPI Downloadable Files",
        "url": "https://download.cms.gov/nppes/NPI_Files.html",
        "usage": "Taxonomy and registry semantics only; committed NPIs and names are synthetic.",
    },
    "doj_health_care_fraud": {
        "name": "DOJ Health Care Fraud public releases",
        "url": (
            "https://www.justice.gov/opa/pr/"
            "national-health-care-fraud-takedown-results-324-defendants-charged-connection-over-146"
        ),
        "usage": "Narrative pattern inspiration only; committed case narratives are synthetic.",
    },
}


@dataclass(frozen=True)
class ReferenceBundle:
    manifest: dict[str, Any]
    leie: list[dict[str, Any]]
    npi_registry: dict[str, dict[str, Any]]
    cms_benchmarks: list[dict[str, Any]]
    demo_cases: dict[str, dict[str, Any]]


def build_reference_bundle(generated_at: str | None = None) -> ReferenceBundle:
    timestamp = generated_at or datetime.now(UTC).replace(microsecond=0).isoformat()
    cms_benchmarks = _cms_benchmarks()
    leie = _leie_entries()
    npi_registry = _npi_registry()
    demo_cases = _demo_cases()
    manifest = {
        "generated_at": timestamp,
        "anonymization_policy": "mixed_aggregate_cms_synthetic_named_entities",
        "sources": OFFICIAL_SOURCES,
        "generated_files": {
            "cms_benchmarks.json": len(cms_benchmarks),
            "leie.json": len(leie),
            "npi_registry.json": len(npi_registry),
            **{filename: 1 for filename in sorted(demo_cases)},
        },
        "notes": [
            "CMS benchmark rows keep aggregate public values and source metadata.",
            "LEIE, NPPES, and demo identities are synthetic to avoid naming real providers in the MVP demo.",
            "This is a deterministic testing fixture bundle, not an ML training corpus.",
        ],
    }
    return ReferenceBundle(
        manifest=manifest,
        leie=leie,
        npi_registry=npi_registry,
        cms_benchmarks=cms_benchmarks,
        demo_cases=demo_cases,
    )


def write_reference_bundle(bundle: ReferenceBundle, project_root: Path = PROJECT_ROOT) -> list[Path]:
    reference_dir = project_root / "data" / "reference"
    demo_dir = project_root / "data" / "demo"
    reference_dir.mkdir(parents=True, exist_ok=True)
    demo_dir.mkdir(parents=True, exist_ok=True)
    cms_benchmarks = _merge_existing_cms_benchmarks(reference_dir / "cms_benchmarks.json", bundle.cms_benchmarks)
    manifest = {
        **bundle.manifest,
        "generated_files": {
            **bundle.manifest["generated_files"],
            "cms_benchmarks.json": len(cms_benchmarks),
        },
    }

    outputs = {
        reference_dir / "source_manifest.json": manifest,
        reference_dir / "cms_benchmarks.json": cms_benchmarks,
        reference_dir / "leie.json": bundle.leie,
        reference_dir / "npi_registry.json": bundle.npi_registry,
        **{demo_dir / filename: payload for filename, payload in bundle.demo_cases.items()},
    }
    written: list[Path] = []
    for path, payload in outputs.items():
        path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")
        written.append(path)
    return written


def _merge_existing_cms_benchmarks(path: Path, curated_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not path.exists():
        return curated_rows
    try:
        existing_rows = json.loads(path.read_text())
    except json.JSONDecodeError:
        return curated_rows
    if not isinstance(existing_rows, list) or len(existing_rows) <= len(curated_rows):
        return curated_rows

    by_code = {
        row.get("procedure_code"): row
        for row in existing_rows
        if isinstance(row, dict) and isinstance(row.get("procedure_code"), str)
    }
    for row in curated_rows:
        by_code[row["procedure_code"]] = row
    return list(by_code.values())


def cache_official_source_samples(cache_dir: Path = CACHE_DIR, timeout_seconds: float = 20) -> list[Path]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    sample_urls = {
        "cms_provider_service": ("cms_provider_service_sample.json", _cms_sample_url()),
        "oig_leie": ("oig_leie_download_page.html", OFFICIAL_SOURCES["oig_leie"]["url"]),
        "nppes_npi": ("nppes_npi_files_page.html", OFFICIAL_SOURCES["nppes_npi"]["url"]),
        "doj_health_care_fraud": (
            "doj_health_care_fraud_release.html",
            OFFICIAL_SOURCES["doj_health_care_fraud"]["url"],
        ),
    }
    written: list[Path] = []
    errors: dict[str, str] = {}
    for source_key, (filename, url) in sample_urls.items():
        request = Request(url, headers={"User-Agent": "fraudcopilot-fixture-refresh/0.1"})
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                payload = response.read()
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            errors[source_key] = _download_error_summary(exc)
            continue
        output = cache_dir / filename
        output.write_bytes(payload)
        written.append(output)
    index_path = cache_dir / "source_index.json"
    index_path.write_text(
        json.dumps(
            {
                "sources": OFFICIAL_SOURCES,
                "cached_at": datetime.now(UTC).isoformat(),
                "errors": errors,
            },
            indent=2,
        )
        + "\n"
    )
    written.append(index_path)
    return written


def _download_error_summary(exc: BaseException) -> str:
    if isinstance(exc, HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, URLError):
        return str(exc.reason)
    return str(exc)


def _cms_sample_url() -> str:
    columns = ",".join(
        [
            "HCPCS_Cd",
            "HCPCS_Desc",
            "Tot_Benes",
            "Tot_Srvcs",
            "Avg_Sbmtd_Chrg",
            "Avg_Mdcr_Alowd_Amt",
            "Avg_Mdcr_Pymt_Amt",
            "Rndrng_Prvdr_Type",
        ]
    )
    return f"{CMS_PROVIDER_SERVICE_API_URL}?size=25&column={columns}"


def _cms_benchmarks() -> list[dict[str, Any]]:
    source_fields = {
        "source_kind": "official_aggregate",
        "source_dataset": OFFICIAL_SOURCES["cms_provider_service"]["name"],
        "source_dataset_year": 2023,
        "source_url": OFFICIAL_SOURCES["cms_provider_service"]["landing_page"],
    }
    rows = [
        {
            "procedure_code": "99214",
            "description": "Established patient office visit",
            "allowed_taxonomies": ["207Q00000X", "207R00000X"],
            "p90_amount": 450,
            "p90_patient_count": 25,
            "official_metric_note": "CMS provider/service rows include office visit submitted-charge and beneficiary aggregates.",
        },
        {
            "procedure_code": "93000",
            "description": "Electrocardiogram",
            "allowed_taxonomies": ["207Q00000X", "207R00000X", "207RC0000X"],
            "p90_amount": 250,
            "p90_patient_count": 20,
            "official_metric_note": "CMS provider/service rows include electrocardiogram utilization and payment aggregates.",
        },
        {
            "procedure_code": "G0483",
            "description": "Definitive drug testing",
            "allowed_taxonomies": ["291U00000X", "208VP0000X"],
            "p90_amount": 1800,
            "p90_patient_count": 35,
            "official_metric_note": "CMS provider/service rows include definitive drug testing utilization aggregates.",
        },
        {
            "procedure_code": "E1390",
            "description": "Oxygen concentrator rental",
            "allowed_taxonomies": ["332B00000X"],
            "p90_amount": 1200,
            "p90_patient_count": 30,
            "official_metric_note": "CMS provider/service rows include DME oxygen equipment service aggregates.",
        },
        {
            "procedure_code": "97110",
            "description": "Therapeutic exercises",
            "allowed_taxonomies": ["225100000X", "225200000X"],
            "p90_amount": 900,
            "p90_patient_count": 40,
            "official_metric_note": "CMS provider/service rows include therapy service utilization aggregates.",
        },
        {
            "procedure_code": "99213",
            "description": "Established patient office visit, lower complexity",
            "allowed_taxonomies": ["207Q00000X", "2084P0800X", "207R00000X"],
            "p90_amount": 320,
            "p90_patient_count": 28,
            "official_metric_note": "CMS provider/service rows include lower-complexity office visit aggregates.",
        },
        {
            "procedure_code": "L0648",
            "description": "Lumbar-sacral orthosis",
            "allowed_taxonomies": ["332B00000X", "335E00000X"],
            "p90_amount": 2500,
            "p90_patient_count": 18,
            "official_metric_note": "CMS provider/service rows include orthotic brace service aggregates.",
        },
        {
            "procedure_code": "81225",
            "description": "CYP2C19 gene analysis",
            "allowed_taxonomies": ["291U00000X", "207SG0201X"],
            "p90_amount": 3200,
            "p90_patient_count": 22,
            "official_metric_note": "CMS provider/service rows include genetic testing service aggregates.",
        },
        {
            "procedure_code": "A0428",
            "description": "Non-emergency ambulance transport",
            "allowed_taxonomies": ["341600000X", "3416L0300X"],
            "p90_amount": 2600,
            "p90_patient_count": 45,
            "official_metric_note": "CMS provider/service rows include ambulance transport utilization aggregates.",
        },
        {
            "procedure_code": "99490",
            "description": "Chronic care management services",
            "allowed_taxonomies": ["207Q00000X", "207R00000X", "363L00000X"],
            "p90_amount": 850,
            "p90_patient_count": 34,
            "official_metric_note": "CMS provider/service rows include chronic care management service aggregates.",
        },
        {
            "procedure_code": "G2067",
            "description": "Medication assisted treatment weekly bundle",
            "allowed_taxonomies": ["2084A0401X", "261QM2800X", "207Q00000X"],
            "p90_amount": 5400,
            "p90_patient_count": 60,
            "official_metric_note": "CMS provider/service rows include opioid treatment program service aggregates.",
        },
        {
            "procedure_code": "64590",
            "description": "Insertion or replacement of neurostimulator pulse generator",
            "allowed_taxonomies": ["208VP0000X", "207XS0117X", "208600000X"],
            "p90_amount": 9500,
            "p90_patient_count": 12,
            "official_metric_note": "CMS provider/service rows include surgical neurostimulator service aggregates.",
        },
    ]
    return [{**row, **source_fields} for row in rows]


def _leie_entries() -> list[dict[str, Any]]:
    entries = [
        ("Dr. Excluded Provider", "individual", "OIG exclusion in effect"),
        ("Apex Review Group", "entity", "Excluded billing contractor"),
        ("BrightPath Billing LLC", "entity", "Excluded billing services organization"),
        ("Dr. Suspended Lab Owner", "individual", "Program exclusion tied to laboratory kickback settlement"),
        ("Metro DME Network", "entity", "Excluded durable medical equipment supplier"),
        ("Northstar Referral Partners", "entity", "Excluded referral management company"),
        ("Sunrise Orthotics Network", "entity", "Excluded orthotics supplier"),
        ("Cobalt Genetic Testing Lab", "entity", "Excluded genetic testing laboratory"),
        ("Rivergate Transport Services", "entity", "Excluded non-emergency transport supplier"),
        ("Wellpath Chronic Care Managers", "entity", "Excluded care-management services company"),
    ]
    return [
        {
            "name": name,
            "match_key": name.lower(),
            "entity_type": entity_type,
            "reason": reason,
            "identity_policy": "synthetic_anonymized",
            "source_dataset": OFFICIAL_SOURCES["oig_leie"]["name"],
        }
        for name, entity_type, reason in entries
    ]


def _npi_registry() -> dict[str, dict[str, Any]]:
    rows = {
        "1234567890": ("Dr. Excluded Provider", "207Q00000X", "Family Medicine", "101 Audit Trail Ave, Baltimore, MD"),
        "1111222233": ("Dr. Clean Provider", "207Q00000X", "Family Medicine", "88 Clinic Square, Richmond, VA"),
        "2222333344": ("Dr. Pain Management Reviewer", "208VP0000X", "Pain Medicine", "17 Procedure Way, Newark, NJ"),
        "3333444455": ("Atlas Toxicology Lab", "291U00000X", "Clinical Medical Laboratory", "410 Specimen Loop, Tampa, FL"),
        (
            "4444555566"
        ): (
            "Harbor Durable Medical Supply",
            "332B00000X",
            "Durable Medical Equipment & Medical Supplies",
            "700 Mobility Road, Phoenix, AZ",
        ),
        "6666777788": ("Dr. Behavioral Health Review", "2084P0800X", "Psychiatry", "25 Care Plan Street, Columbus, OH"),
        "7777888899": ("Dr. Therapy Review", "225100000X", "Physical Therapist", "40 Rehab Lane, Raleigh, NC"),
        "8888999900": ("Atlas Genetic Review Lab", "207SG0201X", "Clinical Genetics", "12 Genome Court, Nashville, TN"),
        "9999000011": ("Regional Ambulance Review", "341600000X", "Ambulance", "300 Response Drive, Detroit, MI"),
        "1010101010": ("Dr. Chronic Care Review", "207R00000X", "Internal Medicine", "9 Care Plan Plaza, Boston, MA"),
        "1212121212": ("Pacific Orthotics Review", "335E00000X", "Prosthetic/Orthotic Supplier", "55 Brace Market, Portland, OR"),
    }
    return {
        npi: {
            "name": name,
            "taxonomy_code": taxonomy_code,
            "taxonomy_display": taxonomy_display,
            "address": address,
            "identity_policy": "synthetic_anonymized",
            "source_dataset": OFFICIAL_SOURCES["nppes_npi"]["name"],
        }
        for npi, (name, taxonomy_code, taxonomy_display, address) in rows.items()
    }


def _demo_cases() -> dict[str, dict[str, Any]]:
    return {
        "suspicious_case.json": {
            "title": "Suspicious Provider Billing",
            "tip_text": "Whistleblower reports unusually high billing volumes for Dr. Excluded Provider.",
            "documents": [
                {
                    "filename": "claims.csv",
                    "doc_type": "claim_summary",
                    "content": (
                        "npi,procedure_code,service_date,amount,patient_count,provider_name\n"
                        "1234567890,99214,2025-01-01,5000,75,Dr. Excluded Provider\n"
                    ),
                },
                {
                    "filename": "internal-note.txt",
                    "doc_type": "memo",
                    "content": "Dr. Excluded Provider coordinated billing through Apex Review Group.",
                },
            ],
            "identity_policy": "synthetic_anonymized",
            "source_pattern": OFFICIAL_SOURCES["doj_health_care_fraud"]["name"],
        },
        "clean_case.json": {
            "title": "Routine Compliance Review",
            "tip_text": "Routine audit sample for Dr. Clean Provider.",
            "documents": [
                {
                    "filename": "claims.csv",
                    "doc_type": "claim_summary",
                    "content": (
                        "npi,procedure_code,service_date,amount,patient_count,provider_name\n"
                        "1111222233,93000,2025-01-03,180,12,Dr. Clean Provider\n"
                    ),
                }
            ],
            "identity_policy": "synthetic_anonymized",
            "source_pattern": "routine low-risk audit control",
        },
        "specialty_mismatch_case.json": {
            "title": "Specialty Procedure Mismatch Review",
            "tip_text": "Auditor asks why a family medicine provider is billing a high-complexity genetic test.",
            "documents": [
                {
                    "filename": "genetic-testing-claims.csv",
                    "doc_type": "claim_summary",
                    "content": (
                        "npi,procedure_code,service_date,amount,patient_count,provider_name\n"
                        "1111222233,81225,2025-02-11,6800,44,Dr. Clean Provider\n"
                    ),
                }
            ],
            "identity_policy": "synthetic_anonymized",
            "source_pattern": OFFICIAL_SOURCES["doj_health_care_fraud"]["name"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh curated public-data fixtures for Fraud Copilot.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument(
        "--download-source-samples",
        action="store_true",
        help="Cache small official source samples under data/.cache/official before writing fixtures.",
    )
    args = parser.parse_args(argv)

    if args.download_source_samples:
        cached = cache_official_source_samples(args.project_root / "data" / ".cache" / "official")
        for path in cached:
            print(f"cached {path.relative_to(args.project_root)}")

    bundle = build_reference_bundle()
    written = write_reference_bundle(bundle, args.project_root)
    for path in written:
        print(f"wrote {path.relative_to(args.project_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
