# Demo Evidence Files

Synthetic and anonymized evidence files for the Fraud Investigator Copilot live demo. These files are designed for two jobs:

- Upload-ready inputs for the Custom Intake file picker.
- Human-readable exhibits you can open during the pitch to show the source story behind the analysis.

## Fast Demo Path

1. Start the API with Palantir AIP environment variables loaded.
2. Start the web app and open `http://localhost:3000`.
3. Turn `Local-only` off.
4. Select `Custom Intake`.
5. Upload `upload-suspicious-network-claims.csv`.
6. Click `Analyze Case`.

Expected result: high risk, LEIE matches for `Dr. Excluded Provider`, CMS billing-volume findings, an evidence graph, an investigator memo, and Palantir diagnostics. If Palantir shows `partial`, use the diagnostics panel to show which AIP stages returned live enrichment and which fell back to local rules.

## Strongest Custom Intake Demo

For a richer relationship graph, paste the contents of `paste-suspicious-network-bundle.txt` into the Custom Intake evidence content field instead of uploading it. Set the document type to `memo` and click `Analyze Case`.

Expected result: the local parser extracts claim rows and also sees the phrase `Apex Review Group managed billing`, which creates a relationship edge from the provider to the billing organization.

## Upload-Ready Files

- `upload-suspicious-network-claims.csv`: high-risk excluded-provider billing case.
- `upload-specialty-mismatch-claims.csv`: family medicine provider billing genetic testing.
- `upload-clean-control-claims.csv`: low-risk control case for contrast.

## Human-Readable Exhibits

- `exhibit-index.md`: pitch order, talking points, and expected findings.
- `whistleblower-tip.txt`: narrative tip with parseable claim language.
- `internal-billing-note.txt`: billing-operations note linking the provider and excluded billing organization.
- `billing-company-email.txt`: email-style exhibit showing billing-company pressure and referral language.
- `paste-suspicious-network-bundle.txt`: paste-ready all-in-one narrative for Custom Intake.

## Suggested Pitch Sequence

1. Open `exhibit-index.md` and explain that all identities are synthetic/anonymized.
2. Upload `upload-suspicious-network-claims.csv` and run analysis with Palantir enabled.
3. Point to risk score, LEIE/CMS findings, graph, memo, and Palantir diagnostics.
4. Paste `paste-suspicious-network-bundle.txt` into Custom Intake, set the document type to `memo`, and run again to show narrative extraction and relationship evidence.
5. Toggle `Local-only` on and run the same intake to show deterministic local fallback.
6. Upload `upload-clean-control-claims.csv` to show low-risk restraint.
7. Upload `upload-specialty-mismatch-claims.csv` to show a different fraud theory.
