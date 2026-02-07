# File Write Policy (Side-Effect Boundary)

## Default rule

- LLM proposes diffs only
- Deterministic validator approves/blocks
- Apply only in sandbox

## Allowed operations

- create/modify: allowed under policy
- delete: requires explicit approval (always)

## Path and file-type allowlists

- Allowed directories:
- Denylist patterns:
- Secret scanning policy:

## Release gate

- Required checks:
- Override procedure:
