# Task: Schedule Engine

## Parent
- **Requirement**: REQ-11 Triggering & Scheduling
- **Story**: S01 Schedule Engine

## Description
Implement cron-style scheduling that triggers programs (Lambdas) or prompts sent to agents. Schedules stored as YAML/JSON in S3 under `config/schedules/`, executed via EventBridge.

## Acceptance Criteria
- [ ] **AC-01**: Schedule definition: name, cron_expression, target (lambda_arn or agent_id + prompt), enabled, conditions.
- [ ] **AC-02**: Schedules stored in S3 `config/schedules/` as JSON files. CRUD via API.
- [ ] **AC-03**: Active schedules create corresponding EventBridge rules that invoke a dispatcher Lambda.
- [ ] **AC-04**: Dispatcher Lambda routes the trigger to the correct target (Lambda or agent).
- [ ] **AC-05**: Failed executions retry up to 3 times with exponential backoff.
- [ ] **AC-06**: All trigger executions logged in action_logs (S3 JSONL).

## QA Checklist
- [ ] pytest tests: schedule CRUD, cron parsing, dispatch routing, retry logic, logging.- [ ] **Constitution: Serverless-First (I)**: EventBridge + Lambda. No cron daemons.
- [ ] **Constitution: Observability (V)**: Trigger execution logged.
- [ ] **Constitution: Security (VI)**: Schedule payloads validated.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
