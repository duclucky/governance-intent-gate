# Locked specification

Status: `SPEC_LOCKED`

## Identity and public claim boundary

This repository implements the immutable Forge handoff for `governance-intent-gate`, registry record `afd015abb32e8ab185a8376c56f301a5173e18c22fbea88c2c345c9cb3829c52` and handoff `b4d38e8b623ac0d580edbee06728f74edc8ffbccb0648e093427df43362666c4`.

Supported claim: exact proposal directives attested by a configured proposal authority are semantically compared with exact modeled effects attested by a distinct decoder authority. After deterministic coverage validation, a conformant result grants the configured governance authority one internal authorization for the exact case revision and batch digest.

Excluded claims: live DAO vote authenticity, arbitrary calldata or bytecode analysis, absence of hidden runtime behavior, external execution blocking without an adapter, value custody or transfer, frontend operation, adoption, and economic impact.

## Roles and locked profile

- Owner: deployment sender; may configure once and activate once.
- Proposal authority: attests the exact passed-proposal directive record through `gl.message.sender_address`.
- Decoder authority: distinct signer that attests exact allowlisted modeled batch effects.
- Governance authority: only caller allowed to consume an authorization.
- Review requester: any caller; cannot change evidence or consequence rules.
- Context submitter: creator-supplied context is stored as non-authoritative data and is never sufficient for a verdict or consequence.

Configuration locks profile ID, governance origin, three role addresses, decoder version, allowlisted selectors, limits, and source/runner identity. Activation is irreversible.

## Canonical input formats

`directives_json` is canonical compact JSON: an array of objects with exactly `id` and `text`. IDs are non-empty, unique ASCII identifiers. Text is non-empty and bounded.

`effects_json` is canonical compact JSON: an array of objects with exactly `id`, `target`, `value`, `selector`, `operation`, and `summary`. IDs are unique; selectors must be in the locked allowlist; target/value/operation/summary are non-empty bounded strings. Effect bodies model declared effects only; they do not prove arbitrary bytecode behavior.

The contract recomputes SHA-256 from the exact UTF-8 bytes supplied to each attestation and rejects a claimed digest mismatch before review. The batch digest is therefore the digest of the exact stored modeled-effect bytes. Case/proposal IDs, versions, authorities, decoder version, deadline, and contract address supply anti-replay scope.

## State machine

`CONFIGURING -> ACTIVE`

Per case:

`OPEN -> READY -> REVIEWING(transaction-local) -> AUTHORIZED | NONCONFORMANT | UNVERIFIABLE`

- `UNVERIFIABLE -> AUTHORIZED | NONCONFORMANT | UNVERIFIABLE` by retry over unchanged exact evidence.
- `NONCONFORMANT -> READY` only by a strictly increasing decoder-attested batch revision.
- `AUTHORIZED -> CONSUMED` once, only by governance authority with exact revision and digest.
- Any unconsumed nonterminal state becomes `EXPIRED` at or after its deadline.
- `CONSUMED` and `EXPIRED` are terminal.

Every time-sensitive write checks transaction time itself. Legal calls require `now < deadline`; expiry requires `now >= deadline`.

## Semantic review and deterministic settlement

The leader and each validator independently analyze the same exact stored directives and effects. They return:

- `verdict`: `CONFORMANT`, `NONCONFORMANT`, or `UNVERIFIABLE`;
- complete directive ID set;
- complete effect ID set;
- coverage edges `{directive_id,effect_id}`;
- discrepancy codes from the locked enum.

The custom validator reruns the analysis through the current v0.3 `gl.vm.run_nondet` API (the replacement for v0.2 `run_nondet_unsafe`) and compares the normalized verdict, all ID sets, all edges, and all discrepancy codes. After consensus, deterministic code rejects malformed meaning: duplicate/extra/missing IDs, unknown edge endpoints, duplicate edges, invalid enums, incomplete symmetric coverage for `CONFORMANT`, or discrepancies inconsistent with the verdict. An invalid result maps to `UNVERIFIABLE`, changes no authorization right, and remains retryable.

`CONFORMANT` requires every directive to cover at least one effect, every effect to be authorized by at least one directive, and zero discrepancy codes. `NONCONFORMANT` requires at least one valid discrepancy. The contract derives authorization solely from these validated fields; it never trusts an LLM-supplied consequence instruction.

## Canonical views

- Profile and activation state.
- Case JSON including evidence digests, authority bindings, revision, status, review attempt, normalized semantic result, authorization nonce, consumed flag, and deadline.
- Case count and ID-by-index for enumeration.
- `can_consume(case_id, revision, digest, nonce)` as a canonical preflight; actual write repeats all checks.

## Limits

One contract, no frontend, no payable method, no external messages, no cross-contract enforcement, no unbounded scan. Inputs and entity counts are bounded before parsing/review. Storage uses keyed case state and an append-only case ID index.
