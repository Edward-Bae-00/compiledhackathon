import json
from pathlib import Path

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
