# Claim-to-code map

| Claim | State transition / method | Canonical view | Required proof |
|---|---|---|---|
| Distinct configured authorities attest exact records | `configure`, `activate`, `attest_proposal`, `attest_batch` | `get_profile`, `get_case` | wrong-signer, duplicate, digest mismatch, and locked-config tests |
| Validators compare proposal meaning with modeled effects | `request_review`, `retry_review` using custom comparative nondeterminism | stored normalized result in `get_case` | prompt mocks, AST validator checks, integration consensus preflight |
| Coverage is complete and symmetric | deterministic result validator before any status mutation | IDs/edges/discrepancies in `get_case` | missing/extra/duplicate/root-semantic adversarial cases |
| Only conformant output grants a right | review derives `AUTHORIZED`; all other results grant none | `can_consume`, `get_case` | verdict matrix and malicious output tests |
| Authorization is exact and one-time | `consume_authorization` checks authority, status, deadline, revision, digest, nonce | `get_case` | wrong caller/digest/revision, duplicate and boundary tests |
| Uncertainty is non-penalizing and retryable | invalid/unavailable result becomes `UNVERIFIABLE`; `retry_review` | attempt and status fields | malformed/LLM error/retry tests; no hard-state mutation proof |
| Rejected batch can be corrected | `attest_batch` with strictly increasing revision from `NONCONFORMANT` | revision and digest | stale/duplicate/corrected-revision tests |
| No value is moved | no payable decorators or transfer boundary | source/schema | AST/schema assertions and value matrix |

No README or Portal statement may exceed these rows or omit the exclusions in `SPEC.md`.
