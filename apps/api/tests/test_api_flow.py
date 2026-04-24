import json

from fastapi.testclient import TestClient

from fraudcopilot import app as app_module
from fraudcopilot.app import create_app


def test_analysis_flow_returns_case_file_with_findings():
    client = TestClient(create_app())

    create_response = client.post(
        "/cases",
        json={
            "title": "Suspicious Provider Billing",
            "tip_text": "Whistleblower reports unusually high billing volumes for Provider X."
        },
    )

    assert create_response.status_code == 201
    case_id = create_response.json()["id"]

    document_response = client.post(
        f"/cases/{case_id}/documents",
        json={
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
            ]
        },
    )

    assert document_response.status_code == 201
    assert len(document_response.json()["documents"]) == 2

    analyze_response = client.post(f"/cases/{case_id}/analyze")

    assert analyze_response.status_code == 200
    payload = analyze_response.json()

    assert payload["case"]["overall_risk_score"] >= 60
    assert any(match["source_name"] == "LEIE" for match in payload["external_matches"])
    assert any(flag["reason_code"] == "excluded_entity_match" for flag in payload["risk_flags"])
    assert payload["memo"]["body_markdown"]
    assert any(event["source"] == "internal-note.txt" for event in payload["timeline"])
    assert payload["palantir_insight"]["provider"] == "Palantir AIP"
    assert payload["palantir_insight"]["status"] == "not_configured"
    assert "Set PALANTIR_AIP_LOGIC_URL" in payload["palantir_insight"]["recommendation"]


def test_case_detail_endpoints_expose_analysis_outputs():
    client = TestClient(create_app())

    create_response = client.post(
        "/cases",
        json={
            "title": "Clean Provider Review",
            "tip_text": "Routine review of a provider with no exclusion history."
        },
    )
    case_id = create_response.json()["id"]

    client.post(
        f"/cases/{case_id}/documents",
        json={
            "documents": [
                {
                    "filename": "claims.csv",
                    "doc_type": "claim_summary",
                    "content": (
                        "npi,procedure_code,service_date,amount,patient_count,provider_name\n"
                        "1111222233,93000,2025-01-03,180,12,Dr. Clean Provider\n"
                    ),
                }
            ]
        },
    )
    client.post(f"/cases/{case_id}/analyze")

    case_response = client.get(f"/cases/{case_id}")
    findings_response = client.get(f"/cases/{case_id}/findings")
    timeline_response = client.get(f"/cases/{case_id}/timeline")
    memo_response = client.get(f"/cases/{case_id}/memo")

    assert case_response.status_code == 200
    assert findings_response.status_code == 200
    assert timeline_response.status_code == 200
    assert memo_response.status_code == 200
    assert case_response.json()["title"] == "Clean Provider Review"
    assert isinstance(findings_response.json()["risk_flags"], list)
    assert isinstance(timeline_response.json()["timeline"], list)
    assert "body_markdown" in memo_response.json()


def test_palantir_status_reports_not_configured_without_env(monkeypatch):
    monkeypatch.delenv("PALANTIR_AIP_LOGIC_URL", raising=False)
    monkeypatch.delenv("PALANTIR_API_TOKEN", raising=False)
    monkeypatch.delenv("PALANTIR_HOSTNAME", raising=False)

    client = TestClient(create_app())

    response = client.get("/integrations/palantir/status")

    assert response.status_code == 200
    assert response.json() == {
        "provider": "Palantir AIP",
        "configured": False,
        "reachable": False,
        "mode": "not_configured",
        "error": None,
    }


def test_api_allows_local_frontend_origin_for_live_demo():
    client = TestClient(create_app())

    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_palantir_aip_logic_response_enriches_analysis(monkeypatch):
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(
                {
                    "recommendation": (
                        "Palantir AIP recommends expedited investigator review because the case combines "
                        "an exclusion hit with abnormal billing."
                    )
                }
            ).encode()

    def fake_urlopen(request, timeout):
        calls.append(
            {
                "url": request.full_url,
                "authorization": request.get_header("Authorization"),
                "payload": json.loads(request.data.decode()),
                "timeout": timeout,
            }
        )
        return FakeResponse()

    monkeypatch.setenv("PALANTIR_AIP_LOGIC_URL", "https://example.palantirfoundry.com/aip/run")
    monkeypatch.setenv("PALANTIR_API_TOKEN", "test-token")
    monkeypatch.delenv("PALANTIR_HOSTNAME", raising=False)
    monkeypatch.setattr(app_module, "urlopen", fake_urlopen)

    client = TestClient(create_app())
    create_response = client.post(
        "/cases",
        json={
            "title": "Suspicious Provider Billing",
            "tip_text": "Whistleblower reports unusually high billing volumes for Provider X.",
        },
    )
    case_id = create_response.json()["id"]
    client.post(
        f"/cases/{case_id}/documents",
        json={
            "documents": [
                {
                    "filename": "claims.csv",
                    "doc_type": "claim_summary",
                    "content": (
                        "npi,procedure_code,service_date,amount,patient_count,provider_name\n"
                        "1234567890,99214,2025-01-01,5000,75,Dr. Excluded Provider\n"
                    ),
                }
            ]
        },
    )

    response = client.post(f"/cases/{case_id}/analyze")

    assert response.status_code == 200
    insight = response.json()["palantir_insight"]
    assert insight["status"] == "live"
    assert insight["provider"] == "Palantir AIP"
    assert "expedited investigator review" in insight["recommendation"]
    assert calls[0]["authorization"] == "Bearer test-token"
    assert calls[0]["payload"]["case"]["title"] == "Suspicious Provider Billing"
    assert calls[0]["payload"]["risk_flags"]


def test_staged_palantir_pipeline_extracts_risk_memo_and_graph(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(self.payload).encode()

    def fake_urlopen(request, timeout):
        request_payload = json.loads(request.data.decode())
        calls.append(
            {
                "url": request.full_url,
                "authorization": request.get_header("Authorization"),
                "payload": request_payload,
                "timeout": timeout,
            }
        )
        if request.full_url.endswith("/extract"):
            return FakeResponse(
                {
                    "entities": [
                        {
                            "id": "aip-provider",
                            "entity_type": "provider",
                            "name": "Dr. Narrative Provider",
                            "npi": "9999888877",
                            "source": "Palantir AIP",
                        },
                        {
                            "id": "aip-billing-company",
                            "entity_type": "organization",
                            "name": "Apex Review Group",
                            "source": "Palantir AIP",
                        },
                    ],
                    "claims": [
                        {
                            "provider_name": "Dr. Narrative Provider",
                            "npi": "9999888877",
                            "procedure_code": "G0483",
                            "service_date": "2025-02-10",
                            "amount": 7200,
                            "patient_count": 94,
                            "source": "Palantir AIP",
                        }
                    ],
                    "relationships": [
                        {
                            "source": "Dr. Narrative Provider",
                            "target": "Apex Review Group",
                            "relationship": "billing_management",
                            "evidence": "Apex Review Group managed billing for the provider.",
                            "source_type": "Palantir AIP",
                        }
                    ],
                }
            )
        if request.full_url.endswith("/risk"):
            return FakeResponse(
                {
                    "risk_factors": [
                        {
                            "severity": "high",
                            "reason_code": "aip_billing_network_risk",
                            "score_delta": 35,
                            "summary": "AIP found a billing company linkage tied to abnormal volume.",
                            "why_flagged": "The provider, billing company, and claims volume form a high-risk cluster.",
                            "external_validation": "Palantir AIP network and risk assessment",
                            "evidence_quotes": ["Apex Review Group managed billing for the provider."],
                        }
                    ]
                }
            )
        if request.full_url.endswith("/memo"):
            return FakeResponse(
                {
                    "memo_markdown": (
                        "# AIP Investigator Memo\n\n"
                        "Palantir AIP identified a provider-billing-company relationship and abnormal billing volume."
                    ),
                    "recommendation": "Escalate for investigator review and preserve billing-company records.",
                }
            )
        raise AssertionError(f"Unexpected URL {request.full_url}")

    monkeypatch.setenv("PALANTIR_AIP_EXTRACT_FACTS_URL", "https://example.palantirfoundry.com/aip/extract")
    monkeypatch.setenv("PALANTIR_AIP_ASSESS_RISK_URL", "https://example.palantirfoundry.com/aip/risk")
    monkeypatch.setenv("PALANTIR_AIP_GENERATE_MEMO_URL", "https://example.palantirfoundry.com/aip/memo")
    monkeypatch.setenv("PALANTIR_API_TOKEN", "test-token")
    monkeypatch.setenv("PALANTIR_FORCE_LOCAL", "false")
    monkeypatch.delenv("PALANTIR_AIP_LOGIC_URL", raising=False)
    monkeypatch.delenv("PALANTIR_HOSTNAME", raising=False)
    monkeypatch.setattr(app_module, "urlopen", fake_urlopen)

    client = TestClient(create_app())
    case_response = client.post(
        "/cases",
        json={
            "title": "Narrative Billing Network",
            "tip_text": "Tip says Dr. Narrative Provider routes billing through Apex Review Group.",
        },
    )
    case_id = case_response.json()["id"]
    client.post(
        f"/cases/{case_id}/documents",
        json={
            "documents": [
                {
                    "filename": "tip-email.txt",
                    "doc_type": "memo",
                    "content": (
                        "On 2025-02-10, Dr. Narrative Provider NPI 9999888877 billed G0483 for "
                        "$7200 across 94 patients. Apex Review Group managed billing for the provider."
                    ),
                }
            ]
        },
    )

    response = client.post(f"/cases/{case_id}/analyze")

    assert response.status_code == 200
    payload = response.json()
    assert [call["url"] for call in calls] == [
        "https://example.palantirfoundry.com/aip/extract",
        "https://example.palantirfoundry.com/aip/risk",
        "https://example.palantirfoundry.com/aip/memo",
    ]
    assert all(call["authorization"] == "Bearer test-token" for call in calls)
    assert payload["case"]["overall_risk_score"] >= 35
    assert any(flag["source"] == "Palantir AIP" for flag in payload["risk_flags"])
    assert any(flag["reason_code"] == "aip_billing_network_risk" for flag in payload["risk_flags"])
    assert "Palantir AIP identified" in payload["memo"]["body_markdown"]
    assert payload["memo"]["source"] == "Palantir AIP"
    assert payload["palantir_insight"]["status"] == "live"
    assert "Escalate" in payload["palantir_insight"]["recommendation"]
    assert {stage["stage"]: stage["status"] for stage in payload["palantir"]["stages"]} == {
        "extract_case_facts": "live",
        "assess_risk": "live",
        "generate_memo": "live",
    }
    assert any(node["label"] == "Dr. Narrative Provider" for node in payload["evidence_graph"]["nodes"])
    assert any(edge["relationship"] == "billing_management" for edge in payload["evidence_graph"]["edges"])


def test_local_fallback_scores_narrative_input_and_builds_graph(monkeypatch):
    monkeypatch.delenv("PALANTIR_AIP_EXTRACT_FACTS_URL", raising=False)
    monkeypatch.delenv("PALANTIR_AIP_ASSESS_RISK_URL", raising=False)
    monkeypatch.delenv("PALANTIR_AIP_GENERATE_MEMO_URL", raising=False)
    monkeypatch.delenv("PALANTIR_AIP_LOGIC_URL", raising=False)
    monkeypatch.delenv("PALANTIR_API_TOKEN", raising=False)
    monkeypatch.delenv("PALANTIR_HOSTNAME", raising=False)

    client = TestClient(create_app())
    case_response = client.post(
        "/cases",
        json={
            "title": "Unknown Narrative Provider",
            "tip_text": "Auditor reports a new provider with high billing and management-company control.",
        },
    )
    case_id = case_response.json()["id"]
    client.post(
        f"/cases/{case_id}/documents",
        json={
            "documents": [
                {
                    "filename": "audit-note.txt",
                    "doc_type": "memo",
                    "content": (
                        "On 2025-03-12, Dr. Unknown Provider NPI 5555666677 billed 99214 for "
                        "$12000 across 160 patients. Apex Review Group managed billing and referrals."
                    ),
                }
            ]
        },
    )

    response = client.post(f"/cases/{case_id}/analyze")

    assert response.status_code == 200
    payload = response.json()
    assert payload["case"]["overall_risk_score"] > 0
    reason_codes = {flag["reason_code"] for flag in payload["risk_flags"]}
    assert "unknown_npi" in reason_codes
    assert "high_claim_volume" in reason_codes
    assert "suspicious_relationship_language" in reason_codes
    assert all(flag["source"] == "Local Rule" for flag in payload["risk_flags"])
    assert payload["palantir"]["mode"] == "not_configured"
    assert all(stage["status"] == "not_configured" for stage in payload["palantir"]["stages"])
    assert any(node["label"] == "Dr. Unknown Provider" for node in payload["evidence_graph"]["nodes"])
    assert any(edge["relationship"] == "managed_by" for edge in payload["evidence_graph"]["edges"])


def test_force_local_query_skips_configured_palantir_stages(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        raise AssertionError("Palantir should not be called when force_local=true")

    monkeypatch.setenv("PALANTIR_AIP_EXTRACT_FACTS_URL", "https://example.palantirfoundry.com/aip/extract")
    monkeypatch.setenv("PALANTIR_AIP_ASSESS_RISK_URL", "https://example.palantirfoundry.com/aip/risk")
    monkeypatch.setenv("PALANTIR_AIP_GENERATE_MEMO_URL", "https://example.palantirfoundry.com/aip/memo")
    monkeypatch.setenv("PALANTIR_API_TOKEN", "test-token")
    monkeypatch.setattr(app_module, "urlopen", fake_urlopen)

    client = TestClient(create_app())
    create_response = client.post(
        "/cases",
        json={
            "title": "Forced Local Review",
            "tip_text": "Run the configured case in local-only mode.",
        },
    )
    case_id = create_response.json()["id"]
    client.post(
        f"/cases/{case_id}/documents",
        json={
            "documents": [
                {
                    "filename": "claims.csv",
                    "doc_type": "claim_summary",
                    "content": (
                        "npi,procedure_code,service_date,amount,patient_count,provider_name\n"
                        "1234567890,99214,2025-01-01,5000,75,Dr. Excluded Provider\n"
                    ),
                }
            ]
        },
    )

    response = client.post(f"/cases/{case_id}/analyze?force_local=true")

    assert response.status_code == 200
    payload = response.json()
    assert calls == []
    assert payload["palantir"]["mode"] == "forced_local"
    assert all(stage["status"] == "forced_local" for stage in payload["palantir"]["stages"])
    assert payload["palantir_insight"]["status"] == "forced_local"
