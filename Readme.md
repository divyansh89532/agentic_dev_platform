# Agentic Developer Platform — Project Overview

## Executive Summary

The **Agentic Developer Platform** is an AI-powered system that automates the initial development setup for backend projects. Given a natural-language description (e.g., "Create a blog platform with posts and comments"), it generates structured requirements, designs a database schema, validates and reviews the design, optionally pauses for human approval, proposes a Git strategy with starter files, and can push the result to GitHub.

Built on **IBM watsonx.ai** and **LangChain**, it targets developers who want to move quickly from idea to a scaffolded, version-controlled project.

---

## Problem Statement

Traditional development setup is manual and time-consuming:

- Translating vague ideas into requirements
- Designing normalized database schemas
- Setting up repositories, branches, and boilerplate
- Establishing governance (validation, review, approval) before committing

This platform automates that flow and adds a **human-in-the-loop** approval step for higher-risk designs.

---

## Solution Overview

A multi-step pipeline that:

1. **Extracts requirements** from natural language using an LLM
2. **Designs a database schema** (tables, columns, relationships, SQL)
3. **Validates** the design (deterministic checks)
4. **Reviews** the design for risk and governance
5. **Pauses for human approval** when review deems it necessary
6. **Proposes a Git strategy** (branch, structure, starter files)
7. **Optionally pushes** the generated structure to GitHub (including repo creation for new projects)

---

## Architecture

### High-Level Flow

```
User Prompt
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Requirements Agent (LLM)                                     │
│     → Entities, relationships, assumptions, out-of-scope         │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Database Architect Agent (LLM)                               │
│     → Tables, columns, normalization, SQL schema                 │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Validation Skill (deterministic)                             │
│     → Schema checks, required fields, constraints                │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Review Agent (LLM)                                           │
│     → Assessment, issues, risk level, approval_required          │
└─────────────────────────────────────────────────────────────────┘
    │
    ├── approval_required? ── Yes ──► PENDING_APPROVAL
    │                                      │
    │                                      ▼
    │                              Human: POST /approval
    │                                      │
    │                                      ▼
    │                              POST /orchestrate/continue
    │
    └── No (or after approval) ────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. Git Agent (LLM)                                              │
│     → Branch name, structure, files (README, .gitignore, etc.)   │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. Git Execution                                                │
│     → Simulated (github_skill) or Real (github_push_skill)       │
└─────────────────────────────────────────────────────────────────┘
```

### Component Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **LLM** | IBM watsonx.ai (via LangChain) | Structured generation for requirements, DB design, review, Git strategy |
| **Framework** | LangChain + Pydantic | Structured output, schema validation, retry logic |
| **API** | FastAPI | REST endpoints for orchestration and tools |
| **UI** | Streamlit | Interactive demo and approval workflow |
| **External** | PyGithub | Real GitHub repository and file creation |

---

## Project Structure

```
agentic_dev_platform/
├── app/
│   ├── main.py                 # FastAPI app, all endpoints
│   ├── orchestrator/
│   │   └── orchestrator.py     # Pipeline orchestration
│   ├── agents/                 # LLM-powered agents
│   │   ├── requirements_agent.py
│   │   ├── db_architect_agent.py
│   │   ├── review_agent.py
│   │   └── git_agent.py
│   ├── skills/                 # Deterministic + external tools
│   │   ├── validation_skill.py
│   │   ├── github_push_skill.py
│   │   └── github_skill.py
│   ├── models/
│   │   └── schemas.py          # Pydantic models
│   └── utils/
│       ├── langchain_watsonx.py
│       ├── approval_store.py
│       └── watsonx_client.py
├── streamlit_app.py            # Web UI
├── openapi_exports/            # OpenAPI specs for watsonx Orchestrate
├── requirements.txt
└── Documentation (DEPLOYMENT.md, WATSONX_ORCHESTRATE.md, etc.)
```

---

## Core Components

### 1. Agents (LLM-Powered)

| Agent | Input | Output | Role |
|-------|-------|--------|------|
| **Requirements** | User prompt | Entities, relationships, assumptions, out-of-scope | Turn natural language into structured requirements |
| **Database Architect** | Requirements | Tables, columns, normalization, SQL schema | Design normalized schema |
| **Review** | Database design | Assessment, issues, risk level, approval_required | Governance and risk checks |
| **Git Strategy** | Project context (type, framework, language) | Branch, structure, files (path + content) | Propose repo layout and starter files |

All agents use **LangChain + Pydantic** for structured output and retries on failures.

### 2. Skills (Deterministic / External)

| Skill | Type | Purpose |
|-------|------|---------|
| **Validation** | Deterministic | Check tables, columns, required fields, constraints |
| **GitHub Push** | External (PyGithub) | Create repo, branch, push files; supports empty repos and missing repos |
| **Git (simulated)** | Deterministic | Simulated branch creation for demos |

### 3. Orchestrator

- Runs the pipeline in sequence
- Stops at approval when `review.approval_required` is true
- Stores pending state in memory (orchestrator + approval_store)
- Resumes via `POST /orchestrate/continue` after `POST /approval`

### 4. Approval Flow

- **In-memory store** (approval_store): Maps `approval_token` to pending state and decision
- **API**: `POST /approval` records approve/reject; `POST /orchestrate/continue` loads state and continues or halts
- For production, this should be backed by Redis or a database

---

## API Endpoints

### Orchestration

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/orchestrate` | POST | Run full pipeline; returns SUCCESS, FAILED, HALTED, or PENDING_APPROVAL |
| `/approval` | POST | Record human approve/reject decision |
| `/orchestrate/continue` | POST | Resume pipeline after approval |

### Git Operations

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/git/push` | POST | Push proposed structure to GitHub (create repo and branch if needed) |

### Individual Agents (for testing / watsonx Orchestrate)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/agents/requirements` | POST | Extract requirements only |
| `/agents/database-design` | POST | Design database only |
| `/agents/review` | POST | Review design only |
| `/agents/git-strategy` | POST | Propose Git strategy only |

### Skills

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/skills/validate` | POST | Validate database design |

---

## User Interfaces

### 1. Streamlit (Interactive Demo)

- Single-page UI for the full pipeline
- Sidebar: quick prompts, language, GitHub token/repo
- Tabs: Requirements, DB design, Review, Git
- Human approval: approve/reject with comments
- Push to GitHub: uses token and repo from sidebar

### 2. IBM watsonx Orchestrate

- Imported via OpenAPI (openapi_full.json or openapi_orchestrate.json + openapi_git.json)
- Agent behavior defined in WATSONX_ORCHESTRATE_BEHAVIOR.txt
- GitHub token: from credential vault or runtime prompt
- Repo name: from user’s message or runtime prompt

### 3. REST API (curl, Postman, etc.)

- Direct calls to endpoints for automation and integration

---

## Key Features

- **Structured output**: Pydantic models ensure consistent JSON
- **Retry logic**: LLM calls retried with backoff and slight temperature increase
- **Human-in-the-loop**: Optional approval before Git execution
- **Language-aware**: Python, Node.js, Java, Go mapped to appropriate frameworks
- **GitHub integration**:
  - Create repositories if they do not exist
  - Handle empty repos (no branches)
  - Push README, .gitignore, main entry, dependency file
- **watsonx Orchestrate**: OpenAPI specs and behavior instructions for skill import

---

## Deployment

- **Backend**: FastAPI app (Railway, IBM Code Engine, Docker, etc.)
- **Environment**: watsonx.ai credentials (API key, project ID, URL)
- **Streamlit**: Optional, can run locally or as a separate service
- **Documentation**: DEPLOYMENT.md, WATSONX_ORCHESTRATE.md, DEPLOYMENT_CHECKLIST.md

---

## Technology Choices

| Choice | Rationale |
|--------|-----------|
| **watsonx.ai** | Enterprise LLM platform, hackathon focus |
| **LangChain** | Structured output, watsonx integration |
| **Pydantic** | Schema validation, type safety |
| **FastAPI** | Modern async API, OpenAPI support |
| **Streamlit** | Fast prototyping and demos |
| **PyGithub** | GitHub API access for repo and file creation |

---

## Status and Extensions

**Current state**

- Full orchestration pipeline
- Human approval flow (API-driven)
- Real GitHub push (including repo creation and empty repos)
- Streamlit UI and watsonx Orchestrate integration

**Possible extensions**

- Persistent approval store (Redis/DB)
- Additional agents (tests, deployment, monitoring)
- More platforms (GitLab, Bitbucket)
- CI/CD integration
- Webhook notifications

---

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Configure .env with watsonx.ai credentials
WATSONX_API_KEY=...
WATSONX_PROJECT_ID=...
WATSONX_URL=https://us-south.ml.cloud.ibm.com

# Run API
uvicorn app.main:app --reload

# Run Streamlit UI
streamlit run streamlit_app.py
```

---

## Related Documentation

- **DEPLOYMENT.md** — Deployment and environment setup
- **WATSONX_ORCHESTRATE.md** — Integration with watsonx Orchestrate
- **WATSONX_ORCHESTRATE_BEHAVIOR.txt** — Agent behavior and guidelines
- **API_SUMMARY.md** — API quick reference
