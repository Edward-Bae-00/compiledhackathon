# Exhibit Index

All names, NPIs, organizations, dates, and narratives in this folder are synthetic/anonymized demo material. They are built to match the seeded reference data in this repository.

## Exhibit E-001: Suspicious Claims Summary

File: `upload-suspicious-network-claims.csv`

Use this first. It shows Dr. Excluded Provider billing unusually high volumes for office visits and chronic care management. The local rules should find:

- LEIE hit for Dr. Excluded Provider.
- NPPES verification for NPI `1234567890`.
- CMS benchmark overage for `99214` and `99490`.
- High claim-volume flags.

Pitch line: "The local rules give us deterministic baseline findings, while Palantir AIP can enrich extraction, risk interpretation, and memo drafting."

## Exhibit E-002: Whistleblower Tip

File: `whistleblower-tip.txt`

Open this during the pitch before or after analysis to show the kind of messy narrative evidence an investigator might receive.

Pitch line: "The source material is not a clean database. It is a tip, an email, an internal note, and claim snippets."

## Exhibit E-003: Internal Billing Note

File: `internal-billing-note.txt`

This connects Dr. Excluded Provider to Apex Review Group and BrightPath Billing LLC. Both organizations are represented in the seeded exclusion data.

Pitch line: "The graph is useful because a suspicious case is usually a network, not a single row."

## Exhibit E-004: Billing Company Email

File: `billing-company-email.txt`

Use this as a human-readable exhibit to explain why relationship and intent-like language matters.

Pitch line: "AIP is helpful for turning this kind of text into structured entities, relationships, and investigator-ready memo language."

## Exhibit E-005: Paste-Ready Narrative Bundle

File: `paste-suspicious-network-bundle.txt`

Paste this into Custom Intake for the richest no-upload demo. Set the document type to `memo`. It includes exact parseable claim sentences and relationship language.

Expected local result:

- Provider, NPI, procedure, amount, and patient count extraction.
- LEIE matches for excluded names in the text.
- A local relationship edge from Dr. Excluded Provider to Apex Review Group.

## Exhibit E-006: Specialty Mismatch Claims

File: `upload-specialty-mismatch-claims.csv`

This is a second fraud theory. Dr. Clean Provider is family medicine, but the claim is for genetic testing code `81225`, which the seeded benchmark expects from laboratory/genetics taxonomies.

Expected local result:

- Specialty/procedure mismatch.
- CMS benchmark overage.
- High claim-volume flag.

## Exhibit E-007: Clean Control Claims

File: `upload-clean-control-claims.csv`

Use this last to show the system can avoid over-flagging ordinary claims.

Expected local result:

- NPPES verification.
- Low or zero risk.
- Local memo with restraint.
