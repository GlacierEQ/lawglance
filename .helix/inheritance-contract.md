# Pro_Code Inheritance Contract

`Pro_Code` is the doctrine strand of the GlacierEQ Double Helix.

## Authority

Every GlacierEQ repo may inherit from this repo for:

- operator identity and mission context
- code style and naming conventions
- commit discipline
- agent loading order
- repo audit expectations
- ecosystem link references
- non-secret memory architecture policy

## Paired Strand

Runtime execution is delegated to the paired strand:

- `GlacierEQ/pro-code`

The paired runtime strand may import doctrine from this repo, but this repo does not own the live worker runtime.

## Aspen Grove Binding

All cross-repo memory, connector, evidence, and Grove topology pointers are routed through:

- `GlacierEQ/aspen-grove-core`

## Mastermind Binding

Mastermind may read this repo as doctrine source material and use `.mastermind/agent-loading-policy.md` for agent bootstrapping. Mastermind may propose patches, but must preserve this repo as the doctrine authority.

## Secret and Evidence Policy

- No raw secrets in GitHub.
- No raw privileged legal evidence in GitHub.
- Use `secret_ref`, `vault_ref`, `evidence_id`, `sha256`, or external storage pointers.

## Phase 1A Scope

This contract creates a hidden substrate only. It does not move code, delete files, rewrite history, or merge repos.
