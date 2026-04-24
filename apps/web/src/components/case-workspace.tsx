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
    source?: string;
  }>;
  evidenceGraph?: {
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
      sourceType: string;
    }>;
  };
  timeline: Array<{
    id: string;
    label: string;
    date?: string | null;
    source: string;
  }>;
  memo: {
    title: string;
    body: string;
    source?: string;
  };
  externalMatches?: Array<{
    id: string;
    source: string;
    summary: string;
  }>;
  palantirInsight?: {
    provider: string;
    status: string;
    recommendation: string;
    errorSummary?: string | null;
  };
  palantir?: {
    provider: string;
    mode: string;
    stages: Array<{
      stage: string;
      configured: boolean;
      status: string;
      latencyMs: number;
      errorSummary?: string | null;
      rawResponse?: unknown;
    }>;
  };
};

type CaseWorkspaceProps = {
  caseData: WorkspaceCaseData;
};

function sourceBadge(source?: string): string {
  return source?.toLowerCase().includes("palantir") ? "AIP" : "Local";
}

function pluralize(count: number, singular: string): string {
  return `${count} ${singular}${count === 1 ? "" : "s"}`;
}

export function CaseWorkspace({ caseData }: CaseWorkspaceProps) {
  const nodeLabels = new Map(caseData.evidenceGraph?.nodes.map((node) => [node.id, node.label]) ?? []);
  const graphNodeCount = caseData.evidenceGraph?.nodes.length ?? 0;
  const graphEdgeCount = caseData.evidenceGraph?.edges.length ?? 0;
  const palantirMode = caseData.palantir?.mode ?? caseData.palantirInsight?.status ?? "not returned";

  return (
    <div className="workspace-shell">
      <section className="case-summary" aria-label="Case Summary">
        <div>
          <div className="section-kicker">Case Summary</div>
          <h2>{caseData.title}</h2>
          <p className="muted">
            A single demo-ready view of intake status, graph coverage, risk findings, and memo provenance.
          </p>
        </div>
        <div className="summary-metrics" aria-label="Case metrics">
          <div className="metric-card">
            <span>Risk score</span>
            <strong>{caseData.overallRiskScore}/100</strong>
          </div>
          <div className="metric-card">
            <span>Evidence packet</span>
            <strong>{pluralize(caseData.documents.length, "document")}</strong>
          </div>
          <div className="metric-card">
            <span>Findings</span>
            <strong>{pluralize(caseData.findings.length, "finding")}</strong>
          </div>
          <div className="metric-card">
            <span>Palantir mode</span>
            <strong>{palantirMode}</strong>
          </div>
        </div>
      </section>

      <div className="workspace-grid">
      <section aria-label="Case Intake">
        <div className="section-heading">
          <div>
            <div className="section-kicker">Step 1</div>
            <h2>Case Intake</h2>
          </div>
          <p className="muted">
            Preserve the starter record and source documents the analysis used.
          </p>
        </div>
        <div className="case-meta">
          <span className="chip chip-score">Score {caseData.overallRiskScore}/100</span>
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
        <div className="section-heading">
          <div>
            <div className="section-kicker">{graphNodeCount} nodes / {graphEdgeCount} links</div>
            <h2>Evidence Graph</h2>
          </div>
          <p className="muted">
            Connect providers, procedure codes, and supporting documents into a scan-friendly timeline.
          </p>
        </div>
        {caseData.evidenceGraph?.nodes.length ? (
          <div className="network-graph" aria-label="Entity relationship graph">
            <div className="graph-node-list">
              {caseData.evidenceGraph.nodes.map((node) => (
                <div className="graph-node" data-node-type={node.type} key={node.id}>
                  <strong>{node.label}</strong>
                  <span className="muted">{node.type}</span>
                  <span className="chip chip-source">{sourceBadge(node.source)}</span>
                </div>
              ))}
            </div>
            <ul className="graph-edge-list">
              {caseData.evidenceGraph.edges.map((edge) => (
                <li key={edge.id}>
                  <div className="edge-row">
                    <strong>{nodeLabels.get(edge.source) ?? edge.source}</strong>
                    <span className="relationship-label">{edge.relationship}</span>
                    <strong>{nodeLabels.get(edge.target) ?? edge.target}</strong>
                    <span className="chip chip-source">{sourceBadge(edge.sourceType)}</span>
                  </div>
                  <div className="muted">{edge.evidence}</div>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <div className="list-label">Timeline</div>
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
        <div className="section-heading">
          <div>
            <div className="section-kicker">Risk review</div>
            <h2>Risk Findings</h2>
          </div>
          <p className="muted">
            Rule-backed signals stay ahead of memo drafting so every suspicion remains anchored to evidence.
          </p>
        </div>
        {caseData.findings.length ? (
          <ul className="finding-list">
            {caseData.findings.map((finding) => (
              <li key={finding.id}>
                <div className="finding-heading">
                  <span className="chip finding-severity" data-severity={finding.severity}>
                    {finding.severity}
                  </span>
                  <span className="chip chip-source">{sourceBadge(finding.source)}</span>
                </div>
                <strong>{finding.summary}</strong>
                <p>{finding.whyFlagged}</p>
                <div className="muted">Validation: {finding.externalValidation}</div>
                <div className="muted">Evidence: {finding.evidenceQuotes.join(" | ")}</div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state">
            <strong>No risk findings detected</strong>
            <p className="muted">This packet is ready for routine documentation and standard reviewer signoff.</p>
          </div>
        )}
        {caseData.externalMatches?.length ? (
          <>
          <div className="list-label">External validation</div>
          <ul className="validation-list">
            {caseData.externalMatches.map((match) => (
              <li key={match.id}>
                <strong>{match.source}</strong>
                <div className="muted">{match.summary}</div>
              </li>
            ))}
          </ul>
          </>
        ) : null}
      </section>

      <section aria-label="Memo Generator">
        <div className="section-heading">
          <div>
            <div className="section-kicker">Referral draft</div>
            <h2>Memo Generator</h2>
          </div>
          <p className="muted">
            Turn the findings into a referral-ready narrative with provenance an investigator can follow.
          </p>
        </div>
        <h3>{caseData.memo.title}</h3>
        <div className="muted memo-source">Memo source: {caseData.memo.source ?? "Local Rule"}</div>
        <div className="memo-body">{caseData.memo.body}</div>
        {caseData.palantirInsight ? (
          <div className="palantir-insight">
            <div className="palantir-heading">
              <strong>{caseData.palantirInsight.provider}</strong>
              <span className="chip chip-status">{caseData.palantirInsight.status}</span>
            </div>
            <p>{caseData.palantirInsight.recommendation}</p>
            {caseData.palantirInsight.errorSummary ? (
              <div className="muted">Error: {caseData.palantirInsight.errorSummary}</div>
            ) : null}
          </div>
        ) : null}
        {caseData.palantir ? (
          <div className="palantir-diagnostics">
            <h3>Palantir Diagnostics</h3>
            <div className="case-meta">
              <span className="chip chip-status">{caseData.palantir.mode}</span>
              <span className="chip chip-source">{caseData.palantir.provider}</span>
            </div>
            <ul className="diagnostic-list">
              {caseData.palantir.stages.map((stage) => (
                <li key={stage.stage}>
                  <div className="diagnostic-row">
                    <strong>{stage.stage}</strong>
                    <span className="chip chip-status">{stage.status}</span>
                    <span className="muted">{stage.latencyMs} ms</span>
                  </div>
                  {stage.errorSummary ? <div className="muted">Error: {stage.errorSummary}</div> : null}
                  {stage.rawResponse ? (
                    <details>
                      <summary>Raw response</summary>
                      <pre>{JSON.stringify(stage.rawResponse, null, 2)}</pre>
                    </details>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>
      </div>
    </div>
  );
}
