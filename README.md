# Governance Intent Gate

Governance Intent Gate is a reusable GenLayer Intelligent Contract that compares exact, authority-attested proposal directives with exact, independently attested modeled execution effects. A validator-approved `CONFORMANT` result creates one internal authorization bound to the case, batch revision, digest, nonce, and deadline; the configured governance authority can consume it once.

The contribution is contract-only. There is no frontend, hosted app, custody, or simulated wallet flow.

## Why it exists

DAO votes and execution batches are often reviewed in different tools and represented in different formats. A hash proves byte stability, but it does not answer whether every approved directive is implemented or whether the batch adds an unauthorized effect. This contract gives governors, timelocks, Safe modules, and registries a bounded semantic admission primitive with explicit authority separation and fail-closed settlement rules.

## Contract model

- The owner locks three distinct authorities, an origin/profile, decoder version, and selector allowlist, then activates the profile once.
- A proposal authority attests the exact directive bytes and SHA-256 digest.
- A distinct decoder authority attests the exact modeled-effect bytes, digest, and revision.
- GenLayer validators independently compare semantic coverage through `gl.vm.run_nondet`.
- Deterministic code rejects missing, extra, duplicate, malformed, or internally inconsistent result entities before any authorization is created.
- Invalid or unavailable review output becomes non-consequential `UNVERIFIABLE` and may be retried over unchanged commitments.
- Only the governance authority can consume an exact authorization, once, before the deadline.

Canonical integration views are `get_profile`, `get_case`, `get_case_count`, `get_case_id`, and `can_consume`.

## Verified deployment

- Network: GenLayer Studio Dev, chain ID `61997`
- Contract: [`0x3f6AE21DF18DF4104DD3b0a5596612B9C17240D2`](https://explorer-studio-dev.genlayer.com/address/0x3f6AE21DF18DF4104DD3b0a5596612B9C17240D2)
- Deployment transaction: [`0x10709d…c154`](https://explorer-studio-dev.genlayer.com/tx/0x10709da2c3ff42199c63e004e5ee424307ad82bd1299320cea8d5343dd07c154)
- Semantic review transaction: [`0xa2feb1…0b29`](https://explorer-studio-dev.genlayer.com/tx/0xa2feb1ec10cf521d33d4a350b29a290e2090cd6bcbe8d8c738009563a0db0b29)
- Final consequence transaction: [`0x8b30a0…bfa9`](https://explorer-studio-dev.genlayer.com/tx/0x8b30a034d56acdfd726a890e350e05e9bfd0ec2e1a42fcb1422c21a21aeebfa9)

The deployment and all seven lifecycle writes reached `FINALIZED` with `FINISHED_WITH_RETURN`. The semantic result was `CONFORMANT`; the canonical case moved from `AUTHORIZED` to `CONSUMED`, and `can_consume` became false. Exact sanitized evidence is in [`docs/evidence/studio-dev`](docs/evidence/studio-dev).

## Verification

The repository contains one contract and 28 automated tests: 22 direct contract tests, five local SDK/parser/source-policy tests, and one read-only Studio Dev integration test.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
npm run check
npm run preflight
npm run test:integration
```

`npm run check` runs GenVM lint and semantic validation, strict type checking, schema assertions, direct tests, adversarial settlement tests, native SDK ABI round trips, and sanitized receipt parser tests. `npm run preflight` verifies the Studio Dev chain, exact source schema, fee policy, and all nine write ABI round trips without writing to the network.

The deployment and lifecycle scripts are resumable: `npm run deploy:resume` and `npm run demo:resume` recover checkpointed transaction IDs instead of replaying finalized writes. They discover secrets from ignored `.env` files and never persist private keys.

## Reuse examples

- A Safe module can read `can_consume` before forwarding a digest-bound batch.
- A timelock adapter can require a consumed authorization for the queued revision.
- A registry can enumerate cases and expose finalized conformance without trusting a reviewer dashboard.

An integrating consumer must authenticate this contract, bind its own proposal and batch identities, and enforce the returned authorization at its actual execution boundary.

## Honest limits

This contract does not prove a live DAO vote, decode arbitrary calldata or bytecode, prove hidden runtime behavior, execute the modeled calls, move value, or block an external executor by itself. The Studio Dev lifecycle uses synthetic fixtures and is not adoption evidence. Semantic judgment is bounded by the exact authority-attested text and modeled effects. See [`docs/SPEC.md`](docs/SPEC.md) for the complete claim boundary.

## Forge identity

- Track: `INTELLIGENT_CONTRACTS`
- Forge run: `20260927t093405z-intelligent-contracts`
- Registry record: `afd015abb32e8ab185a8376c56f301a5173e18c22fbea88c2c345c9cb3829c52`
- Immutable handoff: `b4d38e8b623ac0d580edbee06728f74edc8ffbccb0648e093427df43362666c4`

Licensed under the MIT License.
