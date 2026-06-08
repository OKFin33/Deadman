# Deadman Schemas

Tracked JSON schemas for Deadman runtime contracts, producer graph artifacts,
visual-result planning, and migration evidence.

Public schemas are allowed here when they describe stable or reviewable
contracts. Raw generated provider outputs and run-specific intermediate
artifacts stay under ignored `tmp/` paths.

Current v0.4 source contract:

```text
docs/CompanionExchangePack_v0.1_Contract.md
data/schemas/companion_exchange_pack.v0.1.json
```

Existing moment/field schemas remain compatibility and migration contracts.

Current groups:

- `deadman_judgment_adapter_*.v0.1.json`: backend adapter request/response
  contracts;
- `companion_exchange_pack.v0.1.json`: reviewed friend-style exchange artifact
  contract;
- `deadman_v04_authoring_proof.v0.1.json`: tracked v0.4 Studio authoring
  proof fixture contract;
- `moment_*` and `field_*`: legacy/migration moment causality and field-minimum
  contracts;
- `producer_graph/`: producer graph batch and review artifact schemas;
- `visual_result_*.v0.1.json`: future visual result planning contracts.
