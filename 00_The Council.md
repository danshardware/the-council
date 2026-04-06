# The Council

## Project description

The council is an agent swarm that is dedicated to a single enterprise.

## Actors

- The board: The humans in the enterprise that gate all work
- Long-term agents: These agents have extensive access to instatutional knowledge, memory, and specific operating areas. Think: CFO, VP of Marketing, Etc.
- Short-term Agents: Contractors. Are assigned a well-scoped thing to work on and get a workspace to perform their functions.

## General Requirements

The Council is a serverless application that runs on AWS. The baseline system should consist of lambdas for handling small funcntions, Bedrock LLMs for most LLM Work, and AgentCore for major work. Storage uses CodeCommit for code, S3 for the vast majority of file storage and KV entries, and DynamoDB for advanced stores.

## Agents

### Functional Requirements
- Modular agents
    - Agents can be defined programatically via YAML files. They can also be created on the fly by the AI should it need a specialized function.
    - Agent prompts come from an MCP Server
    - Agents can have multiple sessions open
    - Every action is logged in a form making it easy to inspect the workflow.
- Long Term Agents
    - Have memory, personality, custom tooling, and permissions for resources
    - General workflow is Agent > Thinking > Guardrails > Checkpoint (prevent irreversable changes) > ACTION (tools, user feed back, communicate, stop) > Guardrails > Decide Next Step
    - On various checkpoints (end of a session, or throughout a longer session) a second agent is used to create new memories
- Agent communication
    - Agents have a message board that has a series of rooms for general use, as well as on-the-fly created rooms for various other purposes
    - Messages in the boards queues a message to the every taget agent in the room
    - Agent to Agent direst messages are allowed.
    - Messages reference internal resources such as files, repositories, conversation UUIDs, etc. Messages without a conversation ID are assumed to be for a thing.
- Functional Agents
    - Perform a single, well defined function: Spot inconsitencies. Research this. Write this code.

### Technical Requirements

- Agents should be based on the Pocket Flow system with the typing issues worked out. 
- We should avoid using expensive LLMs for anything but the use cases where they care
- Pocket Flow blocks should exist for various critical functions:
    - Extract facts
    - Extract memory
    - Check for prompt injection, or non-sequitre content that doesn't belong
    - Have we strayed from the overall goals
- Prockflow flows should exist for important patterns:
    - Ralph loops
    - Chain of Thought
    - Any others?
- LLM Interactions should use my conversations API interface.

## Communication Channels

The software should be able to communicate with people over various cahnnels:

- Direct Web Chat (critical)
- Discord (important)
- Slack (eventually)
- Teams (eventually)

## Memory

Memory is a database that consists of things agents may need to look up in a given space. Some memory is permanent throughout an agent's life, some is shared across all agents, and some is temporary. 

The use case is so an agent can quickly check its memory for information about things that it needed to know in the past, rather than re-deriving th information. Example: 

- What it can store
    - Things that happened and the result, like conversations with the board, short term goals, etc.
    - Facts
    - Numbers
    - commonly used data
    - Really, anything the Agents may need to keep tabs on
- What it can't store
    - passwords
    - large data. It should be stored in files and referenced
- Requirements
    - Should be searchable by either asking a question or by keywords
    - Each memory entry should be structured to have the information, any keywords, and any related information that would come in handy to explain why the memory exists

## Tools

- Basic file tools
    - Search
    - Read
    - Edit
- Git Kraken
- Execute - Execute commands with some restrictions
- Run Sub Agent
- AgentChat
- Get human input
- Get approvals
- Session TODO
- Kanban work board that support the very basics of swimlanes, item dependancy, and agent/human assignment
- Web - Should allow for either a headless browser or connecting to the debug port on a human run browser
    - Browse
    - Download
    - Search
    - All the normal stuff on running web browser
- SmithyAI Tools (in progress)
    - KV Store
    - Documentation
    - Vector Store
- Deep Research
- Coding
- AWS Athena

Try to get as many of these from existing code bases as possible

## Triggering actions

- Actions can be scheduled. These can either be programs to run, or prompts to send to an agent.
- AWS Events can be mapped to prompts.
- Chat triggers agents.

## UI/UX

This should have a basic UI on the web for:
- Show history of agent activity in a nice panel that allows the user to view what was done
    - Each action is presented by agent and session, and can follow conversations that get pushed to sub agents
    - Each type of action (thinking, tool call, gaurdrail, etc.) is presented with its own Icon/Emoji and there is an internal default state as to whether to expand the full display or show only the high-level task.
    - Session should list all resources touched and actions taken in a table.
    - Like Github Copilot
- Allow editing of config files and resources. 
    - VS Code web would be great. Since all long-term storage is in S3 or code commit, it would need to be brought into a temporary location for editing, or provide an adapter so VS COde can handle it.
- Allow editing config
- Reference OpenClaw for UX decisions

## Technical

Python 3.14, AWS, Terraform (latest) with latest AWS provider.

## Gotchas

Avoid anything that spins up long-standing resources.

