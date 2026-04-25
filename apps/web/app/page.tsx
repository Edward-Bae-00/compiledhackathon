"use client";

import { type ChangeEvent, useMemo, useState, useTransition } from "react";

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

const claimColumns = ["npi", "procedure_code", "service_date", "amount", "patient_count", "provider_name"] as const;

type ClaimColumn = (typeof claimColumns)[number];
type ClaimRow = Record<ClaimColumn, string>;

const headerAliases: Record<string, ClaimColumn> = {
  amount: "amount",
  billed: "amount",
  billed_amount: "amount",
  billed_charge: "amount",
  charge: "amount",
  charges: "amount",
  claim_amount: "amount",
  cost: "amount",
  cpt: "procedure_code",
  cpt_code: "procedure_code",
  date: "service_date",
  doctor: "provider_name",
  hcpcs: "procedure_code",
  hcpcs_code: "procedure_code",
  national_provider_identifier: "npi",
  npi: "npi",
  patient_count: "patient_count",
  patient_volume: "patient_count",
  patients: "patient_count",
  physician: "provider_name",
  procedure: "procedure_code",
  procedure_code: "procedure_code",
  provider: "provider_name",
  provider_name: "provider_name",
  provider_npi: "npi",
  service_date: "service_date",
  total_amount: "amount"
};

type FormattedEvidenceFile = {
  document: IntakeDocument;
  rowCount: number;
};

function emptyClaimRow(): ClaimRow {
  return {
    npi: "",
    procedure_code: "",
    service_date: "",
    amount: "",
    patient_count: "",
    provider_name: ""
  };
}

function stripBom(value: string): string {
  return value.replace(/^\uFEFF/, "");
}

function slugHeader(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, "_")
    .replace(/[^a-z0-9_]/g, "");
}

function canonicalColumn(value: string): ClaimColumn | null {
  return headerAliases[slugHeader(value)] ?? null;
}

function ensureCsvFilename(filename: string): string {
  const safeName = filename.trim() || "uploaded-claims";
  return safeName.replace(/\.[^.]+$/, "") + ".csv";
}

function normalizeMoney(value: string): string {
  return value.replace(/[$,\s]/g, "");
}

function normalizeInteger(value: string): string {
  const match = value.replace(/,/g, "").match(/\d+/);
  return match?.[0] ?? "";
}

function normalizeDate(value: string): string {
  const trimmed = value.trim();
  const slashDate = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!slashDate) {
    return trimmed;
  }
  const [, month, day, year] = slashDate;
  return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
}

function normalizeClaimRow(row: ClaimRow): ClaimRow {
  return {
    npi: row.npi.replace(/\D/g, "").slice(0, 10),
    procedure_code: row.procedure_code.trim().toUpperCase(),
    service_date: normalizeDate(row.service_date),
    amount: normalizeMoney(row.amount),
    patient_count: normalizeInteger(row.patient_count),
    provider_name: row.provider_name.trim()
  };
}

function hasClaimValue(row: ClaimRow): boolean {
  return claimColumns.some((column) => row[column].trim().length > 0);
}

function parseDelimitedRows(content: string, delimiter: "," | "\t"): string[][] {
  const rows: string[][] = [];
  let currentRow: string[] = [];
  let currentCell = "";
  let inQuotes = false;

  for (let index = 0; index < content.length; index += 1) {
    const character = content[index];
    const nextCharacter = content[index + 1];

    if (character === "\"") {
      if (inQuotes && nextCharacter === "\"") {
        currentCell += "\"";
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (character === delimiter && !inQuotes) {
      currentRow.push(currentCell);
      currentCell = "";
    } else if ((character === "\n" || character === "\r") && !inQuotes) {
      if (character === "\r" && nextCharacter === "\n") {
        index += 1;
      }
      currentRow.push(currentCell);
      if (currentRow.some((cell) => cell.trim().length > 0)) {
        rows.push(currentRow);
      }
      currentRow = [];
      currentCell = "";
    } else {
      currentCell += character;
    }
  }

  currentRow.push(currentCell);
  if (currentRow.some((cell) => cell.trim().length > 0)) {
    rows.push(currentRow);
  }

  return rows;
}

function parseDelimitedClaims(content: string): ClaimRow[] {
  const cleaned = stripBom(content);
  const firstLine = cleaned.split(/\r?\n/, 1)[0] ?? "";
  const delimiter: "," | "\t" = firstLine.includes("\t") ? "\t" : ",";
  const rows = parseDelimitedRows(cleaned, delimiter);
  const [headers, ...dataRows] = rows;
  if (!headers) {
    return [];
  }

  const mappedHeaders = headers.map((header) => canonicalColumn(header));
  if (!mappedHeaders.some(Boolean)) {
    return [];
  }

  return dataRows
    .map((cells) => {
      const claimRow = emptyClaimRow();
      mappedHeaders.forEach((column, index) => {
        if (column) {
          claimRow[column] = cells[index]?.trim() ?? "";
        }
      });
      return normalizeClaimRow(claimRow);
    })
    .filter(hasClaimValue);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function jsonRowsFromValue(value: unknown): unknown[] {
  if (Array.isArray(value)) {
    return value;
  }
  if (!isRecord(value)) {
    return [];
  }

  for (const key of ["claims", "rows", "records", "data"]) {
    const nestedValue = value[key];
    if (Array.isArray(nestedValue)) {
      return nestedValue;
    }
  }

  return [value];
}

function parseJsonClaims(content: string): ClaimRow[] {
  try {
    return jsonRowsFromValue(JSON.parse(stripBom(content)))
      .filter(isRecord)
      .map((record) => {
        const claimRow = emptyClaimRow();
        Object.entries(record).forEach(([key, value]) => {
          const column = canonicalColumn(key);
          if (column && value !== null && value !== undefined) {
            claimRow[column] = String(value);
          }
        });
        return normalizeClaimRow(claimRow);
      })
      .filter(hasClaimValue);
  } catch {
    return [];
  }
}

function extractProviderName(text: string): string {
  const labeledProvider = text.match(
    /(?:provider|physician|doctor)\s*(?:name)?\s*[:#-]\s*([A-Z][A-Za-z.' -]{2,80})/i
  );
  if (labeledProvider?.[1]) {
    return labeledProvider[1].trim();
  }
  const doctorName = text.match(/\bDr\.\s+[A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*){0,4}/);
  return doctorName?.[0].trim() ?? "";
}

function parsePlainTextClaim(text: string): ClaimRow {
  const claimRow = emptyClaimRow();
  const npi = text.match(/\b\d{10}\b/);
  const procedure =
    text.match(/(?:procedure|cpt|hcpcs)(?:\s*code)?\s*[:#-]?\s*([A-Z]?\d{4,5})/i) ??
    text.match(/\b([A-Z]\d{4}|\d{5})\b/);
  const serviceDate = text.match(/\b\d{4}-\d{2}-\d{2}\b/) ?? text.match(/\b\d{1,2}\/\d{1,2}\/\d{4}\b/);
  const labeledAmount = text.match(/(?:amount|billed|paid|charge|charges)\D{0,20}(\$?\s*\d[\d,]*(?:\.\d{1,2})?)/i);
  const dollarAmount = text.match(/\$\s*\d[\d,]*(?:\.\d{1,2})?/);
  const patientCount = text.match(/(\d[\d,]*)\s+patients?\b/i) ?? text.match(/patient[_\s-]*count\D{0,12}(\d[\d,]*)/i);

  claimRow.npi = npi?.[0] ?? "";
  claimRow.procedure_code = procedure?.[1] ?? "";
  claimRow.service_date = serviceDate?.[0] ?? "";
  claimRow.amount = labeledAmount?.[1] ?? dollarAmount?.[0] ?? "";
  claimRow.patient_count = patientCount?.[1] ?? "";
  claimRow.provider_name = extractProviderName(text);

  return normalizeClaimRow(claimRow);
}

function parsePlainTextClaims(content: string): ClaimRow[] {
  const candidateLines = content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => /(?:npi|provider|doctor|physician|procedure|cpt|hcpcs|billed|amount|patients?|\$\s*\d)/i.test(line));

  const claims = (candidateLines.length > 0 ? candidateLines : [content])
    .map(parsePlainTextClaim)
    .filter(hasClaimValue);

  return claims.length > 0 ? claims : [];
}

function csvEscape(value: string): string {
  if (/[",\r\n]/.test(value)) {
    return `"${value.replace(/"/g, "\"\"")}"`;
  }
  return value;
}

function toClaimSummaryCsv(rows: ClaimRow[]): string {
  const header = claimColumns.join(",");
  const body = rows.map((row) => claimColumns.map((column) => csvEscape(row[column])).join(","));
  return [header, ...body].join("\n") + "\n";
}

function formatUploadedEvidence(filename: string, content: string): FormattedEvidenceFile {
  const trimmedContent = stripBom(content).trim();
  const parsedRows =
    filename.toLowerCase().endsWith(".json") || trimmedContent.startsWith("{") || trimmedContent.startsWith("[")
      ? parseJsonClaims(content)
      : [];
  const rows = parsedRows.length > 0 ? parsedRows : parseDelimitedClaims(content);
  const fallbackRows = rows.length > 0 ? rows : parsePlainTextClaims(content);

  return {
    document: {
      filename: ensureCsvFilename(filename),
      doc_type: "claim_summary",
      content: toClaimSummaryCsv(fallbackRows)
    },
    rowCount: fallbackRows.length
  };
}

async function readUploadedFile(file: File): Promise<string> {
  if (typeof file.text === "function") {
    return file.text();
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => resolve(String(reader.result ?? "")));
    reader.addEventListener("error", () => reject(reader.error ?? new Error("Unable to read file.")));
    reader.readAsText(file);
  });
}

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
  const [fileStatus, setFileStatus] = useState<string | null>(null);
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
      documents:
        current.documents.length > 0
          ? current.documents.map((document, index) => (index === 0 ? { ...document, [field]: value } : document))
          : [{ ...customPreset.documents[0], [field]: value }]
    }));
  };

  const handleModeChange = (mode: IntakeMode) => {
    setIntakeMode(mode);
    setCaseData(null);
    setStatusNote(null);
    setFileStatus(null);
  };

  const handleEvidenceFileUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (files.length === 0) {
      return;
    }

    try {
      const formattedFiles = await Promise.all(
        files.map(async (file) => formatUploadedEvidence(file.name, await readUploadedFile(file)))
      );
      const totalRows = formattedFiles.reduce((sum, file) => sum + file.rowCount, 0);
      setCustomRequest((current) => ({
        ...current,
        documents: formattedFiles.map((file) => file.document)
      }));
      setFileStatus(
        totalRows > 0
          ? `Formatted ${files.length} file${files.length === 1 ? "" : "s"} into ${totalRows} claim row${
              totalRows === 1 ? "" : "s"
            }.`
          : "No claim rows were found, so an empty claim summary template was created."
      );
    } catch {
      setFileStatus("That file could not be read.");
    } finally {
      event.target.value = "";
    }
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
            Use a preset for the live walkthrough or switch to custom intake to upload or paste evidence.
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

        <label className="file-upload-field">
          Evidence File
          <input
            accept=".csv,.tsv,.txt,.json,text/csv,text/tab-separated-values,text/plain,application/json"
            disabled={!isCustom}
            multiple
            onChange={(event) => {
              void handleEvidenceFileUpload(event);
            }}
            type="file"
          />
        </label>
        {fileStatus ? (
          <p className="file-status" aria-live="polite">
            {fileStatus}
          </p>
        ) : null}
        {isCustom && customRequest.documents.length > 1 ? (
          <ul className="uploaded-document-list" aria-label="Uploaded documents">
            {customRequest.documents.map((document) => (
              <li key={`${document.filename}-${document.content.length}`}>
                <strong>{document.filename}</strong>
                <span>{document.doc_type}</span>
              </li>
            ))}
          </ul>
        ) : null}

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
