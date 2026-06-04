# Deadman Tools

Repo-level tooling for producer workflows, publication checks, and runtime-pack
validation.

Current subdirectories:

- `ars/`: ARS, Studio, provider-adapter, producer-graph, and runtime-pack bridge
  tools.

Root tools:

- `check_publication_safety.py`: fail-fast public repo hygiene check. Run it
  before staging or publishing.

Provider tools must read credentials from environment variables only. Raw
provider request/response logs, cache files, checkpoints, local media, and
review scratch stay under ignored `tmp/` paths.

