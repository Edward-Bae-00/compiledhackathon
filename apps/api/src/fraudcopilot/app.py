from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
    source: str = "Local Rule"


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
    source: str = "Local Rule"


class PalantirInsight(BaseModel):
    provider: str = "Palantir AIP"
    status: str
    recommendation: str
    error_summary: str | None = None


class PalantirStageStatus(BaseModel):
    stage: str
    configured: bool
    status: str
    latency_ms: int = 0
    error_summary: str | None = None
    raw_response: Any | None = None


class PalantirAnalysis(BaseModel):
    provider: str = "Palantir AIP"
    mode: str
    stages: list[PalantirStageStatus]


class PalantirStatusResponse(BaseModel):
    provider: str = "Palantir AIP"
    configured: bool
    reachable: bool
    mode: str
    error: str | None = None


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    source: str = "Local Rule"


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str
    evidence: str
    source_type: str = "Local Rule"


class EvidenceGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class ExtractedEntity(BaseModel):
    id: str | None = None
    entity_type: str = "unknown"
    name: str
    npi: str | None = None
    source: str = "Local Rule"


class ExtractedRelationship(BaseModel):
    source: str
    target: str
    relationship: str
    evidence: str
    source_type: str = "Local Rule"


class ExtractedFacts(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)
    claims: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)


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
    evidence_graph: EvidenceGraph
    memo: MemoRecord
    palantir_insight: PalantirInsight
    palantir: PalantirAnalysis


@dataclass
class ReferenceData:
    leie: list[dict[str, Any]]
    npi_registry: dict[str, dict[str, Any]]
    cms_benchmarks: dict[str, dict[str, Any]]


@dataclass
class PalantirAipClient:
    logic_url: str | None
    api_token: str | None
    hostname: str | None = None
    extract_facts_url: str | None = None
    assess_risk_url: str | None = None
    generate_memo_url: str | None = None
    force_local: bool = False
    timeout_seconds: float = 8

    @classmethod
    def from_env(cls) -> "PalantirAipClient":
        return cls(
            logic_url=os.getenv("PALANTIR_AIP_LOGIC_URL"),
            api_token=os.getenv("PALANTIR_API_TOKEN"),
            hostname=os.getenv("PALANTIR_HOSTNAME"),
            extract_facts_url=os.getenv("PALANTIR_AIP_EXTRACT_FACTS_URL"),
            assess_risk_url=os.getenv("PALANTIR_AIP_ASSESS_RISK_URL"),
            generate_memo_url=os.getenv("PALANTIR_AIP_GENERATE_MEMO_URL"),
            force_local=os.getenv("PALANTIR_FORCE_LOCAL", "").lower() in {"1", "true", "yes"},
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_token and self.any_url_configured and not self.force_local)

    @property
    def any_url_configured(self) -> bool:
        return bool(self.logic_url or self.extract_facts_url or self.assess_risk_url or self.generate_memo_url)

    @property
    def staged_configured(self) -> bool:
        return bool(self.api_token and (self.extract_facts_url or self.assess_risk_url or self.generate_memo_url))

    def status(self) -> PalantirStatusResponse:
        if self.force_local:
            return PalantirStatusResponse(
                configured=bool(self.api_token and self.any_url_configured),
                reachable=False,
                mode="forced_local",
            )

        if not self.configured:
            return PalantirStatusResponse(
                configured=False,
                reachable=False,
                mode="not_configured",
            )

        if not self.hostname:
            return PalantirStatusResponse(
                configured=True,
                reachable=True,
                mode="configured",
            )

        health_url = self._build_foundry_url("/api/v2/ontologies")
        request = Request(
            health_url,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response.read()
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return PalantirStatusResponse(
                configured=True,
                reachable=False,
                mode="error",
                error=self._safe_error(exc),
            )

        return PalantirStatusResponse(
            configured=True,
            reachable=True,
            mode="live",
        )

    def extract_case_facts(self, payload: dict[str, Any]) -> tuple[ExtractedFacts, PalantirStageStatus]:
        data, stage = self._run_stage("extract_case_facts", self.extract_facts_url, payload)
        if stage.status != "live" or not isinstance(data, dict):
            return ExtractedFacts(), stage

        entities = [
            ExtractedEntity(
                id=item.get("id"),
                entity_type=item.get("entity_type", "unknown"),
                name=item.get("name") or item.get("canonical_name") or item.get("label") or "Unknown Entity",
                npi=item.get("npi"),
                source=item.get("source", "Palantir AIP"),
            )
            for item in data.get("entities", [])
            if isinstance(item, dict)
        ]
        claims = [
            self._normalize_aip_claim(item)
            for item in data.get("claims", [])
            if isinstance(item, dict)
        ]
        relationships = [
            ExtractedRelationship(
                source=item.get("source", "Unknown Source"),
                target=item.get("target", "Unknown Target"),
                relationship=item.get("relationship", "related_to"),
                evidence=item.get("evidence", "Palantir AIP relationship"),
                source_type=item.get("source_type", "Palantir AIP"),
            )
            for item in data.get("relationships", [])
            if isinstance(item, dict)
        ]
        return ExtractedFacts(entities=entities, claims=claims, relationships=relationships), stage

    def assess_risk(self, payload: dict[str, Any], case_id: str) -> tuple[list[RiskFlag], PalantirStageStatus]:
        data, stage = self._run_stage("assess_risk", self.assess_risk_url, payload)
        if stage.status != "live" or not isinstance(data, dict):
            return [], stage

        flags: list[RiskFlag] = []
        for item in data.get("risk_factors", []):
            if not isinstance(item, dict):
                continue
            summary = item.get("summary") or item.get("title") or "Palantir AIP risk factor"
            flags.append(
                RiskFlag(
                    id=str(uuid4()),
                    case_id=case_id,
                    severity=item.get("severity", "medium"),
                    reason_code=item.get("reason_code") or slugify_reason(summary),
                    score_delta=int(item.get("score_delta", item.get("score", 10)) or 0),
                    summary=summary,
                    why_flagged=item.get("why_flagged") or item.get("reasoning") or "Palantir AIP returned this risk factor.",
                    external_validation=item.get("external_validation", "Palantir AIP risk assessment"),
                    evidence_quotes=[
                        str(quote)
                        for quote in item.get("evidence_quotes", item.get("evidence", []))
                    ]
                    if isinstance(item.get("evidence_quotes", item.get("evidence", [])), list)
                    else [str(item.get("evidence_quotes", item.get("evidence", "Palantir AIP evidence")))],
                    source="Palantir AIP",
                )
            )
        return flags, stage

    def generate_memo(self, payload: dict[str, Any], case_id: str) -> tuple[MemoRecord | None, str | None, PalantirStageStatus]:
        data, stage = self._run_stage("generate_memo", self.generate_memo_url, payload)
        if stage.status != "live" or not isinstance(data, dict):
            return None, None, stage

        body = data.get("memo_markdown") or data.get("memo") or data.get("body_markdown") or data.get("result")
        recommendation = data.get("recommendation") or data.get("recommended_action") or data.get("next_step")
        if not isinstance(body, str) or not body.strip():
            return None, recommendation if isinstance(recommendation, str) else None, stage

        return (
            MemoRecord(
                id=str(uuid4()),
                case_id=case_id,
                title=data.get("title", "AIP Investigator Memo"),
                body_markdown=body.strip(),
                generated_at=now_iso(),
                source="Palantir AIP",
            ),
            recommendation if isinstance(recommendation, str) else None,
            stage,
        )

    def generate_insight(self, payload: dict[str, Any]) -> PalantirInsight:
        if self.force_local:
            return PalantirInsight(
                status="forced_local",
                recommendation="Palantir AIP calls are disabled for this run. Local deterministic findings are shown.",
            )

        if not self.logic_url or not self.api_token:
            return PalantirInsight(
                status="not_configured",
                recommendation=(
                    "Set PALANTIR_AIP_LOGIC_URL and PALANTIR_API_TOKEN to enable live Palantir AIP "
                    "triage. Local deterministic findings remain available for the demo."
                ),
            )

        request_body = json.dumps(
            {
                **payload,
                "case_file_json": json.dumps(payload),
            }
        ).encode()
        request = Request(
            self.logic_url or "",
            data=request_body,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode()
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return PalantirInsight(
                status="error",
                recommendation=(
                    "Palantir AIP is configured but unavailable. Continue the live demo with the local "
                    "rule-backed analysis and retry the Palantir handoff after checking credentials and endpoint access."
                ),
                error_summary=self._safe_error(exc),
            )

        return PalantirInsight(
            status="live",
            recommendation=self._extract_recommendation(body),
        )

    def build_analysis(self, stages: list[PalantirStageStatus]) -> PalantirAnalysis:
        if self.force_local:
            mode = "forced_local"
        elif not self.configured and not self.staged_configured:
            mode = "not_configured"
        elif any(stage.status == "live" for stage in stages) and any(stage.status == "error" for stage in stages):
            mode = "partial"
        elif any(stage.status == "live" for stage in stages):
            mode = "live"
        elif any(stage.status == "error" for stage in stages):
            mode = "error"
        else:
            mode = "configured" if self.staged_configured else "not_configured"
        return PalantirAnalysis(mode=mode, stages=stages)

    def _run_stage(self, stage_name: str, url: str | None, payload: dict[str, Any]) -> tuple[Any | None, PalantirStageStatus]:
        if self.force_local:
            return None, PalantirStageStatus(stage=stage_name, configured=bool(url), status="forced_local")
        if not url or not self.api_token:
            return None, PalantirStageStatus(stage=stage_name, configured=False, status="not_configured")

        request_body = json.dumps(
            {
                **payload,
                "case_file_json": json.dumps(payload),
            }
        ).encode()
        request = Request(
            url,
            data=request_body,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        start = perf_counter()
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode()
            parsed = self._parse_response_body(body)
            return parsed, PalantirStageStatus(
                stage=stage_name,
                configured=True,
                status="live",
                latency_ms=int((perf_counter() - start) * 1000),
                raw_response=parsed,
            )
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return None, PalantirStageStatus(
                stage=stage_name,
                configured=True,
                status="error",
                latency_ms=int((perf_counter() - start) * 1000),
                error_summary=self._safe_error(exc),
            )

    def _normalize_aip_claim(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(uuid4()),
            "document_id": item.get("document_id", "palantir-aip"),
            "provider_name": str(item.get("provider_name") or item.get("provider") or "Unknown Provider").strip(),
            "npi": str(item.get("npi", "") or "").strip(),
            "procedure_code": str(item.get("procedure_code") or item.get("code") or "").strip(),
            "service_date": item.get("service_date"),
            "amount": float(item.get("amount", 0) or 0),
            "patient_count": int(item.get("patient_count", 0) or 0),
            "source": item.get("source", "Palantir AIP"),
        }

    def _build_foundry_url(self, path: str) -> str:
        hostname = self.hostname or ""
        base_url = hostname if hostname.startswith(("http://", "https://")) else f"https://{hostname}"
        return f"{base_url.rstrip('/')}{path}"

    def _extract_recommendation(self, body: str) -> str:
        text = body.strip()
        if not text:
            return "Palantir AIP returned an empty response."

        payload = self._parse_response_body(text)
        if isinstance(payload, dict):
            for key in ("recommendation", "result", "output", "text", "message"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            return json.dumps(payload, sort_keys=True)

        if isinstance(payload, str):
            return payload

        return json.dumps(payload, sort_keys=True)

    def _parse_response_body(self, body: str) -> Any:
        text = body.strip()
        if not text:
            return ""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def _safe_error(self, exc: BaseException) -> str:
        if isinstance(exc, HTTPError):
            return f"HTTP {exc.code}"
        if isinstance(exc, URLError):
            reason = getattr(exc, "reason", exc)
            return f"{type(exc).__name__}: {reason}"
        return type(exc).__name__


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
                evidence_quotes TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'Local Rule'
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
                generated_at TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'Local Rule'
            );
            """
        )
        self._ensure_column("risk_flags", "source", "TEXT NOT NULL DEFAULT 'Local Rule'")
        self._ensure_column("memos", "source", "TEXT NOT NULL DEFAULT 'Local Rule'")
        self.connection.commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        columns = {
            row["name"]
            for row in self.connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

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
                (id, case_id, severity, reason_code, score_delta, summary, why_flagged, external_validation, evidence_quotes, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    flag.source,
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
            INSERT INTO memos (id, case_id, title, body_markdown, generated_at, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (memo.id, case_id, memo.title, memo.body_markdown, memo.generated_at, memo.source),
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


def entity_node_id(label: str) -> str:
    return f"entity:{slugify_reason(label) or str(uuid4())}"


def procedure_node_id(code: str) -> str:
    return f"procedure:{slugify_reason(code) or str(uuid4())}"


def reference_node_id(label: str) -> str:
    return f"reference:{slugify_reason(label) or str(uuid4())}"


def parse_text_claim_rows(document: DocumentRecord) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"(?P<provider>Dr\.\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})\s+"
        r"NPI\s+(?P<npi>\d{10})\s+billed\s+(?P<procedure_code>[A-Z]?\d{4,5})\s+"
        r"for\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+across\s+(?P<patient_count>\d+)\s+patients",
        re.IGNORECASE,
    )
    rows: list[dict[str, Any]] = []
    for match in pattern.finditer(document.content):
        provider_name = " ".join(match.group("provider").split())
        rows.append(
            {
                "id": str(uuid4()),
                "document_id": document.id,
                "provider_name": provider_name,
                "npi": match.group("npi"),
                "procedure_code": match.group("procedure_code").upper(),
                "service_date": parse_date(document.content),
                "amount": float(match.group("amount").replace(",", "")),
                "patient_count": int(match.group("patient_count")),
                "source": document.filename,
            }
        )
    return rows


def parse_text_relationships(document: DocumentRecord, claims: list[dict[str, Any]]) -> list[ExtractedRelationship]:
    relationships: list[ExtractedRelationship] = []
    provider_name = claims[0]["provider_name"] if claims else "Unknown Provider"
    management_match = re.search(
        r"(?P<org>[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,4})\s+managed billing",
        document.content,
    )
    if management_match:
        relationships.append(
            ExtractedRelationship(
                source=provider_name,
                target=" ".join(management_match.group("org").split()),
                relationship="managed_by",
                evidence=sentence_preview(document.content),
                source_type="Local Rule",
            )
        )
    return relationships


def add_node(nodes: dict[str, GraphNode], label: str, node_type: str, source: str = "Local Rule") -> str:
    node_id = entity_node_id(label) if node_type != "procedure" else procedure_node_id(label)
    existing = nodes.get(node_id)
    if existing is None or existing.source == "Local Rule":
        nodes[node_id] = GraphNode(id=node_id, label=label, type=node_type, source=source)
    return node_id


def add_edge(
    edges: dict[tuple[str, str, str], GraphEdge],
    source_id: str,
    target_id: str,
    relationship: str,
    evidence: str,
    source_type: str = "Local Rule",
) -> None:
    key = (source_id, target_id, relationship)
    if key not in edges:
        edges[key] = GraphEdge(
            id=str(uuid4()),
            source=source_id,
            target=target_id,
            relationship=relationship,
            evidence=evidence,
            source_type=source_type,
        )


def build_evidence_graph(
    documents: list[DocumentRecord],
    claims: list[dict[str, Any]],
    external_matches: list[ExternalMatch],
    entities: list[ExtractedEntity],
    relationships: list[ExtractedRelationship],
) -> EvidenceGraph:
    nodes: dict[str, GraphNode] = {}
    edges: dict[tuple[str, str, str], GraphEdge] = {}

    document_nodes: dict[str, str] = {}
    for document in documents:
        doc_id = f"document:{document.id}"
        document_nodes[document.id] = doc_id
        nodes[doc_id] = GraphNode(id=doc_id, label=document.filename, type="document", source="Local Rule")

    for entity in entities:
        add_node(nodes, entity.name, entity.entity_type, entity.source)

    for claim in claims:
        provider_id = add_node(nodes, claim["provider_name"], "provider", claim.get("source", "Local Rule"))
        procedure_id = add_node(nodes, claim["procedure_code"], "procedure", "CMS Benchmark")
        add_edge(
            edges,
            provider_id,
            procedure_id,
            "billed",
            f"{claim['provider_name']} billed {claim['procedure_code']} for ${claim['amount']:.0f}",
            claim.get("source", "Local Rule"),
        )
        document_id = claim.get("document_id")
        if document_id in document_nodes:
            add_edge(
                edges,
                document_nodes[document_id],
                provider_id,
                "mentions",
                f"{claim['provider_name']} appears in {claim.get('source', 'evidence')}",
                "Local Rule",
            )

    for relationship in relationships:
        source_id = add_node(nodes, relationship.source, "provider", relationship.source_type)
        target_id = add_node(nodes, relationship.target, "organization", relationship.source_type)
        add_edge(
            edges,
            source_id,
            target_id,
            relationship.relationship,
            relationship.evidence,
            relationship.source_type,
        )

    for match in external_matches:
        match_id = reference_node_id(match.source_name)
        nodes[match_id] = GraphNode(id=match_id, label=match.source_name, type="reference", source=match.source_name)
        matched_entity_id = add_node(nodes, match.match_key, "entity", match.source_name)
        add_edge(
            edges,
            matched_entity_id,
            match_id,
            "matched",
            match.summary,
            match.source_name,
        )

    return EvidenceGraph(nodes=list(nodes.values()), edges=list(edges.values()))


def build_local_memo(
    case: CaseRecord,
    risk_flags: list[RiskFlag],
    external_matches: list[ExternalMatch],
    overall_risk_score: int,
) -> MemoRecord:
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

    return MemoRecord(
        id=str(uuid4()),
        case_id=case.id,
        title="Draft Investigator Memo",
        body_markdown="\n".join(memo_lines),
        generated_at=now_iso(),
    )


def analyze_case(
    case: CaseRecord,
    documents: list[DocumentRecord],
    references: ReferenceData,
    aip_facts: ExtractedFacts | None = None,
) -> dict[str, Any]:
    claims: list[dict[str, Any]] = []
    entities: list[ExtractedEntity] = []
    relationships: list[ExtractedRelationship] = []
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
                entities.append(
                    ExtractedEntity(
                        entity_type="provider",
                        name=claim["provider_name"],
                        npi=claim["npi"],
                    )
                )
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
            parsed_claims = parse_text_claim_rows(document)
            claims.extend(parsed_claims)
            for claim in parsed_claims:
                names_seen.add(claim["provider_name"].lower())
                entities.append(
                    ExtractedEntity(
                        entity_type="provider",
                        name=claim["provider_name"],
                        npi=claim["npi"],
                    )
                )
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
            relationships.extend(parse_text_relationships(document, parsed_claims))
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
                    entities.append(
                        ExtractedEntity(
                            entity_type=candidate["entity_type"],
                            name=candidate["name"],
                        )
                    )

    if aip_facts:
        claims.extend(aip_facts.claims)
        entities.extend(aip_facts.entities)
        relationships.extend(aip_facts.relationships)
        for claim in aip_facts.claims:
            names_seen.add(claim["provider_name"].lower())
            timeline.append(
                TimelineEvent(
                    id=str(uuid4()),
                    case_id=case.id,
                    label=(
                        f"Palantir AIP extracted {claim['provider_name']} billing {claim['procedure_code']} "
                        f"for ${claim['amount']:.0f}"
                    ),
                    date=claim.get("service_date"),
                    source=claim.get("source", "Palantir AIP"),
                )
            )
        for relationship in aip_facts.relationships:
            names_seen.add(relationship.source.lower())
            names_seen.add(relationship.target.lower())

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
        elif claim["npi"]:
            risk_flags.append(
                RiskFlag(
                    id=str(uuid4()),
                    case_id=case.id,
                    severity="medium",
                    reason_code="unknown_npi",
                    score_delta=12,
                    summary=f"NPI {claim['npi']} was not found in the seeded NPPES registry",
                    why_flagged="The claim references an NPI that the local reference slice cannot verify.",
                    external_validation="Seeded NPPES registry lookup",
                    evidence_quotes=[f"{claim['provider_name']} NPI {claim['npi']}"],
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

        amount_volume_threshold = max(5000, (benchmark["p90_amount"] * 2) if benchmark else 5000)
        patient_volume_threshold = max(75, (benchmark["p90_patient_count"] * 2) if benchmark else 75)
        if claim["amount"] >= amount_volume_threshold or claim["patient_count"] >= patient_volume_threshold:
            risk_flags.append(
                RiskFlag(
                    id=str(uuid4()),
                    case_id=case.id,
                    severity="high",
                    reason_code="high_claim_volume",
                    score_delta=18,
                    summary=f"Claim volume for {claim['provider_name']} is materially above demo thresholds",
                    why_flagged=(
                        f"Observed ${claim['amount']:.0f} and {claim['patient_count']} patients exceed "
                        "the local high-volume triage threshold."
                    ),
                    external_validation="Local high-volume triage rule",
                    evidence_quotes=[
                        f"{claim['provider_name']} billed ${claim['amount']:.0f}",
                        f"{claim['patient_count']} patients",
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

    suspicious_relationships = [
        relationship
        for relationship in relationships
        if relationship.relationship in {"managed_by", "billing_management", "referral_control"}
        or any(keyword in relationship.evidence.lower() for keyword in ("managed billing", "referral", "ownership"))
    ]
    for relationship in suspicious_relationships:
        risk_flags.append(
            RiskFlag(
                id=str(uuid4()),
                case_id=case.id,
                severity="medium",
                reason_code="suspicious_relationship_language",
                score_delta=15,
                summary=f"Evidence links {relationship.source} to {relationship.target}",
                why_flagged="The evidence describes a management, billing, or referral relationship that warrants network review.",
                external_validation=f"{relationship.source_type} relationship extraction",
                evidence_quotes=[relationship.evidence],
                source=relationship.source_type,
            )
        )

    deduped_matches = {
        (match.source_name, match.match_key, match.match_status): match for match in external_matches
    }
    deduped_flags = {(flag.source, flag.reason_code, flag.summary): flag for flag in risk_flags}
    external_matches = list(deduped_matches.values())
    risk_flags = sorted(deduped_flags.values(), key=lambda item: item.score_delta, reverse=True)
    overall_risk_score = min(sum(flag.score_delta for flag in risk_flags), 100)
    evidence_graph = build_evidence_graph(documents, claims, external_matches, entities, relationships)

    memo = build_local_memo(case, risk_flags, external_matches, overall_risk_score)

    return {
        "status": "analyzed",
        "overall_risk_score": overall_risk_score,
        "claims": claims,
        "external_matches": external_matches,
        "risk_flags": risk_flags,
        "timeline": timeline,
        "evidence_graph": evidence_graph,
        "memo": memo,
    }


def build_palantir_case_file(
    case: CaseRecord,
    documents: list[DocumentRecord],
    external_matches: list[ExternalMatch],
    risk_flags: list[RiskFlag],
    timeline: list[TimelineEvent],
    evidence_graph: EvidenceGraph,
    memo: MemoRecord,
) -> dict[str, Any]:
    return {
        "case": case.model_dump(),
        "documents": [
            {
                "id": document.id,
                "filename": document.filename,
                "doc_type": document.doc_type,
                "preview": sentence_preview(document.content),
            }
            for document in documents
        ],
        "external_matches": [match.model_dump() for match in external_matches],
        "risk_flags": [flag.model_dump() for flag in risk_flags],
        "timeline": [event.model_dump() for event in timeline],
        "evidence_graph": evidence_graph.model_dump(),
        "memo": memo.model_dump(),
    }


def build_palantir_intake_file(case: CaseRecord, documents: list[DocumentRecord]) -> dict[str, Any]:
    return {
        "case": case.model_dump(),
        "documents": [
            {
                "id": document.id,
                "filename": document.filename,
                "doc_type": document.doc_type,
                "content": document.content,
            }
            for document in documents
        ],
    }


def merge_risk_flags(flags: list[RiskFlag]) -> list[RiskFlag]:
    deduped = {(flag.source, flag.reason_code, flag.summary): flag for flag in flags}
    return sorted(deduped.values(), key=lambda item: item.score_delta, reverse=True)


def score_risk_flags(flags: list[RiskFlag]) -> int:
    return min(sum(flag.score_delta for flag in flags), 100)


def build_palantir_insight(
    palantir_analysis: PalantirAnalysis,
    recommendation: str | None,
    legacy_insight: PalantirInsight | None = None,
) -> PalantirInsight:
    if legacy_insight:
        return legacy_insight
    if recommendation:
        return PalantirInsight(status="live", recommendation=recommendation)
    if palantir_analysis.mode == "live":
        return PalantirInsight(
            status="live",
            recommendation="Palantir AIP stages completed. Review AIP badges in the findings, graph, and memo panels.",
        )
    if palantir_analysis.mode == "partial":
        errors = [
            f"{stage.stage}: {stage.error_summary}"
            for stage in palantir_analysis.stages
            if stage.status == "error" and stage.error_summary
        ]
        return PalantirInsight(
            status="partial",
            recommendation="Palantir AIP returned partial enrichment. Local deterministic findings remain available.",
            error_summary="; ".join(errors) if errors else None,
        )
    if palantir_analysis.mode == "error":
        errors = [
            f"{stage.stage}: {stage.error_summary}"
            for stage in palantir_analysis.stages
            if stage.error_summary
        ]
        return PalantirInsight(
            status="error",
            recommendation=(
                "Palantir AIP is configured but unavailable. Continue the demo with local analysis and retry after checking credentials."
            ),
            error_summary="; ".join(errors) if errors else None,
        )
    if palantir_analysis.mode == "forced_local":
        return PalantirInsight(
            status="forced_local",
            recommendation="Palantir AIP calls are disabled for this run. Local deterministic findings are shown.",
        )
    return PalantirInsight(
        status="not_configured",
        recommendation=(
            "Set PALANTIR_AIP_LOGIC_URL for legacy insight mode, or set PALANTIR_AIP_EXTRACT_FACTS_URL, "
            "PALANTIR_AIP_ASSESS_RISK_URL, PALANTIR_AIP_GENERATE_MEMO_URL, and PALANTIR_API_TOKEN "
            "to enable staged Palantir AIP analysis."
        ),
    )


def create_app() -> FastAPI:
    database_url = ":memory:" if os.getenv("PYTEST_CURRENT_TEST") else str(PROJECT_ROOT / "storage" / "fraudcopilot.db")
    storage = Storage(database_url)
    references = load_reference_data()
    palantir = PalantirAipClient.from_env()
    app = FastAPI(title="Fraud Investigator Copilot API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/integrations/palantir/status", response_model=PalantirStatusResponse)
    def palantir_status_endpoint() -> PalantirStatusResponse:
        return palantir.status()

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
    def analyze_case_endpoint(case_id: str, force_local: bool = False) -> AnalyzeResponse:
        try:
            case = storage.get_case(case_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Case not found") from exc

        documents = storage.list_documents(case_id)
        active_palantir = replace(palantir, force_local=True) if force_local else palantir
        aip_facts, extract_stage = active_palantir.extract_case_facts(build_palantir_intake_file(case, documents))
        analysis = analyze_case(case, documents, references, aip_facts)
        working_case = case.model_copy(
            update={
                "status": analysis["status"],
                "overall_risk_score": analysis["overall_risk_score"],
            }
        )

        risk_payload = build_palantir_case_file(
            case=working_case,
            documents=documents,
            external_matches=analysis["external_matches"],
            risk_flags=analysis["risk_flags"],
            timeline=analysis["timeline"],
            evidence_graph=analysis["evidence_graph"],
            memo=analysis["memo"],
        )
        aip_risk_flags, risk_stage = active_palantir.assess_risk(risk_payload, case_id)
        if aip_risk_flags:
            analysis["risk_flags"] = merge_risk_flags([*analysis["risk_flags"], *aip_risk_flags])
            analysis["overall_risk_score"] = score_risk_flags(analysis["risk_flags"])
            analysis["memo"] = build_local_memo(
                case,
                analysis["risk_flags"],
                analysis["external_matches"],
                analysis["overall_risk_score"],
            )
            working_case = case.model_copy(
                update={
                    "status": analysis["status"],
                    "overall_risk_score": analysis["overall_risk_score"],
                }
            )

        memo_payload = build_palantir_case_file(
            case=working_case,
            documents=documents,
            external_matches=analysis["external_matches"],
            risk_flags=analysis["risk_flags"],
            timeline=analysis["timeline"],
            evidence_graph=analysis["evidence_graph"],
            memo=analysis["memo"],
        )
        aip_memo, aip_recommendation, memo_stage = active_palantir.generate_memo(memo_payload, case_id)
        if aip_memo:
            analysis["memo"] = aip_memo

        palantir_analysis = active_palantir.build_analysis([extract_stage, risk_stage, memo_stage])
        legacy_insight: PalantirInsight | None = None
        if (
            not active_palantir.staged_configured
            and active_palantir.logic_url
            and active_palantir.api_token
            and not active_palantir.force_local
        ):
            legacy_insight = active_palantir.generate_insight(memo_payload)
            palantir_analysis = PalantirAnalysis(
                mode=legacy_insight.status,
                stages=[
                    PalantirStageStatus(
                        stage="legacy_insight",
                        configured=True,
                        status=legacy_insight.status,
                        error_summary=legacy_insight.error_summary,
                    )
                ],
            )
        palantir_insight = build_palantir_insight(palantir_analysis, aip_recommendation, legacy_insight)

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
        external_matches = storage.list_external_matches(case_id)
        risk_flags = storage.list_risk_flags(case_id)
        timeline = storage.list_timeline(case_id)
        memo = storage.get_memo(case_id)
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
            external_matches=external_matches,
            risk_flags=risk_flags,
            timeline=timeline,
            evidence_graph=analysis["evidence_graph"],
            memo=memo,
            palantir_insight=palantir_insight,
            palantir=palantir_analysis,
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
