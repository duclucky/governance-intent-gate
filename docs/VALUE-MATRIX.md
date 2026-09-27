# Value destination matrix

This contract has no application value flow.

| Item | Source | Locked state | Release/refund/forfeit | Terminal proof |
|---|---|---|---|---|
| GEN, token, bond, fee, reward, escrow, credit | N/A | N/A | N/A | no payable methods, no ledger, no transfer, no EVM interface, no emitted value message |

Consensus protocol fees for deployment/write transactions are external execution costs, not contract-held application value. Deployment evidence must report estimated/deposited/consumed/refunded protocol fee fields when available and must not describe them as escrow.
