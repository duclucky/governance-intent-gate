# Evidence authority matrix

| Input | Authority and authentication | Exact binding / anti-replay | Safe failure | Consequence access |
|---|---|---|---|---|
| Profile | immutable owner transaction signer before activation | contract address, chain, profile ID/version, origins, roles, decoder version, allowlist | revert | gates all later methods |
| Passed proposal record | configured proposal authority via `gl.message.sender_address` | case/proposal ID, proposal version, deadline, exact directive bytes and recomputed digest | revert before review; case remains open | required but cannot authorize alone |
| Decoded batch record | configured, distinct decoder authority via transaction signer | case/proposal identity, decoder version, strictly increasing batch revision, exact effect bytes and recomputed digest | revert before review; no right | required but cannot authorize alone |
| Optional context | case creator, recorded only | case and exact stored bytes | ignore for authority | never grants, denies, or modifies a right |
| Semantic result | GenLayer leader/validator path plus deterministic settlement checks | exact stored evidence digests, case/revision, complete ID sets/edges/codes | `UNVERIFIABLE`, retryable, no authorization | conformant valid result only |

Artifact prose cannot redefine authority, canonical objectives, identities, consequence rules, or destinations. A valid digest without the correct transaction signer is rejected. Digest/content mismatch never reaches the LLM.
