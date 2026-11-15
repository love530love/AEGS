# ADR-0006: Establish the AEGS v0.2 Domain Model Before Runtime Expansion

- Status: Accepted as v0.2 implementation direction
- Date: 2026-09-13
- Scope: domain model and implementation sequencing

## Context

AEGS already has a meaningful governance control plane: Charter, policy-oriented decisions, handoffs, read-only architecture discovery, and an append-only event ledger.

The current Python implementation, however, is still concentrated in a small prototype core and does not yet provide first-class representations for the full self-evolution lifecycle.

Adding more autonomous agents, incentives, reputation, or UI before stabilising this domain language would create architectural debt and make later audit/replay harder.

## Decision

AEGS v0.2 will establish a first-class domain model before implementing broad autonomous evolution.

The primary objects are:

`Task → Trace → Evidence/Hypothesis → Experiment → Evaluation → Decision → Action → Outcome → Experience → Capability/Skill`

Supporting objects include Proposal, Agent/Expert, Reputation, Authority, Incentive/Penalty, Governance, Provenance, Version, and Replay.

The following distinctions are normative:

1. Evaluation is not Outcome.
2. Experience is not generic Memory.
3. Reputation is not Authority.
4. Expert is a role, not a permanent model instance.
5. Capability Radar is not Capability Registry.
6. Existence of a candidate does not imply production eligibility.

## Consequences

### Positive

- Gives AEGS a stable vocabulary for future code and documentation.
- Makes longitudinal improvement measurable through real-world Outcomes.
- Makes provenance and replay requirements explicit.
- Prevents governance mechanics from becoming the accidental domain model.
- Provides a controlled foundation for later Reputation, Incentive, Forecasting, and Meta-Evolution work.

### Negative

- Delays implementation of visible autonomous features.
- Requires additional schemas, validation, serialization, and tests.
- Some domain boundaries will remain experimental until real workloads expose their limits.

## Implementation sequence

1. Fix the test/packaging foundation so `pytest` can import the src-layout package.
2. Add typed domain entities and validation without changing autonomous behaviour.
3. Add lifecycle event representations and provenance references.
4. Add persistence adapters only after the domain contract is testable.
5. Implement Shadow Experiment and Evaluation around the domain objects.
6. Add promotion/rollback integration through the existing governance gate.
7. Only then introduce adaptive expert composition, contribution/reputation experiments, and broader self-evolution.

## Non-goals

This ADR does not authorise:

- foundation-model weight self-modification;
- autonomous governance-rule activation;
- permission expansion;
- tradable tokens or blockchain;
- unrestricted production writes;
- fixed-size multi-agent swarms.

## Acceptance test

For every promoted capability, AEGS should eventually reconstruct:

`problem → evidence → experiment → evaluation → decision → approval → action → outcome → experience → transfer evidence`

If that chain cannot be reconstructed, the change is not yet demonstrably governed self-evolution.
