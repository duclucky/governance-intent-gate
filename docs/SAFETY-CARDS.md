# Write-method safety cards

All rejected calls must leave canonical state unchanged. No method is payable.

| Method | Caller | Allowed / forbidden states | Time gate | Idempotency and effect | Canonical views / negative tests |
|---|---|---|---|---|---|
| `configure` | owner | `CONFIGURING`; forbidden after configured/active | N/A: pre-activation one-time setup | exactly once; locks roles/profile/allowlist | profile; wrong caller, duplicate, equal/zero roles, malformed allowlist |
| `activate` | owner | configured and inactive only | N/A: configuration phase, no deadline | exactly once; irreversibly active | profile; wrong caller, early, duplicate |
| `create_case` | any nonzero caller | active; unique case | supplied deadline must satisfy `now < deadline` | one case ID once; stores non-authoritative context | case/index; inactive, duplicate, boundary/equality/past, malformed IDs |
| `attest_proposal` | proposal authority | `OPEN`, no proposal record | `now < deadline` | one exact record; recompute digest; may make `READY` | case; wrong signer/state, duplicate, digest mismatch, malformed IDs/content, boundary |
| `attest_batch` | decoder authority | initial `OPEN` or correction from `NONCONFORMANT` | `now < deadline` | initial revision 1; correction strictly increments; recompute digest; resets semantic fields and may make `READY` | case; wrong signer/state, duplicate/stale revision, digest mismatch, selector/schema violations, boundary |
| `request_review` | any | `READY` only | `now < deadline` | one attempt; deterministically valid conformant output grants one nonce; otherwise no right | case/can-consume; wrong state, malformed/malicious result, prompt injection, boundary |
| `retry_review` | any | `UNVERIFIABLE` only, exact evidence unchanged | `now < deadline` | increments attempt; never duplicates nonce | case/can-consume; wrong state, changed/missing evidence, boundary |
| `consume_authorization` | governance authority | `AUTHORIZED`, unconsumed | `now < deadline` | exact case/revision/digest/nonce once; status becomes `CONSUMED` | case/can-consume; wrong caller/state/digest/revision/nonce, duplicate, boundary |
| `expire_case` | any | any unconsumed nonterminal state | `now >= deadline`; equality is late | once; removes any unconsumed internal right and sets `EXPIRED` | case/can-consume; early, consumed/expired duplicate, boundary ±1 |
