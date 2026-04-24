export type WorkspaceCaseData = {
  title: string;
  status: string;
  overallRiskScore: number;
  documents: Array<{
    id: string;
    filename: string;
    docType: string;
  }>;
  findings: Array<{
    id: string;
    severity: string;
    summary: string;
    whyFlagged: string;
    externalValidation: string;
    evidenceQuotes: string[];
  }>;
  timeline: Array<{
    id: string;
    label: string;
    date?: string | null;
    source: string;
  }>;
  memo: {
    title: string;
    body: string;
  };
  externalMatches?: Array<{
    id: string;
    source: string;
    summary: string;
  }>;
};

type CaseWorkspaceProps = {
  caseData: WorkspaceCaseData;
};

export function CaseWorkspace({ caseData }: CaseWorkspaceProps) {
  return (
    <div className="workspace-grid">
      <section aria-label="Case Intake">
        <h2>Case Intake</h2>
        <p className="muted">
          Upload documents, paste the whistleblower tip, and preserve the structured starter record for the case.
        </p>
        <h3>{caseData.title}</h3>
        <div className="case-meta">
          <span className="chip chip-score">Risk Score {caseData.overallRiskScore}</span>
          <span className="chip chip-status">{caseData.status}</span>
        </div>
        <ul className="document-list">
          {caseData.documents.map((document) => (
            <li key={document.id}>
              <strong>{document.filename}</strong>
              <div className="muted">{document.docType}</div>
            </li>
          ))}
        </ul>
      </section>

      <section aria-label="Evidence Graph">
        <h2>Evidence Graph</h2>
        <p className="muted">
          Connect providers, procedure codes, and supporting documents into a timeline an investigator can scan quickly.
        </p>
        <ul className="timeline-list">
          {caseData.timeline.map((event) => (
            <li key={event.id}>
              <strong>{event.label}</strong>
              <div className="muted">
                {event.date ? `${event.date} • ` : ""}
                {event.source}
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section aria-label="Risk Findings">
        <h2>Risk Findings</h2>
        <p className="muted">
          Rule-backed signals stay ahead of memo drafting so every suspicion stays anchored to evidence.
        </p>
        <ul className="finding-list">
          {caseData.findings.map((finding) => (
            <li key={finding.id}>
              <span className="chip finding-severity" data-severity={finding.severity}>
                {finding.severity}
              </span>
              <strong>{finding.summary}</strong>
              <p>{finding.whyFlagged}</p>
              <div className="muted">Validation: {finding.externalValidation}</div>
              <div className="muted">Evidence: {finding.evidenceQuotes.join(" | ")}</div>
            </li>
          ))}
        </ul>
        {caseData.externalMatches?.length ? (
          <ul className="validation-list">
            {caseData.externalMatches.map((match) => (
              <li key={match.id}>
                <strong>{match.source}</strong>
                <div className="muted">{match.summary}</div>
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      <section aria-label="Memo Generator">
        <h2>Memo Generator</h2>
        <p className="muted">
          Turn the rule-backed findings into a referral-ready narrative with citations an investigator can follow.
        </p>
        <h3>{caseData.memo.title}</h3>
        <div className="memo-body">{caseData.memo.body}</div>
      </section>
    </div>
  );
}
