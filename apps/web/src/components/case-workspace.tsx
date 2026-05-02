"use client";

import { type ReactNode } from "react";

import { EvidenceGraphVisual } from "./evidence-graph-visual";

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

function downloadBlob(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function downloadMemo(caseData: WorkspaceCaseData) {
  downloadBlob(memoDownloadFilename(caseData), buildMemoMarkdown(caseData), "text/markdown;charset=utf-8");
}

function riskBand(score: number): "low" | "medium" | "high" | "severe" {
  if (score >= 80) return "severe";
  if (score >= 55) return "high";
  if (score >= 25) return "medium";
  return "low";
}

function formatBandLabel(band: string): string {
  return band.charAt(0).toUpperCase() + band.slice(1);
}

function StatusChip({ status }: { status: string }) {
  return (
    <span className="chip chip-status" data-status={status}>
      {status}
    </span>
  );
}

function RiskScoreVisual({ score }: { score: number }) {
  const clampedScore = Math.max(0, Math.min(score, 100));
  const band = riskBand(clampedScore);
  const angle = clampedScore * 3.6;

  return (
    <div className="risk-score-summary" data-risk-band={band}>
      <div
        aria-label={`Risk score ${clampedScore} out of 100`}
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={clampedScore}
        className="risk-meter"
        data-risk-band={band}
        role="meter"
        style={{ background: `conic-gradient(var(--risk-${band}) ${angle}deg, rgba(23, 32, 51, 0.12) 0deg)` }}
      >
        <span>{clampedScore}</span>
      </div>
      <div>
        <span className="risk-label">Risk Score</span>
        <strong>{formatBandLabel(band)}</strong>
      </div>
    </div>
  );
}

function renderInlineMarkdown(text: string, keyPrefix: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map((part, index) => {
    const bold = part.match(/^\*\*([^*]+)\*\*$/);
    if (bold) {
      return <strong key={`${keyPrefix}-bold-${index}`}>{bold[1]}</strong>;
    }
    return part;
  });
}

function MemoMarkdown({ body }: { body: string }) {
  const blocks: ReactNode[] = [];
  let bulletItems: string[] = [];

  const flushBullets = () => {
    if (bulletItems.length === 0) return;
    const items = bulletItems;
    bulletItems = [];
    blocks.push(
      <ul className="memo-markdown-list" key={`bullets-${blocks.length}`}>
        {items.map((item, index) => (
          <li aria-label={item} key={`${item}-${index}`}>
            {renderInlineMarkdown(item, `bullet-${blocks.length}-${index}`)}
          </li>
        ))}
      </ul>
    );
  };

  body.split(/\r?\n/).forEach((rawLine, lineIndex) => {
    const line = rawLine.trim();
    if (!line) {
      flushBullets();
      return;
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      flushBullets();
      const level = Math.min(6, heading[1].length + 3);
      const content = renderInlineMarkdown(heading[2], `heading-${lineIndex}`);
      if (level === 4) {
        blocks.push(<h4 key={`heading-${lineIndex}`}>{content}</h4>);
      } else if (level === 5) {
        blocks.push(<h5 key={`heading-${lineIndex}`}>{content}</h5>);
      } else {
        blocks.push(<h6 key={`heading-${lineIndex}`}>{content}</h6>);
      }
      return;
    }

    const bullet = line.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      bulletItems.push(bullet[1]);
      return;
    }

    flushBullets();
    blocks.push(<p key={`paragraph-${lineIndex}`}>{renderInlineMarkdown(line, `paragraph-${lineIndex}`)}</p>);
  });
  flushBullets();

  return <div className="memo-body memo-markdown">{blocks}</div>;
}

function downloadCasePackage(caseData: WorkspaceCaseData) {
  downloadBlob(
    `${caseData.title.replace(/[^a-zA-Z0-9_-]/g, "_")}_case_package.json`,
    JSON.stringify(caseData, null, 2),
    "application/json"
  );
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
          <RiskScoreVisual score={caseData.overallRiskScore} />
          <StatusChip status={caseData.status} />
          <button
            className="mode-button"
            onClick={() => downloadCasePackage(caseData)}
            type="button"
          >
            Download Case Package
          </button>
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
          <>
            <EvidenceGraphVisual
              nodes={caseData.evidenceGraph.nodes}
              edges={caseData.evidenceGraph.edges}
            />
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
          </>
        ) : null}
        <ul aria-label="Case timeline" className="timeline-list visual-timeline">
          {caseData.timeline.map((event) => (
            <li className="timeline-item" key={event.id}>
              <span aria-hidden="true" className="timeline-dot" />
              <div>
                <strong>{event.label}</strong>
                <div className="muted">
                  {event.date ? `${event.date} • ` : ""}
                  {event.source}
                </div>
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
        <MemoMarkdown body={caseData.memo.body} />
        {caseData.palantirInsight ? (
          <div className="palantir-insight">
            <div className="palantir-heading">
              <strong>{caseData.palantirInsight.provider}</strong>
              <StatusChip status={caseData.palantirInsight.status} />
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
              <StatusChip status={caseData.palantir.mode} />
              <span className="chip chip-source">{caseData.palantir.provider}</span>
            </div>
            <ul className="diagnostic-list">
              {caseData.palantir.stages.map((stage) => (
                <li key={stage.stage}>
                  <div className="diagnostic-row">
                    <strong>{stage.stage}</strong>
                    <StatusChip status={stage.status} />
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
