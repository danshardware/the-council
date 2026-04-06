# Task: Shared S3 Bucket and SSM Parameters

## Parent
- **Requirement**: REQ-01 Shared Resources
- **Story**: S01 Shared Resources Bootstrap

## Description
Create the single shared S3 bucket used across all components and SSM Parameter Store keys for shared configuration (project name, environment, bucket name, region). Each component deploys its own Terraform resources (Lambda, API Gateway, IAM, etc.) alongside its code — this task only covers the shared resources that multiple components depend on.

## Acceptance Criteria
- [ ] **AC-01**: Terraform project initialized with local backend and latest AWS provider.
- [ ] **AC-02**: Single S3 bucket created with prefixes for: `config/`, `agent-logs/`, `files/`, `memory/`, `messages/`, `web-ui/`. Versioning enabled.
- [ ] **AC-03**: SSM parameters created for: `council-${Environment}/bucket-name`.
- [ ] **AC-04**: Lifecycle policy on `agent-logs/` prefix (90-day expiry).
- [ ] **AC-05**: Encryption at rest enabled (SSE-S3).
- [ ] **AC-06**: No hardcoded AWS account IDs, regions, or secrets in any `.tf` file. All from environment.
- [ ] **AC-07**: `terraform init && terraform plan && terraform apply` succeeds cleanly.

## QA Checklist
- [ ] `terraform fmt -check` and `terraform validate` pass.
- [ ] All resources tagged with `project=the-council` and `environment` ( default should be 'dev').
- [ ] **Constitution: Serverless-First (I)**: S3 and SSM scale to zero cost when idle.
- [ ] **Constitution: Security (VI)**: No credentials in code. Public access blocked.
- [ ] **Constitution: Simplicity (VII)**: One bucket, not many. Prefixes separate concerns.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
