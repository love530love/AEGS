# Executable High-Risk Approval Gates

`decide` is the enforcement point for YELLOW and RED approvals. Before an
approval is recorded, it rechecks that `expires_at` is timezone-qualified and
still future, the structured proposal fields and evidence/rollback/reason are
present, the proposal contains the risk-appropriate approval policy record,
and the owner approver is named in the Charter and independent of the proposer.

RED additionally requires a second, distinct reviewer named in the Charter's
`independent_reviewers` list. A missing, self, or unqualified reviewer is
rejected before any directive or ledger event is written. This remains a local
identity policy; it does not provide authentication or signatures.

GREEN keeps its existing owner-only decision path and does not require the
high-risk fields or independent review.
