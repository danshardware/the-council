# REQ-12: Long-term Agent Features

## Overview
Extend agents with persistent personality, custom tooling, permissions, and a companion memory-writing agent. Long-term agents are the "executives" (CFO, VP of Marketing, etc.) with deep institutional knowledge.

## Source
- [00_The Council.md](../00_The%20Council.md) → Actors (Long-term agents), Agents: Functional Requirements (Long Term Agents)

## Phase
Phase 2 — Important

## Functional Requirements

- **FR-12.01**: Long-term agents have **personality** defined in YAML: communication style, priorities, decision-making tendencies.
- **FR-12.02**: Long-term agents have **custom tooling**: agent-specific tools beyond the core set, configured in YAML.
- **FR-12.03**: Long-term agents have **permissions**: explicit access controls for files, commands, rooms, and other agents.
- **FR-12.04**: Long-term agents have **persistent memory** that accumulates across all sessions (uses REQ-06 permanent scope).
- **FR-12.05**: **Memory-writing companion agent**: At session end (or periodically during long sessions), a separate agent reviews the session and creates new memories — summarizing decisions, facts learned, and important outcomes.
- **FR-12.06**: Long-term agents can be "introduced" to each other with role descriptions for effective collaboration.
- **FR-12.07**: Each long-term agent has a profile page in the dashboard showing: role, personality summary, recent activity, memory stats, and active sessions.

## Acceptance Criteria

- **AC-12.01**: An agent with a defined personality consistently reflects that personality in its communications.
- **AC-12.02**: An agent with custom tools can use those tools; an agent without them cannot.
- **AC-12.03**: Permission boundaries prevent an agent from accessing restricted resources.
- **AC-12.04**: After a session, the memory-writing agent creates at least one relevant memory entry.
- **AC-12.05**: Memories from the companion agent are searchable in subsequent sessions.
- **AC-12.06**: Agent profile page shows correct and current information.

## QA Checklist

- [ ] **Unit Tests**: Personality injection, permission enforcement, memory agent trigger, profile data aggregation.
- [ ] **Integration Tests**: Full lifecycle: agent session → memory agent runs → memories persist → next session retrieves them.
- [ ] **Human Walkthrough**: Run a long-term agent through multiple sessions. Verify personality consistency, memory accumulation, and permission enforcement.
- [ ] **Constitution: Agent Modularity (II)**: Personality and tools are configuration, not hardcoded.
- [ ] **Constitution: Security (VI)**: Permissions enforced at tool invocation layer.
- [ ] **Constitution: Cost-Conscious (IV)**: Memory-writing agent uses a cheap model.

## Dependencies

- **Depends on**: REQ-05 (Workflow Engine), REQ-06 (Memory System), REQ-07 (Communication)
- **Blocks**: REQ-13 (Short-term agents are managed by long-term agents)
