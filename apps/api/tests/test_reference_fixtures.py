import json
from pathlib import Path
from urllib.error import URLError

from fraudcopilot import reference_ingest
from fraudcopilot.reference_ingest import build_reference_bundle


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"


def test_reference_ingest_builds_anonymized_official_fixture_bundle():
    bundle = build_reference_bundle()

    assert bundle.manifest["anonymization_policy"] == "mixed_aggregate_cms_synthetic_named_entities"
    assert bundle.manifest["sources"]["cms_provider_service"]["url"].startswith("https://data.cms.gov/")
    assert bundle.manifest["sources"]["oig_leie"]["url"].startswith("https://www.oig.hhs.gov/")
    assert bundle.manifest["sources"]["nppes_npi"]["url"].startswith("https://download.cms.gov/")
    assert bundle.manifest["sources"]["doj_health_care_fraud"]["url"].startswith("https://www.justice.gov/")

    assert len(bundle.cms_benchmarks) >= 10
    assert len(bundle.leie) >= 8
    assert len(bundle.npi_registry) >= 8
    assert {"suspicious_case.json", "clean_case.json", "specialty_mismatch_case.json"} <= set(bundle.demo_cases)
    assert all(row["source_kind"] == "official_aggregate" for row in bundle.cms_benchmarks)
    assert all(row["identity_policy"] == "synthetic_anonymized" for row in bundle.leie)
    assert all(row["identity_policy"] == "synthetic_anonymized" for row in bundle.npi_registry.values())


def test_committed_reference_fixtures_include_manifest_and_rule_coverage():
    manifest = json.loads((REFERENCE_DIR / "source_manifest.json").read_text())
    leie = json.loads((REFERENCE_DIR / "leie.json").read_text())
    npi_registry = json.loads((REFERENCE_DIR / "npi_registry.json").read_text())
    cms_benchmarks = json.loads((REFERENCE_DIR / "cms_benchmarks.json").read_text())

    assert manifest["anonymization_policy"] == "mixed_aggregate_cms_synthetic_named_entities"
    assert manifest["generated_files"]["cms_benchmarks.json"] == len(cms_benchmarks)
    assert manifest["generated_files"]["leie.json"] == len(leie)
    assert manifest["generated_files"]["npi_registry.json"] == len(npi_registry)

    procedure_codes = {row["procedure_code"] for row in cms_benchmarks}
    assert {"99214", "93000", "G0483", "E1390", "97110", "99213", "L0648", "81225", "A0428", "99490"} <= procedure_codes
    assert all(row["source_kind"] == "official_aggregate" for row in cms_benchmarks)
    assert all(row["source_dataset_year"] == 2023 for row in cms_benchmarks)
    assert all(row["p90_amount"] > 0 and row["p90_patient_count"] > 0 for row in cms_benchmarks)

    assert all(entry["identity_policy"] == "synthetic_anonymized" for entry in leie)
    assert all(provider["identity_policy"] == "synthetic_anonymized" for provider in npi_registry.values())


def test_source_sample_cache_records_download_failures_without_blocking_refresh(tmp_path, monkeypatch):
    def raise_url_error(request, timeout):
        raise URLError("certificate verification failed")

    monkeypatch.setattr(reference_ingest, "urlopen", raise_url_error)

    written = reference_ingest.cache_official_source_samples(tmp_path)

    assert written == [tmp_path / "source_index.json"]
    index = json.loads((tmp_path / "source_index.json").read_text())
    assert set(index["errors"]) == set(reference_ingest.OFFICIAL_SOURCES)
    assert "certificate verification failed" in index["errors"]["cms_provider_service"]


def test_fixture_writer_preserves_existing_broad_cms_benchmark_rows(tmp_path):
    reference_dir = tmp_path / "data" / "reference"
    reference_dir.mkdir(parents=True)
    existing_rows = [
        {
            "procedure_code": f"X{i:04d}",
            "description": "Existing official aggregate row",
            "allowed_taxonomies": [],
            "p90_amount": 100,
            "p90_patient_count": 20,
        }
        for i in range(20)
    ]
    existing_rows.append(
        {
            "procedure_code": "99214",
            "description": "Older office visit aggregate",
            "allowed_taxonomies": [],
            "p90_amount": 1,
            "p90_patient_count": 1,
        }
    )
    (reference_dir / "cms_benchmarks.json").write_text(json.dumps(existing_rows) + "\n")

    bundle = build_reference_bundle(generated_at="2026-04-25T00:00:00+00:00")
    reference_ingest.write_reference_bundle(bundle, tmp_path)

    merged_rows = json.loads((reference_dir / "cms_benchmarks.json").read_text())
    manifest = json.loads((reference_dir / "source_manifest.json").read_text())
    rows_by_code = {row["procedure_code"]: row for row in merged_rows}
    assert rows_by_code["X0000"]["description"] == "Existing official aggregate row"
    assert rows_by_code["99214"]["p90_amount"] == 450
    assert manifest["generated_files"]["cms_benchmarks.json"] == len(merged_rows)
