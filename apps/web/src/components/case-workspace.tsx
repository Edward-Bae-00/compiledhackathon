"use client";

export type WorkspaceCaseData = {
  title: string;
  status: string;
  overallRiskScore: number;
  documents: Array<{
    id: string;
    filename: string;
    docType: string;
  }>;
  sourceFiles?: string[];
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
    generatedAt?: string;
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

function slugify(value: string): string {
  const slug = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "investigator-memo";
}

export function buildMemoMarkdown(caseData: WorkspaceCaseData): string {
  const metadata = [
    `Case: ${caseData.title}`,
    `Status: ${caseData.status}`,
    `Risk Score: ${caseData.overallRiskScore}`,
    `Memo Source: ${caseData.memo.source ?? "Local Rule"}`
  ];

  if (caseData.memo.generatedAt) {
    metadata.push(`Generated At: ${caseData.memo.generatedAt}`);
  }

  return [`# ${caseData.memo.title}`, "", ...metadata, "", caseData.memo.body.trim(), ""].join("\n");
}

export function memoDownloadFilename(caseData: WorkspaceCaseData): string {
  return `${slugify(caseData.title)}-memo.md`;
}

function downloadMemo(caseData: WorkspaceCaseData) {
  const blob = new Blob([buildMemoMarkdown(caseData)], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = memoDownloadFilename(caseData);
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function CaseWorkspace({ caseData }: CaseWorkspaceProps) {
  const nodeLabels = new Map(caseData.evidenceGraph?.nodes.map((node) => [node.id, node.label]) ?? []);

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
        <h4 className="case-list-heading">Documents</h4>
        <ul className="document-list">
          {caseData.documents.map((document) => (
            <li key={document.id}>
              <strong>{document.filename}</strong>
              <div className="muted">{document.docType}</div>
            </li>
          ))}
        </ul>
        {caseData.sourceFiles?.length ? (
          <>
            <h4 className="case-list-heading">Source files</h4>
            <ul className="document-list">
              {caseData.sourceFiles.map((filename) => (
                <li key={filename}>
                  <strong>{filename}</strong>
                  <div className="muted">original upload</div>
                </li>
              ))}
            </ul>
          </>
        ) : null}
      </section>

      <section aria-label="Evidence Graph">
        <h2>Evidence Graph</h2>
        <p className="muted">
          Connect providers, procedure codes, and supporting documents into a timeline an investigator can scan quickly.
        </p>
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
                    <span>{edge.relationship}</span>
                    <strong>{nodeLabels.get(edge.target) ?? edge.target}</strong>
                    <span className="chip chip-source">{sourceBadge(edge.sourceType)}</span>
                  </div>
                  <div className="muted">{edge.evidence}</div>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
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
        <div className="memo-header">
          <h3>{caseData.memo.title}</h3>
          <button className="memo-export-button" onClick={() => downloadMemo(caseData)} type="button">
            Export Memo
          </button>
        </div>
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
  );
}
