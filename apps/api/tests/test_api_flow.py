from fastapi.testclient import TestClient

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
