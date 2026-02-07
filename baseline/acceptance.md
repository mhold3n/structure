# Baseline Acceptance Criteria

The system is considered "ready for baseline" when the following criteria are met:

## 1. Regression Suite

- [ ] All `eval/regression_locked` tests pass with exact string match (D1).
- [ ] No regressions in latency or token usage > 5% from previous baseline.

## 2. Contamination Audit

- [ ] `scripts/contamination_audit.py` returns SUCCESS (no overlap between Train/Dev and Test).

## 3. Observability

- [ ] Traces are generated for 100% of requests.
- [ ] Logs contain `correlation_id` linking across services.

## 4. Safety & Policy

- [ ] Safety gates block 100% of "adversarial harmful" test cases.
- [ ] Compliance checker enforces role-based access control.

## 5. Stability

- [ ] System handles 10 concurrent requests without crashing or timeout.
- [ ] Bootstrap service verifies health of all dependencies on startup.
