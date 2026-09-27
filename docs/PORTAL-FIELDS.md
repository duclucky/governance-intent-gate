# Portal fields — copy-ready except publication links

Submission category: `Intelligent Contracts`

Project name: `Governance Intent Gate`

Repository URL: `https://github.com/duclucky/governance-intent-gate`

Successful CI URL: `https://github.com/duclucky/governance-intent-gate/actions/runs/36325722366`

Primary contract Explorer: `https://explorer-studio-dev.genlayer.com/address/0x3f6AE21DF18DF4104DD3b0a5596612B9C17240D2`

Lifecycle evidence: `https://explorer-studio-dev.genlayer.com/tx/0xa2feb1ec10cf521d33d4a350b29a290e2090cd6bcbe8d8c738009563a0db0b29`

Finalized consequence: `https://explorer-studio-dev.genlayer.com/tx/0x8b30a034d56acdfd726a890e350e05e9bfd0ec2e1a42fcb1422c21a21aeebfa9`

Contract/test counts: `1 Intelligent Contract; 29 automated tests (22 direct, 6 local SDK/parser/source-policy/CI-environment, 1 Studio Dev read-only integration).`

Description:

> Governance Intent Gate is a reusable GenLayer contract that compares exact proposal directives attested by a configured proposal authority with exact modeled batch effects attested by a distinct decoder authority. Validators independently judge symmetric semantic coverage, while deterministic code rejects missing, extra, duplicate, malformed, or inconsistent result entities. A conformant finalized result creates one deadline-bound authorization for the exact case, batch revision, digest, and nonce; only the configured governance authority can consume it once. The Studio Dev lifecycle finalized with `FINISHED_WITH_RETURN`, produced `CONFORMANT`, moved the canonical case to `CONSUMED`, and made `can_consume` false.

What validators inspect:

> Validators inspect the exact stored directive and modeled-effect bytes. They compare every directive and effect, including targets, values, constraints, prohibitions, and sequencing, and return complete ID sets, coverage edges, and bounded discrepancy codes. Embedded evidence text is treated as data, not instructions.

Reuse value:

> Governors, timelocks, Safe modules, and registries can bind their own execution identity to the gate's case/revision/digest/nonce authorization and enforce it at their actual execution boundary.

Limitations:

> The contract does not prove a live DAO vote, decode arbitrary calldata or bytecode, prove hidden runtime behavior, execute modeled calls, move value, or block an external executor without an adapter. The published Studio Dev fixtures are synthetic integration evidence, not adoption evidence. Actual fee use/refund was not exposed by the sanitized receipt and is not claimed.

Submission state: `SUBMISSION_READY`. Public repository and successful CI are verified. Final Portal Submit remains unperformed and requires separate explicit action-time authorization.
