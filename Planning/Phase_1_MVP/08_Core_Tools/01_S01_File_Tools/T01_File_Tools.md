# Task: File Tools (Search, Read, Edit)

## Parent
- **Requirement**: REQ-08 Core Tools
- **Story**: S01 File Tools

## Description
Implement file manipulation tools as BedrockTool-registered functions: search files in S3, read file contents, and create/update/delete files.

## Acceptance Criteria
- [ ] **AC-01**: `file_search(pattern, prefix)` returns matching file keys from S3.
- [ ] **AC-02**: `file_read(key)` returns file content for text files, presigned URL for large/binary files.
- [ ] **AC-03**: `file_write(key, content)` creates or updates a file in S3.
- [ ] **AC-04**: `file_delete(key)` deletes a file (marked as destructive for checkpoint).
- [ ] **AC-05**: All operations scoped to agent's permitted S3 prefix.
- [ ] **AC-06**: All functions registered via `@bedrock_tool` decorator.
- [ ] **AC-07**: File operations logged with action logging system.

## QA Checklist
- [ ] pytest tests: each operation, permission scoping, large file handling, logging.
- [ ] **Constitution: Security (VI)**: Agents can't access files outside their permitted prefix.
- [ ] **Constitution: Observability (V)**: All file ops logged.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
