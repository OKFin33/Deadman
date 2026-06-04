# Deadman Documentation Map

> Status: publicization prep map  
> Scope: tracked docs only. Local working artifacts stay under ignored paths.

This directory contains three different kinds of documents:

1. current product/runtime contracts that public readers can start from;
2. baseline and review documents that explain how v0.3 became the pre-v0.4
   baseline;
3. historical execution specs and producer evidence notes that preserve sprint
   context, but are not the current entry point.

Do not treat every document here as current product truth. Start from the
sections below.

## Current Entry Points

| Need | Start here |
| --- | --- |
| Current UX core | `Branch3_要是我来_PRD_v0.4_UX_Core.md` |
| Why v0.4 pivoted | `Branch3_UX_Core_Pivot_Log_v0.1.md` |
| v0.3 baseline completeness | `V0_3_Completeness_Review_v0.1.md` |
| Local vs public artifact boundary | `Local_Development_Artifact_Policy_v0.1.md` |
| Publicization decisions | `Publicization_Decision_Log_v0.1.md` |
| Publication readiness | `../PUBLICATION_REVIEW.md` |

## Product And UX

Current product direction:

- `Branch3_要是我来_PRD_v0.4_UX_Core.md`
- `Branch3_UX_Core_Pivot_Log_v0.1.md`
- `Branch3_Companion_Product_Detail_Spec_v0.1.md`
- `Resident_Companion_Runtime_Tech_Plan_v0.1.md`
- `P0_Mobile_UX_Acceptance_Checklist_v0.1.md`

Baseline and prior review context:

- `Branch3_要是我来_PRD_v0.3.md`
- `external_review_v0.3_pivoted_lens.md`
- `V0_3_Completeness_Review_v0.1.md`
- older `Branch3_要是我来_PRD_v0.2.md` and `external_review_v0.*.md`
  files are historical context.

## Runtime, Data, And CAB Contracts

Use-side runtime and API contracts:

- `Backend_Judgment_Adapter_Interface_v0.1.md`
- `Backend_Adapter_Mapping_v0.1.md`
- `CABRuntime_SDK_Integration_Contract_v0.1.md`
- `Branch3_Demo_Episode_Pack_Contract_v0.1.md`

Producer-side and Studio contracts:

- `Deadman_Studio_Implementation_Contract_v0.1.md`
- `Producer_Bridge_Minimum_Flow_v0.1.md`
- `Moment_Field_Minimum_Set_v0.3.md`
- `Moment_Causality_Pack_v0.3_Draft.md`
- `Field_Demand_Cluster_Report_v0.3.md`
- `Field_Minimum_Red_Team_v0.1.md`
- `Typed_Subkeys_Patch_Report_v0.1.md`

## Submission And Deployment

Competition/deployment prep docs:

- `Submission_Material_Map_v0.1.md`
- `Submission_Readiness_Runbook_v0.1.md`
- `Competition_Technical_Doc_Draft_v0.1.md`
- `Competition_Technical_Doc_Skeleton_v0.1.md`
- `Android_APK_Delivery_Plan_v0.1.md`

These documents may refer to local recording assets and ignored producer
artifacts. They are useful for submission operations, but must be reviewed
before public release claims are made.

Some older submission docs mention the original OSeria-Alter `Runtime/frontend`
compatibility bridge. In this standalone repo, those mentions are historical
source-workspace context, not a current dependency.

## Historical Execution Specs

`goal_spec/` now contains only selected current-facing producer graph specs.
Older sprint execution contracts live under `archive/goal_spec/`.

Archive files are useful for reconstructing how artifacts were produced, but
they are not current entry points and may mention old checkout paths or ignored
`tmp/` artifacts.

Do not use archive files as current product truth without checking the current
PRD and publication review.

## Local-Only Artifacts

The following paths are intentionally ignored and should not be committed:

- `tmp/`
- `.agent/`
- `local_artifacts/`
- `.env` and provider-specific secret files
- local media, provider traces, caches, build outputs, and generated packages

Run this before staging or publishing:

```bash
python3 tools/check_publication_safety.py
```
