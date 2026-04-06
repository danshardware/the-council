# REQ-01: Shared Resources

## Overview
Create the shared AWS resources that multiple components depend on: a single S3 bucket (with prefixes for different data types) and SSM Parameter Store keys for shared configuration. Each component (agent framework, web chat, dashboard, etc.) deploys its own compute, API, and IAM resources via Terraform alongside its code.

## Source
- [00_The Council.md](../00_The%20Council.md) → General Requirements, Technical

## Phase
Phase 1 — MVP (Critical)

## Functional Requirements

- **FR-01.01**: Terraform project initialized with local backend, latest AWS provider.
- **FR-01.02**: Single S3 bucket provisioned with prefixes: `config/`, `agent-logs/`, `files/`, `memory/`, `messages/`, `web-ui/`, `agent-state/`.
- **FR-01.03**: S3 versioning enabled for data integrity.
- **FR-01.04**: Lifecycle policy on `agent-logs/` prefix (90-day expiry).
- **FR-01.05**: SSM parameters: `/council/bucket-name`, `/council/environment`, `/council/region`.
- **FR-01.06**: All configuration sourced from environment variables — no hardcoded accounts, regions, or secrets.

## Design Principle
Infrastructure is co-located with code. Each requirement's implementation includes its own Terraform for Lambda functions, API Gateway routes, IAM roles, EventBridge rules, SQS queues, etc. This requirement only covers the shared resources that cannot be owned by a single component.

## Non-Functional Requirements

- **NFR-01.01**: S3 bucket scales to zero cost when empty.
- **NFR-01.02**: Terraform state stored locally (migrateable to S3 later).
- **NFR-01.03**: All resources tagged with `project=the-council` and `environment` tag.

## Acceptance Criteria

- **AC-01.01**: `terraform init && terraform plan` succeeds with no errors from a fresh clone.
- **AC-01.02**: `terraform apply` creates the S3 bucket and SSM parameters. `terraform destroy` removes them cleanly.
- **AC-01.03**: S3 bucket is accessible and prefixes are writable.
- **AC-01.04**: SSM parameters are readable from Lambda (verified by integration test with a later component).
- **AC-01.05**: No hardcoded AWS account IDs, regions, or secrets in any Terraform file.

## QA Checklist

- [ ] **Unit Tests**: `terraform validate` passes. `terraform fmt -check` passes.
- [ ] **Integration Tests**: Apply, write to bucket, read SSM params, destroy cleanly.
- [ ] **Human Walkthrough**: Run `terraform apply`, verify bucket exists, verify SSM params, clean destroy.
- [ ] **Constitution: Serverless-First (I)**: Only S3 and SSM. No compute resources.
- [ ] **Constitution: Security (VI)**: No credentials in code. Public access blocked. Encryption at rest.
- [ ] **Constitution: Simplicity (VII)**: One bucket. Prefixes separate concerns. Nothing more.

## Dependencies

- **Depends on**: Nothing (this is the foundation)
- **Blocks**: REQ-02 through REQ-20 (all components use the shared bucket)
