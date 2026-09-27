# Official source and compatibility lock

Retrieved: `2026-09-27` UTC. Target: GenLayer Studio Dev release-candidate environment.

## Official sources

| Subject | Official source | Locked support boundary |
|---|---|---|
| Network identity | https://docs.genlayer.com/developers/intelligent-contracts/deploying/network-configuration | `studio-dev`, RPC `https://studio-dev.genlayer.com/api`, chain ID `61997`; never substitute Studionet `61999` |
| RC family and success semantics | https://docs.genlayer.com/developers/consensus-v06-migration | Consensus v0.6 RC / Studio v0.123 RC; success requires accepted/finalized lifecycle **and** `FINISHED_WITH_RETURN` |
| Contract runner baseline | https://docs.genlayer.com/developers/intelligent-contracts/first-contract | docs still show the older `1jb45...` hash; current RC tooling emitted a material-drift warning and supplied the replacement below |
| Equivalence | https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle plus current SDK API export | current v0.3 `gl.vm.run_nondet`; validator independently reruns the semantic task and compares critical normalized fields |
| Transaction time | https://docs.genlayer.com/developers/intelligent-contracts/features/transaction-context | transaction-pinned UTC time; equality at a deadline is late |
| Testing | https://docs.genlayer.com/developers/intelligent-contracts/testing | direct tests cover deterministic logic; integration/Studio tests cover validator consensus and actual GenVM behavior |
| Finality | https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy/finality | `ACCEPTED` is provisional and can still contain an execution error |

## Compatibility matrix

| Layer | Exact observed/pinned value | Check |
|---|---|---|
| Python | CPython `3.12.13` via `uv` | `.venv/Scripts/python --version` |
| Contract runner | `py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng` | reported by `genvm-lint 0.11.1rc2` as the current runner; must pass lint, schema, direct tests, and Studio Dev code-schema preflight before deployment |
| `genlayer-py` | `0.19.0rc2` | dependency lock and `pip show` |
| `genlayer-test` / `gltest` | `0.30.0rc2` | dependency lock and direct/integration test reports |
| `genvm-linter` | `0.11.1rc2` | dependency lock and `genvm-lint check` |
| GenLayer CLI | `0.40.0-rc.3` | `genlayer --version` |
| Network alias | `studio-dev` | `genlayer network list/info` |
| RPC / chain | `https://studio-dev.genlayer.com/api` / `61997` | CLI network info plus RPC preflight |
| Receipt rule | lifecycle `FINALIZED` and execution `FINISHED_WITH_RETURN` | sanitized deployment evidence |
| Explorer | current URL returned by the matching `studio-dev` chain definition | resolve at deployment; do not hardcode a stale explorer |

Material drift from old Forge notes: the canonical preview endpoint is Studio Dev, not a `studio-next` RPC; the coherent v0.6 RC tooling family and fee profile are required. On 2026-09-27 the current linter also identified `5jyc...qng` as newer than the hash still rendered in the docs; the old hash failed direct-loader initialization with `unexpected end of memory`. The replacement passed lint, strict typecheck, local schema/direct checks, Studio Dev code-schema preflight, exact deployed-source retrieval, finalized deployment, and a seven-write semantic lifecycle. Any later runner, RC family, chain identity, schema, fee, or receipt-shape change invalidates this lock and blocks deployment until the matrix is re-proven.
