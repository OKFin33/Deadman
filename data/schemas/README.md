# Deadman Schemas

Tracked JSON schemas for Deadman runtime contracts, producer graph artifacts,
visual-result planning, and field-minimum evidence.

Public schemas are allowed here when they describe stable or reviewable
contracts. Raw generated provider outputs and run-specific intermediate
artifacts stay under ignored `tmp/` paths.

Current groups:

- `deadman_judgment_adapter_*.v0.1.json`: backend adapter request/response
  contracts;
- `moment_*` and `field_*`: moment causality and field-minimum contracts;
- `producer_graph/`: producer graph batch and review artifact schemas;
- `visual_result_*.v0.1.json`: future visual result planning contracts.

