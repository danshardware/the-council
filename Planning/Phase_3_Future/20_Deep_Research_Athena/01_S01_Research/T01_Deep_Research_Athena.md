# Task: Deep Research and Athena Query Tools

## Parent
- **Requirement**: REQ-20 Deep Research & Athena
- **Story**: S01 Research Tools

## Description
Implement deep research tool (multi-step web research with synthesis) and AWS Athena query tool (SQL over S3 data lakes).

## Acceptance Criteria
- [ ] **AC-01**: `deep_research(question, depth)` spawns a sub-agent that iteratively searches, reads, and synthesizes findings.
- [ ] **AC-02**: Research results stored in memory with source citations.
- [ ] **AC-03**: `athena_query(sql, database)` executes Athena SQL, waits for results, returns formatted data.
- [ ] **AC-04**: Athena queries restricted to read-only (SELECT only, no DDL/DML).
- [ ] **AC-05**: Cost tracking: research token usage and Athena data scanned reported.

## QA Checklist
- [ ] pytest tests: research flow steps, Athena query formatting, result parsing.
- [ ] **Constitution: Cost (IV)**: Token and Athena cost budgets enforced.
- [ ] **Constitution: Security (VI)**: Athena queries sanitized, SELECT-only enforced.
- [ ] **Constitution: Observability (V)**: Research steps and Athena queries logged.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
