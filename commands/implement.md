# Implement Feature

---
description: Research, plan, and implement features following CLAUDE.md principles
allowed-tools: Read, Glob, Grep, Task, TodoWrite, WebFetch, WebSearch, Edit, MultiEdit, Write, Bash
---

## Feature Request: $ARGUMENTS

**Following CLAUDE.md workflow: Research → Plan → Implement**

## Process

### 1. Research Phase
- Read feature requirements thoroughly
- Explore codebase for existing patterns to follow
- Identify integration points and dependencies
- Search for relevant documentation/examples online if needed

### 2. Planning Phase
Present implementation approach:
```
I found these patterns to follow: [specific files/examples]
My approach: [simple, clear explanation]
Key integration points: [where this connects to existing code]
Validation strategy: [how we'll test this works]

Options:
A) [Recommended approach - simplest]
B) [Alternative approach]

Which would you prefer?
```

### 3. Implementation Phase
- Use TodoWrite for complex features to track progress
- Break into logical, manageable steps
- Show progress after each significant change
- Run validation commands as specified in CLAUDE.md
- Get approval at key checkpoints

## Context to Include

**Essential only - avoid over-specification:**
- Existing patterns to mirror (specific files)
- Integration requirements (where code connects)
- Validation commands (tests, lints, builds)
- Project-specific gotchas (from PROJECT.md)

## Validation Checkpoints

Stop and validate after:
- Each complete logical unit of work
- Before major architectural decisions
- When encountering unexpected issues
- Before declaring feature complete

**Remember**: Follow all CLAUDE.md principles - start simple, ask for approval, validate incrementally.