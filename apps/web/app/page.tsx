"use client";

import { useMemo, useState, useTransition } from "react";

import { CaseWorkspace, type WorkspaceCaseData } from "../src/components/case-workspace";

type IntakeMode = "suspicious" | "clean" | "custom";

type IntakeDocument = {
  filename: string;
  doc_type: string;
  content: string;
};

type IntakeRequest = {
  title: string;
  tipText: string;
  documents: IntakeDocument[];
};

const suspiciousPreset: IntakeRequest = {
  title: "Suspicious Provider Billing",
  tipText: "Whistleblower reports unusually high billing volumes for Dr. Excluded Provider.",
  documents: [
    {
      filename: "claims.csv",
      doc_type: "claim_summary",
      content:
        "npi,procedure_code,service_date,amount,patient_count,provider_name\n1234567890,99214,2025-01-01,5000,75,Dr. Excluded Provider\n"
    },
    {
      filename: "internal-note.txt",
      doc_type: "memo",
      content: "Dr. Excluded Provider coordinated billing through Apex Review Group."
    }
  ]
};

const cleanPreset: IntakeRequest = {
  title: "Routine Compliance Review",
  tipText: "Routine audit sample for Dr. Clean Provider.",
  documents: [
    {
      filename: "claims.csv",
      doc_type: "claim_summary",
      content:
        "npi,procedure_code,service_date,amount,patient_count,provider_name\n1111222233,93000,2025-01-03,180,12,Dr. Clean Provider\n"
    }
  ]
};

const customPreset: IntakeRequest = {
  title: "Custom Intake",
  tipText: "Paste the investigator tip or referral narrative here.",
  documents: [
    {
      filename: "custom-claims.csv",
      doc_type: "claim_summary",
      content:
        "npi,procedure_code,service_date,amount,patient_count,provider_name\n1234567890,99214,2025-01-01,3000,50,Dr. Custom Provider\n"
    }
  ]
};

const seededSuspiciousCase: WorkspaceCaseData = {
  title: "Suspicious Provider Billing",
  status: "analyzed",
  overallRiskScore: 95,
  documents: [
    { id: "doc-1", filename: "tip-email.txt", docType: "tip" },
    { id: "doc-2", filename: "claims.csv", docType: "claim_summary" },
    { id: "doc-3", filename: "internal-note.txt", docType: "memo" }
  ],
  findings: [
    {
      id: "flag-1",
      severity: "severe",
      summary: "Matched excluded entity in LEIE",
      whyFlagged: "A named party in the evidence appears on the OIG exclusion list.",
      externalValidation: "LEIE exclusion dataset",
      evidenceQuotes: ["Dr. Excluded Provider", "LEIE exclusion in effect"],
      source: "Local Rule"
    },
    {
      id: "flag-2",
      severity: "high",
      summary: "Billing for 99214 exceeds the seeded CMS benchmark",
      whyFlagged: "Observed amount and patient count exceed the benchmark thresholds.",
      externalValidation: "Seeded CMS benchmark slice",
      evidenceQuotes: ["$5000 billed for 99214", "75 patients"],
      source: "Local Rule"
    }
  ],
  evidenceGraph: {
    nodes: [
      { id: "entity:dr_excluded_provider", label: "Dr. Excluded Provider", type: "provider", source: "Local Rule" },
      { id: "entity:apex_review_group", label: "Apex Review Group", type: "organization", source: "LEIE" },
      { id: "procedure:99214", label: "99214", type: "procedure", source: "CMS Benchmark" }
    ],
    edges: [
      {
        id: "edge-1",
        source: "entity:dr_excluded_provider",
        target: "procedure:99214",
        relationship: "billed",
        evidence: "Dr. Excluded Provider billed 99214 for $5000.",
        sourceType: "Local Rule"
      },
      {
        id: "edge-2",
        source: "entity:dr_excluded_provider",
        target: "entity:apex_review_group",
        relationship: "related_to",
        evidence: "Internal note references Apex Review Group.",
        sourceType: "Local Rule"
      }
    ]
  },
  timeline: [
    {
      id: "evt-1",
      label: "Whistleblower reports unusually high billing volumes for Dr. Excluded Provider.",
      date: null,
      source: "whistleblower-tip"
    },
    {
      id: "evt-2",
      label: "Dr. Excluded Provider billed 99214 for $5000 across 75 patients",
      date: "2025-01-01",
      source: "claims.csv"
    },
    {
      id: "evt-3",
      label: "Internal memo references excluded contractor",
      date: "2025-01-12",
      source: "internal-note.txt"
    }
  ],
  memo: {
    title: "Draft Investigator Memo",
    body:
      "The case scored 95 based on exclusion and abnormal billing signals.\n\n" +
      "Findings:\n" +
      "- Dr. Excluded Provider matched the LEIE exclusion file.\n" +
      "- Billing for CPT/HCPCS 99214 exceeded the seeded CMS benchmark.\n\n" +
      "Recommended next step: validate the cited records and preserve the source documents.",
    source: "Local Rule"
  },
  externalMatches: [
    { id: "match-1", source: "LEIE", summary: "OIG exclusion in effect for Dr. Excluded Provider" },
    { id: "match-2", source: "NPPES", summary: "Verified NPI 1234567890 for Dr. Excluded Provider" }
  ],
  palantirInsight: {
    provider: "Palantir AIP",
    status: "not_configured",
    recommendation: "Local fallback is active. Configure Palantir AIP env vars for live triage recommendations."
  },
  palantir: {
    provider: "Palantir AIP",
    mode: "not_configured",
    stages: [
      { stage: "extract_case_facts", configured: false, status: "not_configured", latencyMs: 0 },
      { stage: "assess_risk", configured: false, status: "not_configured", latencyMs: 0 },
      { stage: "generate_memo", configured: false, status: "not_configured", latencyMs: 0 }
    ]
  }
};

const seededCleanCase: WorkspaceCaseData = {
  title: "Routine Compliance Review",
  status: "analyzed",
  overallRiskScore: 0,
  documents: [{ id: "doc-clean-1", filename: "claims.csv", docType: "claim_summary" }],
  findings: [],
  evidenceGraph: {
    nodes: [
      { id: "entity:dr_clean_provider", label: "Dr. Clean Provider", type: "provider", source: "Local Rule" },
      { id: "procedure:93000", label: "93000", type: "procedure", source: "CMS Benchmark" }
    ],
    edges: [
      {
        id: "edge-clean-1",
        source: "entity:dr_clean_provider",
        target: "procedure:93000",
        relationship: "billed",
        evidence: "Dr. Clean Provider billed 93000 for $180.",
        sourceType: "Local Rule"
      }
    ]
  },
  timeline: [
    {
      id: "evt-clean-1",
      label: "Dr. Clean Provider billed 93000 for $180 across 12 patients",
      date: "2025-01-03",
      source: "claims.csv"
    }
  ],
  memo: {
    title: "Draft Investigator Memo",
    body: "No high-confidence rule matches were detected in the current evidence bundle.",
    source: "Local Rule"
  },
  externalMatches: [
    { id: "match-clean-1", source: "NPPES", summary: "Verified NPI 1111222233 for Dr. Clean Provider" }
  ],
  palantirInsight: {
    provider: "Palantir AIP",
    status: "not_configured",
    recommendation: "Local fallback is active. Configure Palantir AIP env vars for live triage recommendations."
  },
  palantir: {
    provider: "Palantir AIP",
    mode: "not_configured",
    stages: [
      { stage: "extract_case_facts", configured: false, status: "not_configured", latencyMs: 0 },
      { stage: "assess_risk", configured: false, status: "not_configured", latencyMs: 0 },
      { stage: "generate_memo", configured: false, status: "not_configured", latencyMs: 0 }
    ]
  }
};

type AnalyzeApiResponse = {
  case: {
    title: string;
    status: string;
    overall_risk_score: number;
  };
  documents: Array<{
    id: string;
    filename: string;
    doc_type: string;
  }>;
  external_matches: Array<{
    id: string;
    source_name: string;
    summary: string;
  }>;
  risk_flags: Array<{
    id: string;
    severity: string;
    summary: string;
    why_flagged: string;
    external_validation: string;
    evidence_quotes: string[];
    source?: string;
  }>;
  evidence_graph?: {
    nodes: Array<{
      id: string;
      label: string;
      type: string;
      source: string;
    }>;
    edges: Array<{
      id: string;
      source: string;
      target: string;
      relationship: string;
      evidence: string;
      source_type: string;
    }>;
  };
  timeline: Array<{
    id: string;
    label: string;
    date: string | null;
    source: string;
  }>;
  memo: {
    title: string;
    body_markdown: string;
    source?: string;
  };
  palantir_insight?: {
    provider: string;
    status: string;
    recommendation: string;
    error_summary?: string | null;
  };
  palantir?: {
    provider: string;
    mode: string;
    stages: Array<{
      stage: string;
      configured: boolean;
      status: string;
      latency_ms: number;
      error_summary?: string | null;
      raw_response?: unknown;
    }>;
  };
};

async function postJson<TResponse>(url: string, payload: unknown): Promise<TResponse> {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return (await response.json()) as TResponse;
}

function formatModeLabel(mode: IntakeMode): string {
  if (mode === "suspicious") {
    return "suspicious preset";
  }
  if (mode === "clean") {
    return "clean preset";
  }
  return "custom intake";
}

function fallbackCaseFor(mode: IntakeMode): WorkspaceCaseData {
  return mode === "clean" ? seededCleanCase : seededSuspiciousCase;
}

function mapApiCaseToWorkspace(payload: AnalyzeApiResponse): WorkspaceCaseData {
  return {
    title: payload.case.title,
    status: payload.case.status,
    overallRiskScore: payload.case.overall_risk_score,
    documents: payload.documents.map((document) => ({
      id: document.id,
      filename: document.filename,
      docType: document.doc_type
    })),
    findings: payload.risk_flags.map((flag) => ({
      id: flag.id,
      severity: flag.severity,
      summary: flag.summary,
      whyFlagged: flag.why_flagged,
      externalValidation: flag.external_validation,
      evidenceQuotes: flag.evidence_quotes,
      source: flag.source ?? "Local Rule"
    })),
    evidenceGraph: {
      nodes: payload.evidence_graph?.nodes ?? [],
      edges:
        payload.evidence_graph?.edges.map((edge) => ({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          relationship: edge.relationship,
          evidence: edge.evidence,
          sourceType: edge.source_type
        })) ?? []
    },
    timeline: payload.timeline,
    memo: {
      title: payload.memo.title,
      body: payload.memo.body_markdown,
      source: payload.memo.source ?? "Local Rule"
    },
    externalMatches: payload.external_matches.map((match) => ({
      id: match.id,
      source: match.source_name,
      summary: match.summary
    })),
    palantirInsight: payload.palantir_insight
      ? {
          provider: payload.palantir_insight.provider,
          status: payload.palantir_insight.status,
          recommendation: payload.palantir_insight.recommendation,
          errorSummary: payload.palantir_insight.error_summary
        }
      : undefined,
    palantir: payload.palantir
      ? {
          provider: payload.palantir.provider,
          mode: payload.palantir.mode,
          stages: payload.palantir.stages.map((stage) => ({
            stage: stage.stage,
            configured: stage.configured,
            status: stage.status,
            latencyMs: stage.latency_ms,
            errorSummary: stage.error_summary,
            rawResponse: stage.raw_response
          }))
        }
      : undefined
  };
}

async function analyzeViaApi(request: IntakeRequest, forceLocal: boolean): Promise<WorkspaceCaseData> {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
  const createdCase = await postJson<{ id: string }>(`${apiBase}/cases`, {
    title: request.title,
    tip_text: request.tipText
  });

  await postJson(`${apiBase}/cases/${createdCase.id}/documents`, {
    documents: request.documents
  });

  const analysis = await postJson<AnalyzeApiResponse>(
    `${apiBase}/cases/${createdCase.id}/analyze${forceLocal ? "?force_local=true" : ""}`,
    {}
  );
  return mapApiCaseToWorkspace(analysis);
}

export default function HomePage() {
  const [isPending, startTransition] = useTransition();
  const [isLoading, setIsLoading] = useState(false);
  const [intakeMode, setIntakeMode] = useState<IntakeMode>("suspicious");
  const [customRequest, setCustomRequest] = useState<IntakeRequest>(customPreset);
  const [caseData, setCaseData] = useState<WorkspaceCaseData | null>(null);
  const [statusNote, setStatusNote] = useState<string | null>(null);
  const [backendMode, setBackendMode] = useState("not checked");
  const [palantirMode, setPalantirMode] = useState("not checked");
  const [forceLocal, setForceLocal] = useState(false);

  const activeRequest = useMemo(() => {
    if (intakeMode === "clean") {
      return cleanPreset;
    }
    if (intakeMode === "custom") {
      return customRequest;
    }
    return suspiciousPreset;
  }, [customRequest, intakeMode]);

  const updateCustomDocument = (field: keyof IntakeDocument, value: string) => {
    setCustomRequest((current) => ({
      ...current,
      documents: [
        {
          ...current.documents[0],
          [field]: value
        }
      ]
    }));
  };

  const handleModeChange = (mode: IntakeMode) => {
    setIntakeMode(mode);
    setCaseData(null);
    setStatusNote(null);
  };

  const handleAnalyze = async () => {
    setIsLoading(true);
    try {
      const apiCase = await analyzeViaApi(activeRequest, forceLocal);
      startTransition(() => {
        setCaseData(apiCase);
        setBackendMode("connected");
        setPalantirMode(apiCase.palantir?.mode ?? apiCase.palantirInsight?.status ?? "not returned");
        setStatusNote("Loaded from the local FastAPI backend.");
      });
    } catch {
      startTransition(() => {
        const fallbackCase = fallbackCaseFor(intakeMode);
        setCaseData(fallbackCase);
        setBackendMode("fallback");
        setPalantirMode(fallbackCase.palantirInsight?.status ?? "not checked");
        setStatusNote("Local API unavailable, showing a seeded fallback packet instead.");
      });
    } finally {
      setIsLoading(false);
    }
  };

  const isCustom = intakeMode === "custom";

  return (
    <main className="page-shell">
      <section className="hero">
        <div className="eyebrow">Healthcare Fraud Triage</div>
        <h1>Fraud Investigator Copilot</h1>
        <p>
          Drop in messy evidence, get back a structured case file. This MVP organizes the intake story,
          highlights public-data matches, surfaces rule-backed risk findings, adds optional Palantir AIP
          triage, and drafts an investigator memo.
        </p>
        <div className="status-strip" aria-label="Demo status">
          <span>FastAPI: {backendMode}</span>
          <span>Palantir AIP: {palantirMode}</span>
          <span>Case Source: {formatModeLabel(intakeMode)}</span>
          <label className="toggle-chip">
            <input
              checked={forceLocal}
              onChange={(event) => setForceLocal(event.target.checked)}
              type="checkbox"
            />
            Local-only
          </label>
        </div>
        <div className="hero-actions">
          <button
            className="hero-button"
            disabled={isPending || isLoading}
            onClick={() => {
              void handleAnalyze();
            }}
            type="button"
          >
            {isPending || isLoading ? "Analyzing..." : "Analyze Case"}
          </button>
          <span className="hero-hint">
            Use a preset for the live walkthrough or switch to custom intake to paste evidence.
          </span>
        </div>
        {statusNote ? <p className="hero-hint">{statusNote}</p> : null}
      </section>

      <section className="intake-console" aria-label="Evidence Intake">
        <div className="preset-controls" role="group" aria-label="Case source">
          <button
            aria-pressed={intakeMode === "suspicious"}
            className="mode-button"
            onClick={() => handleModeChange("suspicious")}
            type="button"
          >
            Suspicious Preset
          </button>
          <button
            aria-pressed={intakeMode === "clean"}
            className="mode-button"
            onClick={() => handleModeChange("clean")}
            type="button"
          >
            Clean Preset
          </button>
          <button
            aria-pressed={intakeMode === "custom"}
            className="mode-button"
            onClick={() => handleModeChange("custom")}
            type="button"
          >
            Custom Intake
          </button>
        </div>

        <div className="intake-grid">
          <label>
            Case Title
            <input
              disabled={!isCustom}
              onChange={(event) => setCustomRequest((current) => ({ ...current, title: event.target.value }))}
              value={activeRequest.title}
            />
          </label>
          <label>
            Document Filename
            <input
              disabled={!isCustom}
              onChange={(event) => updateCustomDocument("filename", event.target.value)}
              value={activeRequest.documents[0]?.filename ?? ""}
            />
          </label>
          <label>
            Document Type
            <input
              disabled={!isCustom}
              onChange={(event) => updateCustomDocument("doc_type", event.target.value)}
              value={activeRequest.documents[0]?.doc_type ?? ""}
            />
          </label>
        </div>
        <label>
          Tip Text
          <textarea
            disabled={!isCustom}
            onChange={(event) => setCustomRequest((current) => ({ ...current, tipText: event.target.value }))}
            rows={3}
            value={activeRequest.tipText}
          />
        </label>
        <label>
          Document Content
          <textarea
            disabled={!isCustom}
            onChange={(event) => updateCustomDocument("content", event.target.value)}
            rows={5}
            value={activeRequest.documents[0]?.content ?? ""}
          />
        </label>
      </section>

      {caseData ? (
        <CaseWorkspace caseData={caseData} />
      ) : (
        <section className="placeholder-card">
          <h2>Ready for Intake</h2>
          <p className="muted">
            Pick a preset for the live demo or switch to custom intake, paste evidence, and run the local API-backed
            analysis.
          </p>
        </section>
      )}
    </main>
  );
}
