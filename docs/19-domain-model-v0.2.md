# AEGS v0.2 Domain Model

> Status: Proposed baseline
> Version: 0.2.0
> Purpose: establish the minimum domain language before expanding the runtime.

## 1. Why this document exists

AEGS currently has a strong governance/control-plane prototype, but the implementation still models governance mechanics more completely than it models the actual evolution lifecycle.

The next step is therefore **not** to add more agents, token systems, or UI. First establish a stable domain model that can represent what AEGS is trying to learn, evaluate, change, and later verify.

The central chain is:

```text
Question / Requirement
        ↓
       Task
        ↓
      Trace
        ↓
 Evidence + Hypothesis
        ↓
    Experiment
        ↓
    Evaluation
        ↓
     Decision
        ↓
      Action
        ↓
     Outcome
        ↓
   Experience
        ↓
   Capability / Skill
```

This is a conceptual lifecycle, not a requirement that every task instantiate every object.

## 2. First-class objects

### 2.1 Task

A bounded unit of work with an objective, scope, constraints, owner, and expected completion criteria.

Minimum fields:

- `task_id`
- `objective`
- `scope`
- `constraints`
- `created_at`
- `status`
- `owner`

### 2.2 Trace

An ordered record of observable execution facts. Trace answers **what happened**, not why it was correct.

Minimum fields:

- `trace_id`
- `task_id`
- `timestamp`
- `actor`
- `action`
- `input_ref`
- `output_ref`
- `environment_ref`

### 2.3 Evidence

A verifiable support item for a claim, hypothesis, evaluation, or decision.

Evidence must identify its source and verification method. An assertion is not evidence merely because an agent produced it.

Minimum fields:

- `evidence_id`
- `claim`
- `source_ref`
- `verification_method`
- `strength`
- `provenance_ref`

### 2.4 Hypothesis

A falsifiable explanation or proposed improvement that can be investigated.

Minimum fields:

- `hypothesis_id`
- `statement`
- `assumptions`
- `falsification_condition`
- `confidence`
- `origin_ref`

### 2.5 Experiment

A bounded test of a hypothesis or candidate change.

The experiment freezes enough of its baseline to make the result reproducible.

Minimum fields:

- `experiment_id`
- `hypothesis_ref`
- `candidate_ref`
- `baseline_ref`
- `dataset_or_task_set_ref`
- `environment_ref`
- `metrics`
- `thresholds`
- `seed`
- `status`

### 2.6 Evaluation

A structured judgment of an experiment or candidate against predefined criteria.

Evaluation is distinct from Outcome: an experiment can be evaluated before its real-world consequences are known.

Minimum fields:

- `evaluation_id`
- `experiment_ref`
- `criteria`
- `measurements`
- `comparison_baseline`
- `uncertainty`
- `non_regression_result`
- `transfer_result`
- `safety_result`
- `decision_recommendation`

### 2.7 Decision

A governed choice among candidates, including uncertainty and dissent.

Minimum fields:

- `decision_id`
- `problem_ref`
- `candidate_refs`
- `evidence_refs`
- `supporting_reasons`
- `counterarguments`
- `minority_views`
- `predictions`
- `risks`
- `decision_maker`
- `decision_time`
- `review_date`
- `provenance_ref`

### 2.8 Outcome

The observed real-world result after a decision or action.

Outcome is intentionally first-class because durable improvement cannot be established only by internal evaluation scores.

Minimum fields:

- `outcome_id`
- `decision_ref`
- `action_ref`
- `observed_at`
- `result`
- `success_criteria_result`
- `unexpected_effects`
- `evidence_refs`

Outcome enables longitudinal measurement, forecasting calibration, and decision-quality analysis.

### 2.9 Experience

A structured lesson extracted from multiple facts/evidence/outcomes. Experience is not raw memory and is not automatically trusted knowledge.

Minimum fields:

- `experience_id`
- `pattern`
- `supporting_refs`
- `scope`
- `confidence`
- `known_counterexamples`
- `transfer_tests`
- `status`

An Experience becomes eligible to influence production only through the relevant verification and governance path.

### 2.10 Capability

An approved ability to solve a class of problems. Capability is broader than an individual Skill and may compose several Skills, tools, roles, and policies.

Minimum fields:

- `capability_id`
- `problem_class`
- `skill_refs`
- `tool_refs`
- `verification_profile`
- `supported_scope`
- `known_limits`
- `version`
- `approval_ref`

### 2.11 Skill

A deployable, testable, versioned unit of durable procedure.

Minimum fields:

- `skill_id`
- `goal`
- `preconditions`
- `procedure`
- `tools`
- `expected_output`
- `verification`
- `failure_modes`
- `evidence_refs`
- `version`
- `confidence`
- `provenance_ref`

## 3. Supporting objects

The following remain important but should not be confused with the core evidence-to-outcome chain:

- `Agent / Expert`: organizational role with skills, tools, access, and responsibility protocol.
- `Proposal`: governed candidate change.
- `Reputation`: historical performance profile, preferably domain-specific.
- `Authority`: current decision weight, derived from relevant evidence and governance rules; never equivalent to global reputation.
- `Incentive / Penalty`: experimental behavioral feedback mechanisms.
- `Governance`: purpose, boundaries, permissions, risk rules, and human authority.
- `Provenance`: links facts, claims, evidence, experiments, decisions, actions, and versions.
- `Version`: immutable reference to an approved system/capability state.
- `Replay`: reconstruction of a prior execution or decision path.

## 4. Important distinctions

### Evaluation ≠ Outcome

Evaluation asks: **Was the candidate good according to the test?**

Outcome asks: **What actually happened after it was used?**

This distinction prevents AEGS from declaring self-improvement solely because an internal benchmark improved.

### Experience ≠ Memory

Memory stores information. Experience represents a structured, evidence-backed lesson extracted from events and outcomes.

### Reputation ≠ Authority

Reputation describes historical performance. Authority describes how much weight a participant should receive for the current problem and domain.

### Expert ≠ Model instance

An Expert is a role. A role may be fulfilled by one model, several models, a tool, a human, or a combination.

### Capability Radar ≠ Capability Registry

Radar identifies external or internal capabilities worth investigating. Registry contains only capabilities that have passed the applicable evaluation and governance gates.

## 5. Evolution eligibility

No object becomes a production capability merely because it exists.

```text
Observation
  ↓
Evidence / Hypothesis
  ↓
Experiment
  ↓
Evaluation
  ↓
Decision
  ↓
Approval / Version
  ↓
Outcome
  ↓
Experience
  ↓
Transfer verification
  ↓
Capability admission
```

Rejected candidates remain traceable as failure experience. Historical evidence, evaluation results, and decisions are not rewritten to make later evolution look successful.

## 6. v0.2 implementation boundary

The immediate implementation target is deliberately narrow:

1. Define typed/domain representations for the core objects.
2. Give each object a stable identifier and provenance references.
3. Represent lifecycle events separately from current state.
4. Keep `.aegs/state.json` as a current-state index rather than a growing knowledge store.
5. Preserve the append-only ledger for audit events.
6. Add serialization and validation tests before implementing autonomous evolution.

Explicitly deferred from this step:

- foundation-model weight modification;
- tradable token / blockchain;
- autonomous governance modification;
- unrestricted permission expansion;
- large fixed multi-agent swarms;
- automatic production promotion without the applicable policy gate.

## 7. Design test

A future AEGS implementation should be able to answer, for any promoted capability:

> What problem caused it to be proposed, what evidence justified it, what experiment tested it, what baseline was used, who evaluated it, who approved it, what dissent existed, what happened in reality, and what later experience proved or disproved its transfer?

If the system cannot reconstruct that chain, it has automation but not governed self-evolution.
