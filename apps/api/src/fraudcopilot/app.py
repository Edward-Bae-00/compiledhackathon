from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[4]
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def slugify_reason(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


class CreateCaseRequest(BaseModel):
    title: str
    tip_text: str


class CaseRecord(BaseModel):
    id: str
    title: str
    tip_text: str
    status: str
    overall_risk_score: int
    created_at: str


class DocumentInput(BaseModel):
    filename: str
    doc_type: str
    content: str


class DocumentUploadRequest(BaseModel):
    documents: list[DocumentInput]


class DocumentRecord(BaseModel):
    id: str
    case_id: str
    filename: str
    doc_type: str
    content: str


class DocumentPreview(BaseModel):
    id: str
    filename: str
    doc_type: str
    preview: str


class ExternalMatch(BaseModel):
    id: str
    case_id: str
    source_name: str
    match_key: str
    match_status: str
    summary: str


class RiskFlag(BaseModel):
    id: str
    case_id: str
    severity: str
    reason_code: str
    score_delta: int
    summary: str
    why_flagged: str
    external_validation: str
    evidence_quotes: list[str]


class TimelineEvent(BaseModel):
    id: str
    case_id: str
    label: str
    date: str | None
    source: str


class MemoRecord(BaseModel):
    id: str
    case_id: str
    title: str
    body_markdown: str
    generated_at: str


class FindingsResponse(BaseModel):
    risk_flags: list[RiskFlag]
    external_matches: list[ExternalMatch]


class TimelineResponse(BaseModel):
    timeline: list[TimelineEvent]


class AnalyzeResponse(BaseModel):
    case: CaseRecord
    documents: list[DocumentPreview]
    external_matches: list[ExternalMatch]
    risk_flags: list[RiskFlag]
    timeline: list[TimelineEvent]
    memo: MemoRecord


@dataclass
class ReferenceData:
    leie: list[dict[str, Any]]
    npi_registry: dict[str, dict[str, Any]]
    cms_benchmarks: dict[str, dict[str, Any]]


class Storage:
    def __init__(self, database_url: str) -> None:
        if database_url != ":memory:":
            Path(database_url).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(database_url, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                tip_text TEXT NOT NULL,
                status TEXT NOT NULL,
                overall_risk_score INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES cases(id)
            );

            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                canonical_name TEXT NOT NULL,
                raw_name TEXT NOT NULL,
                npi TEXT,
                taxonomy TEXT,
                address TEXT
            );

            CREATE TABLE IF NOT EXISTS claims (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                npi TEXT NOT NULL,
                procedure_code TEXT NOT NULL,
                service_date TEXT,
                amount REAL NOT NULL,
                patient_count INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS external_matches (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                source_name TEXT NOT NULL,
                match_key TEXT NOT NULL,
                match_status TEXT NOT NULL,
                summary TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS risk_flags (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                score_delta INTEGER NOT NULL,
                summary TEXT NOT NULL,
                why_flagged TEXT NOT NULL,
                external_validation TEXT NOT NULL,
                evidence_quotes TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS timeline_events (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                label TEXT NOT NULL,
                date TEXT,
                source TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS evidence_links (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                risk_flag_id TEXT NOT NULL,
                source_label TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memos (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                title TEXT NOT NULL,
                body_markdown TEXT NOT NULL,
                generated_at TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def create_case(self, payload: CreateCaseRequest) -> CaseRecord:
        case = CaseRecord(
            id=str(uuid4()),
            title=payload.title,
            tip_text=payload.tip_text,
            status="draft",
            overall_risk_score=0,
            created_at=now_iso(),
        )
        self.connection.execute(
            """
            INSERT INTO cases (id, title, tip_text, status, overall_risk_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                case.id,
                case.title,
                case.tip_text,
                case.status,
                case.overall_risk_score,
                case.created_at,
            ),
        )
        self.connection.commit()
        return case

    def get_case(self, case_id: str) -> CaseRecord:
        row = self.connection.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        if row is None:
            raise KeyError(case_id)
        return CaseRecord.model_validate(dict(row))

    def add_documents(self, case_id: str, payload: DocumentUploadRequest) -> list[DocumentPreview]:
        previews: list[DocumentPreview] = []
        for document in payload.documents:
            doc_id = str(uuid4())
            self.connection.execute(
                """
                INSERT INTO documents (id, case_id, filename, doc_type, content)
                VALUES (?, ?, ?, ?, ?)
                """,
                (doc_id, case_id, document.filename, document.doc_type, document.content),
            )
            previews.append(
                DocumentPreview(
                    id=doc_id,
                    filename=document.filename,
                    doc_type=document.doc_type,
                    preview=document.content[:160],
                )
            )
        self.connection.commit()
        return previews

    def list_documents(self, case_id: str) -> list[DocumentRecord]:
        rows = self.connection.execute(
            "SELECT * FROM documents WHERE case_id = ? ORDER BY filename ASC", (case_id,)
        ).fetchall()
        return [DocumentRecord.model_validate(dict(row)) for row in rows]

    def save_analysis(
        self,
        case_id: str,
        case_status: str,
        overall_risk_score: int,
        claims: list[dict[str, Any]],
        external_matches: list[ExternalMatch],
        risk_flags: list[RiskFlag],
        timeline: list[TimelineEvent],
        memo: MemoRecord,
    ) -> None:
        for table in ("claims", "external_matches", "risk_flags", "timeline_events", "evidence_links", "memos"):
            self.connection.execute(f"DELETE FROM {table} WHERE case_id = ?", (case_id,))

        self.connection.execute(
            "UPDATE cases SET status = ?, overall_risk_score = ? WHERE id = ?",
            (case_status, overall_risk_score, case_id),
        )

        for claim in claims:
            self.connection.execute(
                """
                INSERT INTO claims
                (id, case_id, document_id, provider_name, npi, procedure_code, service_date, amount, patient_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    claim["id"],
                    case_id,
                    claim["document_id"],
                    claim["provider_name"],
                    claim["npi"],
                    claim["procedure_code"],
                    claim["service_date"],
                    claim["amount"],
                    claim["patient_count"],
                ),
            )

        for match in external_matches:
            self.connection.execute(
                """
                INSERT INTO external_matches
                (id, case_id, source_name, match_key, match_status, summary)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    match.id,
                    match.case_id,
                    match.source_name,
                    match.match_key,
                    match.match_status,
                    match.summary,
                ),
            )

        for flag in risk_flags:
            self.connection.execute(
                """
                INSERT INTO risk_flags
                (id, case_id, severity, reason_code, score_delta, summary, why_flagged, external_validation, evidence_quotes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    flag.id,
                    flag.case_id,
                    flag.severity,
                    flag.reason_code,
                    flag.score_delta,
                    flag.summary,
                    flag.why_flagged,
                    flag.external_validation,
                    json.dumps(flag.evidence_quotes),
                ),
            )
            self.connection.execute(
                """
                INSERT INTO evidence_links (id, case_id, risk_flag_id, source_label)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    case_id,
                    flag.id,
                    flag.evidence_quotes[0] if flag.evidence_quotes else "No evidence recorded",
                ),
            )

        for event in timeline:
            self.connection.execute(
                """
                INSERT INTO timeline_events (id, case_id, label, date, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event.id, case_id, event.label, event.date, event.source),
            )

        self.connection.execute(
            """
            INSERT INTO memos (id, case_id, title, body_markdown, generated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (memo.id, case_id, memo.title, memo.body_markdown, memo.generated_at),
        )
        self.connection.commit()

    def list_external_matches(self, case_id: str) -> list[ExternalMatch]:
        rows = self.connection.execute(
            "SELECT * FROM external_matches WHERE case_id = ? ORDER BY source_name ASC", (case_id,)
        ).fetchall()
        return [ExternalMatch.model_validate(dict(row)) for row in rows]

    def list_risk_flags(self, case_id: str) -> list[RiskFlag]:
        rows = self.connection.execute(
            "SELECT * FROM risk_flags WHERE case_id = ? ORDER BY score_delta DESC, severity ASC", (case_id,)
        ).fetchall()
        flags: list[RiskFlag] = []
        for row in rows:
            payload = dict(row)
            payload["evidence_quotes"] = json.loads(payload["evidence_quotes"])
            flags.append(RiskFlag.model_validate(payload))
        return flags

    def list_timeline(self, case_id: str) -> list[TimelineEvent]:
        rows = self.connection.execute(
            "SELECT * FROM timeline_events WHERE case_id = ? ORDER BY COALESCE(date, '9999-12-31') ASC, source ASC",
            (case_id,),
        ).fetchall()
        return [TimelineEvent.model_validate(dict(row)) for row in rows]

    def get_memo(self, case_id: str) -> MemoRecord:
        row = self.connection.execute("SELECT * FROM memos WHERE case_id = ?", (case_id,)).fetchone()
        if row is None:
            raise KeyError(case_id)
        return MemoRecord.model_validate(dict(row))


def load_reference_data() -> ReferenceData:
    leie = json.loads((REFERENCE_DIR / "leie.json").read_text())
    npi_registry = json.loads((REFERENCE_DIR / "npi_registry.json").read_text())
    cms_rows = json.loads((REFERENCE_DIR / "cms_benchmarks.json").read_text())
    return ReferenceData(
        leie=leie,
        npi_registry=npi_registry,
        cms_benchmarks={row["procedure_code"]: row for row in cms_rows},
    )


def sentence_preview(text: str) -> str:
    compact = " ".join(text.split())
    return compact[:120] + ("..." if len(compact) > 120 else "")


def parse_date(text: str) -> str | None:
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    return match.group(1) if match else None


def parse_claim_rows(document: DocumentRecord) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    reader = csv.DictReader(document.content.splitlines())
    for row in reader:
        rows.append(
            {
                "id": str(uuid4()),
                "document_id": document.id,
                "provider_name": row.get("provider_name", "Unknown Provider").strip(),
                "npi": row.get("npi", "").strip(),
                "procedure_code": row.get("procedure_code", "").strip(),
                "service_date": row.get("service_date", "").strip() or None,
                "amount": float(row.get("amount", 0) or 0),
                "patient_count": int(row.get("patient_count", 0) or 0),
                "source": document.filename,
            }
        )
    return rows


def analyze_case(case: CaseRecord, documents: list[DocumentRecord], references: ReferenceData) -> dict[str, Any]:
    claims: list[dict[str, Any]] = []
    external_matches: list[ExternalMatch] = []
    risk_flags: list[RiskFlag] = []
    timeline: list[TimelineEvent] = [
        TimelineEvent(
            id=str(uuid4()),
            case_id=case.id,
            label=sentence_preview(case.tip_text),
            date=parse_date(case.tip_text),
            source="whistleblower-tip",
        )
    ]

    names_seen: set[str] = set()

    for document in documents:
        if document.doc_type == "claim_summary" or document.filename.endswith(".csv"):
            parsed_claims = parse_claim_rows(document)
            claims.extend(parsed_claims)
            for claim in parsed_claims:
                names_seen.add(claim["provider_name"].lower())
                timeline.append(
                    TimelineEvent(
                        id=str(uuid4()),
                        case_id=case.id,
                        label=(
                            f"{claim['provider_name']} billed {claim['procedure_code']} for "
                            f"${claim['amount']:.0f} across {claim['patient_count']} patients"
                        ),
                        date=claim["service_date"],
                        source=document.filename,
                    )
                )
        else:
            lowered_content = document.content.lower()
            timeline.append(
                TimelineEvent(
                    id=str(uuid4()),
                    case_id=case.id,
                    label=sentence_preview(document.content),
                    date=parse_date(document.content),
                    source=document.filename,
                )
            )
            for candidate in references.leie:
                if candidate["match_key"] in lowered_content:
                    names_seen.add(candidate["match_key"])

    # LEIE hard matches
    for candidate in references.leie:
        if candidate["match_key"] not in names_seen:
            continue
        external_matches.append(
            ExternalMatch(
                id=str(uuid4()),
                case_id=case.id,
                source_name="LEIE",
                match_key=candidate["name"],
                match_status="hit",
                summary=candidate["reason"],
            )
        )
        risk_flags.append(
            RiskFlag(
                id=str(uuid4()),
                case_id=case.id,
                severity="severe",
                reason_code="excluded_entity_match",
                score_delta=60,
                summary=f"Matched excluded entity in LEIE: {candidate['name']}",
                why_flagged="A named party in the evidence appears on the OIG exclusion list.",
                external_validation="LEIE exclusion dataset",
                evidence_quotes=[candidate["name"], "LEIE exclusion in effect"],
            )
        )

    # Claim-based enrichment and scoring
    for claim in claims:
        npi_match = references.npi_registry.get(claim["npi"])
        if npi_match:
            external_matches.append(
                ExternalMatch(
                    id=str(uuid4()),
                    case_id=case.id,
                    source_name="NPPES",
                    match_key=claim["npi"],
                    match_status="verified",
                    summary=f"Verified {npi_match['name']} ({npi_match['taxonomy_display']})",
                )
            )

        benchmark = references.cms_benchmarks.get(claim["procedure_code"])
        if benchmark and (
            claim["amount"] > benchmark["p90_amount"] or claim["patient_count"] > benchmark["p90_patient_count"]
        ):
            risk_flags.append(
                RiskFlag(
                    id=str(uuid4()),
                    case_id=case.id,
                    severity="high",
                    reason_code="abnormal_billing_percentile",
                    score_delta=20,
                    summary=f"Billing for {claim['procedure_code']} exceeds the seeded CMS benchmark",
                    why_flagged=(
                        f"Observed amount ${claim['amount']:.0f} and patient count {claim['patient_count']} "
                        f"exceed the 90th percentile reference."
                    ),
                    external_validation="Seeded CMS benchmark slice",
                    evidence_quotes=[
                        f"{claim['provider_name']} {claim['procedure_code']} ${claim['amount']:.0f}",
                        f"P90 amount ${benchmark['p90_amount']:.0f}, P90 patient count {benchmark['p90_patient_count']}",
                    ],
                )
            )

        if benchmark and npi_match and npi_match["taxonomy_code"] not in benchmark["allowed_taxonomies"]:
            risk_flags.append(
                RiskFlag(
                    id=str(uuid4()),
                    case_id=case.id,
                    severity="medium",
                    reason_code="specialty_procedure_mismatch",
                    score_delta=15,
                    summary=f"Provider specialty is unusual for {claim['procedure_code']}",
                    why_flagged="The verified provider taxonomy is outside the expected taxonomy list for the procedure.",
                    external_validation="NPPES taxonomy cross-check against CMS procedure benchmark",
                    evidence_quotes=[npi_match["taxonomy_display"], benchmark["description"]],
                )
            )

    deduped_matches = {
        (match.source_name, match.match_key, match.match_status): match for match in external_matches
    }
    deduped_flags = {(flag.reason_code, flag.summary): flag for flag in risk_flags}
    external_matches = list(deduped_matches.values())
    risk_flags = sorted(deduped_flags.values(), key=lambda item: item.score_delta, reverse=True)
    overall_risk_score = min(sum(flag.score_delta for flag in risk_flags), 100)

    memo_lines = [
        "# Draft Investigator Memo",
        "",
        f"Case: **{case.title}**",
        "",
        "## Summary",
    ]
    if risk_flags:
        memo_lines.append(
            f"The case scored **{overall_risk_score}** based on {len(risk_flags)} rule-backed findings."
        )
    else:
        memo_lines.append("No high-confidence rule matches were detected in the current evidence bundle.")
    memo_lines.extend(["", "## Findings"])
    for flag in risk_flags:
        memo_lines.append(
            f"- **{flag.summary}**. {flag.why_flagged} Source: {flag.external_validation}. "
            f"Evidence: {', '.join(flag.evidence_quotes)}."
        )
    memo_lines.extend(["", "## External Validation"])
    for match in external_matches:
        memo_lines.append(f"- {match.source_name}: {match.summary}")
    memo_lines.extend(["", "## Recommended Next Step"])
    memo_lines.append("- Validate the high-risk findings against source billing records and preserve the cited documents.")

    memo = MemoRecord(
        id=str(uuid4()),
        case_id=case.id,
        title="Draft Investigator Memo",
        body_markdown="\n".join(memo_lines),
        generated_at=now_iso(),
    )

    return {
        "status": "analyzed",
        "overall_risk_score": overall_risk_score,
        "claims": claims,
        "external_matches": external_matches,
        "risk_flags": risk_flags,
        "timeline": timeline,
        "memo": memo,
    }


def create_app() -> FastAPI:
    database_url = ":memory:" if os.getenv("PYTEST_CURRENT_TEST") else str(PROJECT_ROOT / "storage" / "fraudcopilot.db")
    storage = Storage(database_url)
    references = load_reference_data()
    app = FastAPI(title="Fraud Investigator Copilot API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/cases", response_model=CaseRecord, status_code=201)
    def create_case_endpoint(payload: CreateCaseRequest) -> CaseRecord:
        return storage.create_case(payload)

    @app.get("/cases/{case_id}", response_model=CaseRecord)
    def get_case_endpoint(case_id: str) -> CaseRecord:
        try:
            return storage.get_case(case_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Case not found") from exc

    @app.post("/cases/{case_id}/documents", status_code=201)
    def add_documents_endpoint(case_id: str, payload: DocumentUploadRequest) -> dict[str, list[DocumentPreview]]:
        try:
            storage.get_case(case_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Case not found") from exc
        previews = storage.add_documents(case_id, payload)
        return {"documents": previews}

    @app.post("/cases/{case_id}/analyze", response_model=AnalyzeResponse)
    def analyze_case_endpoint(case_id: str) -> AnalyzeResponse:
        try:
            case = storage.get_case(case_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Case not found") from exc

        documents = storage.list_documents(case_id)
        analysis = analyze_case(case, documents, references)
        storage.save_analysis(
            case_id=case_id,
            case_status=analysis["status"],
            overall_risk_score=analysis["overall_risk_score"],
            claims=analysis["claims"],
            external_matches=analysis["external_matches"],
            risk_flags=analysis["risk_flags"],
            timeline=analysis["timeline"],
            memo=analysis["memo"],
        )

        updated_case = storage.get_case(case_id)
        return AnalyzeResponse(
            case=updated_case,
            documents=[
                DocumentPreview(
                    id=document.id,
                    filename=document.filename,
                    doc_type=document.doc_type,
                    preview=document.content[:160],
                )
                for document in documents
            ],
            external_matches=storage.list_external_matches(case_id),
            risk_flags=storage.list_risk_flags(case_id),
            timeline=storage.list_timeline(case_id),
            memo=storage.get_memo(case_id),
        )

    @app.get("/cases/{case_id}/findings", response_model=FindingsResponse)
    def get_findings_endpoint(case_id: str) -> FindingsResponse:
        try:
            storage.get_case(case_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Case not found") from exc
        return FindingsResponse(
            risk_flags=storage.list_risk_flags(case_id),
            external_matches=storage.list_external_matches(case_id),
        )

    @app.get("/cases/{case_id}/timeline", response_model=TimelineResponse)
    def get_timeline_endpoint(case_id: str) -> TimelineResponse:
        try:
            storage.get_case(case_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Case not found") from exc
        return TimelineResponse(timeline=storage.list_timeline(case_id))

    @app.get("/cases/{case_id}/memo", response_model=MemoRecord)
    def get_memo_endpoint(case_id: str) -> MemoRecord:
        try:
            storage.get_case(case_id)
            return storage.get_memo(case_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Case not found") from exc

    return app


app = create_app()
