# Implementation and TDD plan

1. Lock specification, source/compatibility matrix, claims, authority/value matrices, and safety cards.
2. Write failing direct tests for configuration, authority, exact digest binding, state transitions, deadlines, result invariants, recovery, correction, and one-time consumption.
3. Implement one pinned `GovernanceIntentGate(gl.Contract)` class with bounded JSON parsing and custom independent validator logic.
4. Run `genvm-lint check` after every contract change; add AST/schema checks proving one class, pinned runner, nondeterminism, no payable/value boundary, and complete interface.
5. Run all direct tests. Add integration/preflight tests for source schema, ABI round-trips, comparative validator behavior, LLM capability, fee profile, transaction receipt normalization, commitment mismatch, and finalized semantic consequence.
6. `npm run check` aggregates lint, direct tests, static policy tests, and deployment-script tests. No frontend/build step exists for this track.
7. Run Studio Dev read-only preflight. Only after it passes, use the resumable deployment flow, recover prior finalized work by source/network identity, and save only allowlisted evidence fields.
8. Verify finalized lifecycle plus `FINISHED_WITH_RETURN`, semantic `CONFORMANT`, and canonical one-time consequence as three separate facts. Prepare public repository and copy-ready Portal fields, then stop at `SUBMISSION_READY`.

Acceptance requires zero skipped lifecycle phases and no claim based on local-only evidence.
