import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { CaseWorkspace } from "../components/case-workspace";
import HomePage from "../../app/page";

const caseData = {
  title: "Demo Case",
  status: "ready",
  overallRiskScore: 95,
  documents: [
    { id: "doc-tip", filename: "tip-email.txt", docType: "tip" }
  ],
  findings: [
    {
      id: "flag-1",
      severity: "severe",
      summary: "Matched excluded entity in LEIE",
      whyFlagged: "Named party appears in the exclusion file",
      externalValidation: "LEIE exclusion match",
      evidenceQuotes: ["Provider name matches LEIE row"],
      source: "Local Rule"
    },
    {
      id: "flag-aip",
      severity: "high",
      summary: "AIP found a billing-network risk",
      whyFlagged: "Provider and billing contractor form a high-risk cluster.",
      externalValidation: "Palantir AIP risk assessment",
      evidenceQuotes: ["Apex Review Group managed billing."],
      source: "Palantir AIP"
    }
  ],
  evidenceGraph: {
    nodes: [
      { id: "provider-demo", label: "Dr. Excluded Provider", type: "provider", source: "Local Rule" },
      { id: "org-apex", label: "Apex Review Group", type: "organization", source: "Palantir AIP" },
      { id: "procedure-99214", label: "99214", type: "procedure", source: "CMS Benchmark" }
    ],
    edges: [
      {
        id: "edge-network",
        source: "provider-demo",
        target: "org-apex",
        relationship: "billing_management",
        evidence: "Apex Review Group managed billing.",
        sourceType: "Palantir AIP"
      },
      {
        id: "edge-claim",
        source: "provider-demo",
        target: "procedure-99214",
        relationship: "billed",
        evidence: "Provider billed 99214.",
        sourceType: "Local Rule"
      }
    ]
  },
  timeline: [
    {
      id: "evt-1",
      label: "Internal memo references excluded contractor",
      date: "2025-01-12",
      source: "internal-note.pdf"
    }
  ],
  memo: {
    title: "Draft Investigator Memo",
    body: "A severe exclusion match and abnormal billing volume require escalation.",
    source: "Palantir AIP"
  },
  palantirInsight: {
    provider: "Palantir AIP",
    status: "live",
    recommendation: "Prioritize investigator review and preserve the linked billing records."
  },
  palantir: {
    provider: "Palantir AIP",
    mode: "live",
    stages: [
      {
        stage: "extract_case_facts",
        configured: true,
        status: "live",
        latencyMs: 12,
        rawResponse: { entities: 2 }
      },
      {
        stage: "assess_risk",
        configured: true,
        status: "live",
        latencyMs: 18,
        rawResponse: { risk_factors: 1 }
      },
      {
        stage: "generate_memo",
        configured: true,
        status: "live",
        latencyMs: 21,
        rawResponse: { memo_markdown: "AIP memo" }
      }
    ]
  }
};

describe("CaseWorkspace", () => {
  it("renders the four-panel investigation workspace for an analyzed case", () => {
    render(<CaseWorkspace caseData={caseData} />);

    expect(screen.getByRole("heading", { name: /case intake/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /evidence graph/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /risk findings/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /memo generator/i })).toBeInTheDocument();
    expect(screen.getByText(/case summary/i)).toBeInTheDocument();
    expect(screen.getByText(/risk score/i)).toBeInTheDocument();
    expect(screen.getByText("95/100")).toBeInTheDocument();
    expect(screen.getByText(/1 document/i)).toBeInTheDocument();
    expect(screen.getByText(/2 findings/i)).toBeInTheDocument();
    expect(screen.getByText(/matched excluded entity in leie/i)).toBeInTheDocument();
    expect(screen.getByText(/internal memo references excluded contractor/i)).toBeInTheDocument();
    expect(screen.getByText(/prioritize investigator review/i)).toBeInTheDocument();
    expect(screen.getAllByText(/apex review group/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/billing_management/i)).toBeInTheDocument();
    expect(screen.getAllByText("AIP").length).toBeGreaterThan(0);
    expect(screen.getByText(/memo source: palantir aip/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /palantir diagnostics/i })).toBeInTheDocument();
    expect(screen.getByText(/extract_case_facts/i)).toBeInTheDocument();
    expect(screen.getByText(/12 ms/i)).toBeInTheDocument();
  });

  it("shows a clear empty state when a clean case has no findings", () => {
    render(<CaseWorkspace caseData={{ ...caseData, overallRiskScore: 0, findings: [] }} />);

    expect(screen.getByText("0/100")).toBeInTheDocument();
    expect(screen.getByText(/no risk findings detected/i)).toBeInTheDocument();
    expect(screen.getByText(/this packet is ready for routine documentation/i)).toBeInTheDocument();
  });
});

describe("HomePage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the product shell heading and starter workflow copy", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", { name: /fraud investigator copilot/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/live demo command center/i)).toBeInTheDocument();
    expect(screen.getByText(/turn messy evidence into a structured case file/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /analyze case/i })).toBeInTheDocument();
    expect(screen.getByText(/fastapi: not checked/i)).toBeInTheDocument();
    expect(screen.getByText(/palantir aip: not checked/i)).toBeInTheDocument();
    expect(screen.getByText(/case source: suspicious preset/i)).toBeInTheDocument();
    expect(screen.getByText(/choose demo packet/i)).toBeInTheDocument();
  });

  it("loads the seeded demo case into the workspace when analyze is clicked", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("API offline"));
    render(<HomePage />);

    fireEvent.click(screen.getByRole("button", { name: /analyze case/i }));

    expect(await screen.findByText(/matched excluded entity in leie/i)).toBeInTheDocument();
    expect(screen.getByText(/draft investigator memo/i)).toBeInTheDocument();
  });

  it("prefers the API-backed case payload when the backend is reachable", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: "case-api",
            title: "API Case",
            tip_text: "API tip",
            status: "draft",
            overall_risk_score: 0,
            created_at: "2026-04-24T23:00:00Z"
          })
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            documents: [
              {
                id: "doc-api",
                filename: "claims.csv",
                doc_type: "claim_summary",
                preview: "api preview"
              }
            ]
          })
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            case: {
              id: "case-api",
              title: "API Case",
              tip_text: "API tip",
              status: "analyzed",
              overall_risk_score: 77,
              created_at: "2026-04-24T23:00:00Z"
            },
            documents: [
              {
                id: "doc-api",
                filename: "claims.csv",
                doc_type: "claim_summary",
                preview: "api preview"
              }
            ],
            external_matches: [
              {
                id: "match-api",
                source_name: "NPPES",
                match_key: "1234567890",
                match_status: "verified",
                summary: "Verified provider via API"
              }
            ],
            risk_flags: [
              {
                id: "flag-api",
                case_id: "case-api",
                severity: "high",
                reason_code: "abnormal_billing_percentile",
                score_delta: 20,
                summary: "API finding",
                why_flagged: "Returned from backend analysis",
                external_validation: "Backend rule engine",
                evidence_quotes: ["API evidence"]
              }
            ],
            timeline: [
              {
                id: "evt-api",
                case_id: "case-api",
                label: "API timeline event",
                date: "2025-01-01",
                source: "claims.csv"
              }
            ],
            memo: {
              id: "memo-api",
              case_id: "case-api",
              title: "Draft Investigator Memo",
              body_markdown: "API memo body",
              generated_at: "2026-04-24T23:00:00Z"
            },
            palantir_insight: {
              provider: "Palantir AIP",
              status: "live",
              recommendation: "AIP recommends expedited review."
            }
          })
        )
      );

    render(<HomePage />);

    fireEvent.click(screen.getByRole("button", { name: /analyze case/i }));

    expect(await screen.findByText(/api finding/i)).toBeInTheDocument();
    expect(screen.getByText(/api memo body/i)).toBeInTheDocument();
    expect(screen.getByText(/palantir aip: live/i)).toBeInTheDocument();
    expect(screen.getByText(/aip recommends expedited review/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("sends the clean preset instead of the suspicious preset when selected", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: "case-clean",
            title: "Routine Compliance Review",
            tip_text: "Routine audit sample for Dr. Clean Provider.",
            status: "draft",
            overall_risk_score: 0,
            created_at: "2026-04-24T23:00:00Z"
          })
        )
      )
      .mockResolvedValueOnce(new Response(JSON.stringify({ documents: [] })))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            case: {
              id: "case-clean",
              title: "Routine Compliance Review",
              tip_text: "Routine audit sample for Dr. Clean Provider.",
              status: "analyzed",
              overall_risk_score: 0,
              created_at: "2026-04-24T23:00:00Z"
            },
            documents: [],
            external_matches: [],
            risk_flags: [],
            timeline: [],
            memo: {
              id: "memo-clean",
              case_id: "case-clean",
              title: "Draft Investigator Memo",
              body_markdown: "No high-confidence rule matches were detected.",
              generated_at: "2026-04-24T23:00:00Z"
            },
            palantir_insight: {
              provider: "Palantir AIP",
              status: "not_configured",
              recommendation: "Local deterministic findings remain available."
            }
          })
        )
      );

    render(<HomePage />);

    fireEvent.click(screen.getByRole("button", { name: /clean preset/i }));
    fireEvent.click(screen.getByRole("button", { name: /analyze case/i }));

    expect(await screen.findByText(/routine compliance review/i)).toBeInTheDocument();
    const createBody = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
    expect(createBody.title).toBe("Routine Compliance Review");
    expect(screen.getByText(/case source: clean preset/i)).toBeInTheDocument();
  });

  it("submits custom pasted evidence to the API", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: "case-custom",
            title: "Custom Intake",
            tip_text: "Custom tip",
            status: "draft",
            overall_risk_score: 0,
            created_at: "2026-04-24T23:00:00Z"
          })
        )
      )
      .mockResolvedValueOnce(new Response(JSON.stringify({ documents: [] })))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            case: {
              id: "case-custom",
              title: "Custom Intake",
              tip_text: "Custom tip",
              status: "analyzed",
              overall_risk_score: 42,
              created_at: "2026-04-24T23:00:00Z"
            },
            documents: [
              {
                id: "doc-custom",
                filename: "custom-claims.csv",
                doc_type: "claim_summary",
                preview: "custom preview"
              }
            ],
            external_matches: [],
            risk_flags: [
              {
                id: "flag-custom",
                case_id: "case-custom",
                severity: "medium",
                reason_code: "custom_rule",
                score_delta: 15,
                summary: "Custom evidence finding",
                why_flagged: "Custom evidence reached the backend.",
                external_validation: "Backend rule engine",
                evidence_quotes: ["custom evidence"]
              }
            ],
            timeline: [],
            memo: {
              id: "memo-custom",
              case_id: "case-custom",
              title: "Draft Investigator Memo",
              body_markdown: "Custom memo body",
              generated_at: "2026-04-24T23:00:00Z"
            },
            palantir_insight: {
              provider: "Palantir AIP",
              status: "not_configured",
              recommendation: "Local deterministic findings remain available."
            }
          })
        )
      );

    render(<HomePage />);

    fireEvent.click(screen.getByRole("button", { name: /custom intake/i }));
    fireEvent.change(screen.getByLabelText(/case title/i), { target: { value: "Custom Intake" } });
    fireEvent.change(screen.getByLabelText(/tip text/i), { target: { value: "Custom tip" } });
    fireEvent.change(screen.getByLabelText(/document filename/i), { target: { value: "custom-claims.csv" } });
    fireEvent.change(screen.getByLabelText(/document type/i), { target: { value: "claim_summary" } });
    fireEvent.change(screen.getByLabelText(/document content/i), {
      target: {
        value:
          "npi,procedure_code,service_date,amount,patient_count,provider_name\n1234567890,99214,2025-01-01,3000,50,Dr. Custom\n"
      }
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze case/i }));

    expect(await screen.findByText(/custom evidence finding/i)).toBeInTheDocument();
    const documentBody = JSON.parse(String(fetchMock.mock.calls[1][1]?.body));
    expect(documentBody.documents[0].filename).toBe("custom-claims.csv");
    expect(documentBody.documents[0].content).toContain("Dr. Custom");
  });

  it("sends local-only comparison mode to the analyze endpoint", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: "case-local",
            title: "Local Only",
            tip_text: "Tip",
            status: "draft",
            overall_risk_score: 0,
            created_at: "2026-04-24T23:00:00Z"
          })
        )
      )
      .mockResolvedValueOnce(new Response(JSON.stringify({ documents: [] })))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            case: {
              id: "case-local",
              title: "Local Only",
              tip_text: "Tip",
              status: "analyzed",
              overall_risk_score: 0,
              created_at: "2026-04-24T23:00:00Z"
            },
            documents: [],
            external_matches: [],
            risk_flags: [],
            evidence_graph: { nodes: [], edges: [] },
            timeline: [],
            memo: {
              id: "memo-local",
              case_id: "case-local",
              title: "Draft Investigator Memo",
              body_markdown: "Local memo",
              generated_at: "2026-04-24T23:00:00Z",
              source: "Local Rule"
            },
            palantir_insight: {
              provider: "Palantir AIP",
              status: "forced_local",
              recommendation: "Local deterministic findings are shown."
            },
            palantir: {
              provider: "Palantir AIP",
              mode: "forced_local",
              stages: [
                { stage: "extract_case_facts", configured: true, status: "forced_local", latency_ms: 0 },
                { stage: "assess_risk", configured: true, status: "forced_local", latency_ms: 0 },
                { stage: "generate_memo", configured: true, status: "forced_local", latency_ms: 0 }
              ]
            }
          })
        )
      );

    render(<HomePage />);

    fireEvent.click(screen.getByLabelText(/local-only/i));
    fireEvent.click(screen.getByRole("button", { name: /analyze case/i }));

    expect(await screen.findByText(/local memo/i)).toBeInTheDocument();
    expect(String(fetchMock.mock.calls[2][0])).toContain("?force_local=true");
    expect(screen.getByText(/palantir aip: forced_local/i)).toBeInTheDocument();
  });
});
