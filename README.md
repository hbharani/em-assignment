# AI Agents Platform

A production-grade intelligent agent platform enabling seamless integration with infrastructure APIs, built on modern AI orchestration and cloud-native technologies.

---

## 🎯 Project Vision

The **AI Agents Platform** empowers teams to build, deploy, and manage autonomous AI agents that intelligently interact with infrastructure systems. Our vision is to create a flexible, scalable foundation where agents can:

- **Orchestrate complex workflows** across multiple systems with natural language understanding
- **Integrate seamlessly** with existing infrastructure and APIs
- **Operate reliably** in production environments with comprehensive observability
- **Scale dynamically** on Kubernetes while maintaining control and predictability

By combining cutting-edge language models with deterministic workflow engines, we're building the backbone for the next generation of intelligent infrastructure automation.

---

## 🤖 AI-Driven Management

This repository's backlog and feature prioritization is built and maintained by a custom LangGraph agent designed to optimize task planning and dependencies. You can find the agent scripts in the [scripts/](./scripts/) folder. This approach ensures our roadmap is continuously refined based on architectural dependencies and delivery priorities.

---

## 🛠 Core Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Runtime** | Python 3.11+ | Core agent logic and API server |
| **Web Framework** | FastAPI | High-performance async HTTP API |
| **Agent Orchestration** | LangGraph | Multi-step workflow execution and state management |
| **LLM Integration** | Google Gemini API | Natural language understanding and reasoning |
| **Observability** | LangSmith | Tracing, debugging, and performance monitoring |
| **Container Orchestration** | Kubernetes | Production deployment and scaling |

---

## 🚀 Quarterly Goal: Infrastructure Agent v1.0

This quarter, we are shipping **Infrastructure Agent v1.0**—a production-ready agent capable of:

✅ **Infrastructure Querying** – Retrieve system status, metrics, and configuration data  
✅ **Multi-Step Workflows** – Execute complex provisioning and remediation tasks  
✅ **API Integration** – Connect to existing infrastructure services and tools  
✅ **Observability & Debugging** – Full tracing and audit logs via LangSmith  
✅ **Robust Error Handling** – Graceful degradation and automatic recovery  
✅ **Production Deployment** – Kubernetes-ready with health checks and autoscaling  

---

## � Q2 Strategic Tradeoffs – Team Capacity Planning

With a team of 5 engineers and ~100 effective engineering weeks this quarter, we prioritize ruthlessly:

### ✅ THIS QUARTER (v1.0 MVP – Production Ready)
**Focused on reliability, observability, and core infrastructure automation**

| Feature | Effort | Why Now |
|---------|--------|---------|
| **Core Agent Execution Engine** | High | Foundation for everything; LangGraph + Gemini integration |
| **Single-Step & Multi-Step Workflows** | High | Core premise of the platform; agents must execute tasks |
| **Infrastructure Querying** | Medium | Read-only operations; lower risk, immediate value |
| **Basic API Integration** | Medium | Support ~5-10 critical infrastructure APIs |
| **State Persistence (Redis + PostgreSQL)** | High | Non-negotiable for production reliability |
| **Circuit Breaker Pattern** | Medium | Prevents cascading failures; operational essential |
| **LangSmith Observability** | Medium | Required for debugging agent behavior in prod |
| **Kubernetes Deployment** | High | Target deployment environment; must be battle-tested |
| **Comprehensive Testing** | High | Production requires >80% coverage + integration tests |
| **Operational Documentation** | Medium | Runbook for SREs + deployment guide |

**Estimated allocation:** ~90 engineering weeks

---

### ⏸️ NEXT QUARTER (v1.1 – Enterprise Grade)
**Deferred to focus on throughput and polish this quarter**

| Feature | Why Deferred | Q3 Effort |
|---------|--------------|-----------|
| **Multi-Agent Orchestration** | Requires stable v1.0 foundation first | High |
| **Advanced Workflow Patterns** | Scope creep; defer edge cases | High |
| **Commercial API Integrations** | Nice-to-have; focus on core infra APIs | Medium |
| **UI/Dashboard** | Can use CLI/logs for v1.0; UI can follow | High |
| **Advanced Security (RBAC, Encryption)** | v1.0 assumes trusted environment | Medium |
| **Custom LLM Model Fine-tuning** | Requires production baselines first | High |
| **Performance Optimization (sub-s latency)** | Defer until we measure real workloads | Medium |
| **Disaster Recovery Playbooks** | Can document after v1.0 runs | Low |

**Estimated allocation (Q3):** These features will define v1.1

---

### 🎯 Success Criteria for v1.0
We declare success when:
1. ✅ Agents reliably execute 95%+ of tasks without human intervention
2. ✅ All workflow state survives pod crashes (Redis + PostgreSQL dual-layer persistence)
3. ✅ Operations team can deploy, scale, and monitor using K8s manifests
4. ✅ LangSmith dashboards show full request tracing from user → LLM → tool
5. ✅ Documentation covers deployment, troubleshooting, and extending agents

---

## 👨‍💻 Developer Experience

We believe great developer experience is a competitive advantage. Here's how we make the team's life exceptional:

### 🤖 Automated Ticket Creation & Dependency Mapping
The **LangGraph Backlog Manager Agent** eliminates manual issue creation and dependency management. Instead of tedious GitHub issue templating and manual link tracking, the agent:
- **Generates well-structured tickets** with clear context, acceptance criteria, and technical requirements
- **Automatically maps dependencies** using GitHub's `tracked by` and `blocks` relationships
- **Prioritizes intelligently** based on architectural impact and delivery sequencing
- **Stays in sync** as architecture evolves—no stale dependency graphs

Engineers focus on building; the agent handles the busywork.

### 🔍 Time-Travel Debugging with LangSmith & State Checkpoints
When an agent fails, we don't guess—we *see*:
- **Full execution tracing** in LangSmith shows every LLM call, tool invocation, and state mutation
- **State checkpoints** capture workflow state at each step, enabling you to:
  - Rewind to any point in execution
  - Inspect variable values mid-workflow
  - Replay from a checkpoint without starting over
  - Validate conditional logic with complete context

This transforms debugging from "blindly adding print statements" to "surgical precision inspection."

### ⚡ Circuit Breaker Pattern = No On-Call Fatigue
**Failing fast prevents cascading disasters:**
- When an infrastructure API is slow or broken, the circuit breaker **fails immediately** instead of hanging
- Agents gracefully degrade and report errors in seconds, not minutes
- No alert storms from cascading timeouts
- On-call engineers get actionable, scoped errors—not mystery hangs

The pattern is baked into our tool execution layer, protecting both agents and the infrastructure they manage.

### 🚀 Redis Streams: Parallel Without Blocking
Engineers build **independently**:
- **Workers and orchestrators decouple completely** via Redis Streams—no shared locks, no race conditions
- Multiple teams can own workflow stages without coordination overhead
- Backpressure is natural; stream consumers auto-scale based on queue depth
- No "I'm blocked waiting for the storage team" moments

Build your workflow components in parallel; they integrate through decoupled events.

---

### 💡 Key Tradeoff Decisions

**Decision 1: Single-Tenant First**  
- **Choice:** v1.0 ships as single cluster, single tenant
- **Reason:** Multi-tenancy adds ~15% engineering overhead this quarter; defer to v1.1
- **Impact:** Simplifies secrets management, observability, and compliance for Q2

**Decision 2: CLI + Logs > UI**  
- **Choice:** No web dashboard in v1.0; engineers use CLI + LangSmith UI
- **Reason:** UI adds 1-2 weeks; CLI is sufficient for launch; UI is v1.1 Phase 2
- **Impact:** Faster time-to-market; dashboard can roll out independently

**Decision 3: Infrastructure APIs (not Business Logic)**  
- **Choice:** Focus on infra (compute, storage, networking); defer HR/billing APIs
- **Reason:** Infrastructure is higher ROI; business logic APIs are nice-to-have
- **Impact:** v1.0 is laser-focused on DevOps use cases

**Decision 4: Synchronous Workflows Only**  
- **Choice:** No deeply nested async branching; linear + simple branching only
- **Reason:** Complex workflows require more robust state tracking; save for v1.1
- **Impact:** Most real-world infra tasks are linear anyway; covers 80% of use cases

---

## �📚 Navigation Guide

### Architecture & Design
- **[01 System Overview](./docs/architecture/01-overview.md)** – Core principles, system design, and key components

### Planning & Backlog
- **[02 C4 Diagrams](./docs/architecture/02-c4-diagrams.md)** – Level 1-3 architecture diagrams
- **[03 Components](./docs/architecture/03-components.md)** – Component descriptions
- **[04 Async Communication](./docs/architecture/04-async-communication.md)** – Redis Streams patterns
- **[05 State Persistence](./docs/architecture/05-state-persistence.md)** – Two-tier persistence
- **[06 Idempotency](./docs/architecture/06-idempotency.md)** – Request deduplication
- **[07 Circuit Breaker](./docs/architecture/07-circuit-breaker.md)** – Tool resilience patterns
- **[08 Deployment](./docs/architecture/08-deployment.md)** – Kubernetes deployment

### AI Automation & Tooling
- **[Backlog Manager Agent](./scripts/README.md)** – LangGraph agent for GitHub issue generation
- **[AI Interaction Logs](./docs/ai-interaction-logs/)** – AI-assisted development conversations

---

## � Planning & Dependency Management

We use GitHub's **tracked by** and **blocks** relationship features to manage critical path dependencies:

- **Tracked by**: Issues that are blocked by other work
- **Blocks**: Issues that must be completed before dependent work can proceed

This creates a transparent dependency graph visible in GitHub Issues, ensuring:
- ✅ Clear visibility into critical path items
- ✅ Automatic blocking of dependent tasks
- ✅ Data-driven prioritization informed by AI analysis

See [GitHub Issues](../../issues) for dependency mapping and current blockers.

---

## �📁 Repository Structure

```
em-assignment/
├── README.md                           # This file (project overview & strategic planning)
├── docs/
│   ├── architecture/                   # System design documentation
│   │   ├── 01-overview.md              # System overview and design goals
│   │   ├── 02-c4-diagrams.md           # Level 1-3 architecture diagrams
│   │   ├── 03-components.md            # Detailed component descriptions
│   │   ├── 04-async-communication.md   # Redis Streams patterns
│   │   ├── 05-state-persistence.md     # Two-tier persistence design
│   │   ├── 06-idempotency.md           # Request deduplication
│   │   ├── 07-circuit-breaker.md       # Tool resilience patterns
│   │   ├── 08-deployment.md            # Kubernetes deployment guide
│   │   └── README.md                   # Architecture docs index
│   └── ai-interaction-logs/            # AI-assisted development conversations
│       ├── 2026-04-15-backlog-manager-agent.md
│       ├── 2026-04-15-backlog-manager-fixes.md
│       ├── 2026-04-15-backlog-manager-refinement.md
│       ├── 2026-04-15-backlog-modularization.md
│       ├── 2026-04-15-readme-creation.md
│       ├── 2026-04-15-system-design-architecture.md
│       └── 2026-04-15-strategic-tradeoffs.md
├── scripts/
│   ├── backlog_manager.py               # LangGraph agent for backlog management
│   ├── requirements-backlog-manager.txt # Agent dependencies
│   ├── README.md                        # Backlog manager documentation
│   └── backlog/                         # Agent modules
│       ├── __init__.py
│       ├── state.py
│       ├── workflow.py
│       ├── llm_nodes.py
│       ├── document_loader.py
│       ├── issue_helpers.py
│       └── github_operations.py
└── .gitignore                           # Git ignore rules
```

---

## 🤝 Contributing

This is a released version. For future contributions, follow these guidelines:

1. **Create a GitHub issue** to discuss your proposal
2. **Create a feature branch** from `main`
3. **Update architecture documentation** if design changes
4. **Submit a pull request** with clear description and reasoning
5. **Code review** required before merge to `main`

All changes should align with the [Strategic Tradeoffs](#-q2-strategic-tradeoffs--team-capacity-planning) principles and architectural patterns in [docs/architecture/](./docs/architecture/).

---

## 📋 Current Status

**Phase:** Q2 2026 – Infrastructure Agent v1.0  
**Status:** ✅ Complete & Ready for Production  
**Release Date:** April 15, 2026

All core components documented and architected. Ready for implementation phase (Q2/Q3 2026).

**Deliverables:**
- ✅ Complete system architecture with C4 diagrams
- ✅ Strategic capacity planning and feature prioritization
- ✅ Detailed deployment and operations guide
- ✅ AI-assisted design documentation with complete conversation logs
- ✅ Automated backlog management agent (LangGraph + Gemini)

---

## 📞 Support & Questions

- **Documentation:** See the [docs/](./docs/) directory
- **Issues:** Open a [GitHub Issue](../../issues) for bugs or feature requests
- **Slack:** Connect with the team in `#ai-agents-platform`

---

## 📄 License

This project is licensed under the **MIT License** – see the [LICENSE](./LICENSE) file for details.

Permissions: commercial use, distribution, modification, and private use.  
Conditions: include license and copyright notices.  
Limitations: no liability or warranty.

---

**Built with ❤️ by the AI Agents Engineering Team**
