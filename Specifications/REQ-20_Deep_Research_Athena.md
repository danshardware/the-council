# REQ-20: Deep Research & AWS Athena

## Overview
Research agent patterns for deep investigation tasks, and AWS Athena integration for querying structured data at scale.

## Source
- [00_The Council.md](../00_The%20Council.md) → Tools (Deep Research, AWS Athena)

## Phase
Phase 3 — Future

## Functional Requirements

- **FR-20.01**: **Deep Research Flow**: PocketFlow flow that implements recursive map-reduce research — iteratively searching, gathering, synthesizing, and refining information. Reference PocketFlow's Deep Research cookbook example.
- **FR-20.02**: **AWS Athena Tool**: Execute SQL queries against data in S3 via Athena. Return results as structured data.
- **FR-20.03**: Athena queries scoped to agent permissions — agents can only query datasets they have access to.
- **FR-20.04**: Research results stored as files in S3 and referenced in agent memory.

## Acceptance Criteria

- **AC-20.01**: A deep research agent given a topic produces a multi-source research report.
- **AC-20.02**: An agent runs an Athena query and gets structured results.
- **AC-20.03**: An agent without Athena permissions cannot run queries.

## Dependencies

- **Depends on**: REQ-01 (S3, Athena), REQ-02 (PocketFlow flows), REQ-06 (Memory for storing findings)
