# Deadman Compatibility Namespace

This package preserves historical `Deadman.*` imports after the standalone repo
extraction.

The real source directories now live at the repo root:

- `backend/`
- `tools/`
- `data/`
- `frontend/`

`Deadman/__init__.py` extends the package path to the repo root so older tests
and producer scripts can continue to import modules such as
`Deadman.backend.api` without duplicating files.

Do not add new implementation modules here unless the compatibility strategy is
changed. New code should normally live in the root-owned source directories.

