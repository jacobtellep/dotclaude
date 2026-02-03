# CLAUDE.md - Development Guide

This file provides guidance to Claude Code when working with this repository.

## 🚨 CRITICAL: Automated Checks Are MANDATORY

**ALL hook issues are BLOCKING - EVERYTHING must be ✅ GREEN!**  
Fix ALL issues before continuing. There are NO warnings, only requirements.

When hooks report issues:
1. **STOP** - Address every ❌ issue until everything is ✅ GREEN
2. **VERIFY** - Re-run failed commands to confirm fixes
3. **CONTINUE** - Return to original task only after all issues resolved

## 🎯 Core Workflow

**Research → Plan → Implement** - Always follow this sequence:

1. **Research**: Explore codebase, understand existing patterns
2. **Plan**: Present implementation approach for approval
3. **Implement**: Execute with validation checkpoints

For complex problems, use **"ultrathink"** before proposing solutions.

## 🛠️ Implementation Principles

### Start Simple
- Break tasks into 1-2 file changes maximum
- Ask for approval before each step
- Choose the simplest approach that works
- Build incrementally on working foundations

### Avoid Over-Engineering
- Don't create patterns until explicitly needed
- Use existing libraries vs reinventing
- Focus on solving the immediate problem
- Can a junior developer understand this code?

### Collaboration Pattern
```
Claude: "I need to implement X. Here are options:
A) [Simplest approach - direct solution]
B) [Alternative approach]
C) Show me existing patterns first

Which would you prefer?"
```

## 📁 Project Context

- **Read `PROJECT.md`** at conversation start for architecture/conventions
- **Check `TODO.md`** before new tasks, add if missing
- **Follow existing patterns** found in the codebase
- **Use project's environment management** (virtualenv, nvm, docker, etc.)

## 🧪 Testing Strategy

- **Unit tests** for business logic, utilities, data transformations
- **Skip tests** for simple UI/view layer code
- **Update existing tests** when logic changes
- **Tests in `/tests` folder** mirroring main structure

Include: expected use case, edge case, failure case

## ✅ Task Management

Use TodoWrite tool for complex tasks. Validate at these checkpoints:
- After complete features
- Before new major components  
- When something feels wrong
- **When hooks fail with errors** ❌

## 💻 Development Commands

```pseudocode
[package-manager] run dev      # Development server
[package-manager] run build    # Production build
[package-manager] test         # Run tests
[package-manager] run lint     # Lint code
[package-manager] run format   # Format code
[package-manager] run typecheck # Type checking
```

## 🧠 Essential Rules

- **Never assume** - Ask questions if uncertain
- **Never hallucinate** - Only use verified libraries/functions
- **Prefer editing** existing files over creating new ones
- **Never create files** unless absolutely necessary
- **Do what's asked** - nothing more, nothing less

## 🏗️ Architecture Essentials

Follow existing project patterns for:
- **Security**: Input validation, parameterized queries, secure secrets
- **APIs**: Consistent error handling, proper status codes
- **Database**: Migrations, indexing, connection pooling
- **Config**: Environment variables, centralized settings

## 🎯 Definition of Done

Code is complete when:
- ✅ All linters pass with zero issues
- ✅ All tests pass
- ✅ Feature works end-to-end
- ✅ Dead code removed
- ✅ Simple enough for any developer to understand

## Project-Specific Configuration

Add project details below:

---

### Technology Stack
[Your language, framework, and tools]

### Development Environment  
[Setup instructions, dependencies]

### Project-Specific Commands
[Any unique commands or workflows]

### Additional Guidelines
[Project-specific conventions or requirements]