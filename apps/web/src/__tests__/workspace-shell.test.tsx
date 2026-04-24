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
      evidenceQuotes: ["Provider name matches LEIE row"]
    }
  ],
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
    body: "A severe exclusion match and abnormal billing volume require escalation."
  }
};

describe("CaseWorkspace", () => {
  it("renders the four-panel investigation workspace for an analyzed case", () => {
    render(<CaseWorkspace caseData={caseData} />);

    expect(screen.getByRole("heading", { name: /case intake/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /evidence graph/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /risk findings/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /memo generator/i })).toBeInTheDocument();
    expect(screen.getByText(/matched excluded entity in leie/i)).toBeInTheDocument();
    expect(screen.getByText(/internal memo references excluded contractor/i)).toBeInTheDocument();
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
    expect(screen.getByText(/drop in messy evidence, get back a structured case file/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /analyze case/i })).toBeInTheDocument();
  });

  it("loads the seeded demo case into the workspace when analyze is clicked", async () => {
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
            }
          })
        )
      );

    render(<HomePage />);

    fireEvent.click(screen.getByRole("button", { name: /analyze case/i }));

    expect(await screen.findByText(/api finding/i)).toBeInTheDocument();
    expect(screen.getByText(/api memo body/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});
