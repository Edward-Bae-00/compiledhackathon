"use client";

import { useState, useTransition } from "react";

import { CaseWorkspace, type WorkspaceCaseData } from "../src/components/case-workspace";

const demoRequest = {
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

const seededDemoCase: WorkspaceCaseData = {
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
      evidenceQuotes: ["Dr. Excluded Provider", "LEIE exclusion in effect"]
    },
    {
      id: "flag-2",
      severity: "high",
      summary: "Billing for 99214 exceeds the seeded CMS benchmark",
      whyFlagged: "Observed amount and patient count exceed the benchmark thresholds.",
      externalValidation: "Seeded CMS benchmark slice",
      evidenceQuotes: ["$5000 billed for 99214", "75 patients"]
    }
  ],
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
      "Recommended next step: validate the cited records and preserve the source documents."
  },
  externalMatches: [
    { id: "match-1", source: "LEIE", summary: "OIG exclusion in effect for Dr. Excluded Provider" },
    { id: "match-2", source: "NPPES", summary: "Verified NPI 1234567890 for Dr. Excluded Provider" }
  ]
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
  }>;
  timeline: Array<{
    id: string;
    label: string;
    date: string | null;
    source: string;
  }>;
  memo: {
    title: string;
    body_markdown: string;
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
      evidenceQuotes: flag.evidence_quotes
    })),
    timeline: payload.timeline,
    memo: {
      title: payload.memo.title,
      body: payload.memo.body_markdown
    },
    externalMatches: payload.external_matches.map((match) => ({
      id: match.id,
      source: match.source_name,
      summary: match.summary
    }))
  };
}

async function analyzeViaApi(): Promise<WorkspaceCaseData> {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
  const createdCase = await postJson<{ id: string }>(`${apiBase}/cases`, {
    title: demoRequest.title,
    tip_text: demoRequest.tipText
  });

  await postJson(`${apiBase}/cases/${createdCase.id}/documents`, {
    documents: demoRequest.documents
  });

  const analysis = await postJson<AnalyzeApiResponse>(`${apiBase}/cases/${createdCase.id}/analyze`, {});
  return mapApiCaseToWorkspace(analysis);
}

export default function HomePage() {
  const [isPending, startTransition] = useTransition();
  const [isLoading, setIsLoading] = useState(false);
  const [caseData, setCaseData] = useState<WorkspaceCaseData | null>(null);
  const [statusNote, setStatusNote] = useState<string | null>(null);

  const handleAnalyze = async () => {
    setIsLoading(true);
    try {
      const apiCase = await analyzeViaApi();
      startTransition(() => {
        setCaseData(apiCase);
        setStatusNote("Loaded from the local FastAPI backend.");
      });
    } catch {
      startTransition(() => {
        setCaseData(seededDemoCase);
        setStatusNote("Local API unavailable, showing the seeded demo packet instead.");
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="page-shell">
      <section className="hero">
        <div className="eyebrow">Healthcare Fraud Triage</div>
        <h1>Fraud Investigator Copilot</h1>
        <p>
          Drop in messy evidence, get back a structured case file. This MVP organizes the intake story,
          highlights public-data matches, surfaces rule-backed risk findings, and drafts an investigator memo.
        </p>
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
            Seeded with a demo healthcare fraud packet and ready to connect to the local FastAPI backend.
          </span>
        </div>
        {statusNote ? <p className="hero-hint">{statusNote}</p> : null}
      </section>

      {caseData ? (
        <CaseWorkspace caseData={caseData} />
      ) : (
        <section className="placeholder-card">
          <h2>Ready for Intake</h2>
          <p className="muted">
            Click <strong>Analyze Case</strong> to load the seeded demo packet, or wire this page to the local
            API endpoints to analyze uploaded evidence.
          </p>
        </section>
      )}
    </main>
  );
}
