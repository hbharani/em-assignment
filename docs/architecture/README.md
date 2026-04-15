# AI Agent Platform - System Design Documentation

This directory contains modular documentation for the AI Agent Platform architecture built on Kubernetes with LangGraph orchestration and Google Gemini as the LLM backbone.

## Quick Navigation

### 🏗️ Architecture Foundation
- **[01-Overview](01-overview.md)** - System overview and design goals
- **[02-C4 Diagrams](02-c4-diagrams.md)** - Level 1-3 architecture diagrams
- **[03-Components](03-components.md)** - Detailed component descriptions (Gateway, Orchestrator, Workers, Redis, LangSmith, PostgreSQL)

### 🔄 Patterns & Designs
- **[04-Async Communication](04-async-communication.md)** - Redis Streams orchestrator-to-worker communication
- **[05-State Persistence](05-state-persistence.md)** - Stateful agent pattern with two-tier persistence (Redis + PostgreSQL)
- **[06-Idempotency](06-idempotency.md)** - Request deduplication and duplicate handling
- **[07-Circuit Breaker](07-circuit-breaker.md)** - Tool resilience and failure handling

### 🚀 Deployment & Operations
- **[08-Deployment](08-deployment.md)** - Kubernetes manifests, deployment checklist, and operational guide

---

## System at a Glance

```
User
  ↓ HTTP/REST
┌─────────────────────────────────────────────────────────┐
│          Kubernetes Cluster                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  FastAPI Gateway → LangGraph Orchestrator        │  │
│  │         ↓ (async via Redis Streams)              │  │
│  │  Agent Workers (auto-scaling)                    │  │
│  │         ↓ (tools, APIs)                          │  │
│  │  External Services                               │  │
│  │                                                   │  │
│  │  Persistence: Redis Cache + PostgreSQL           │  │
│  │  Observability: LangSmith                        │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
      ↓ LLM Calls
  Google Gemini API
```

---

## Key Features

✅ **Stateful Agents** - Multi-step workflows survive pod restarts  
✅ **Async Communication** - Non-blocking task distribution via Redis Streams  
✅ **Fault Tolerance** - Circuit breakers prevent cascading failures  
✅ **Idempotency** - Duplicate requests handled gracefully  
✅ **Observability** - LangSmith traces + LangGraph debugging  
✅ **Scalability** - Horizontal auto-scaling of workers  
✅ **Durability** - Two-tier persistence for fast recovery + long-term audit  

---

## Reading Path

**For Architects:**
1. Start with [01-Overview](01-overview.md)
2. Study [02-C4 Diagrams](02-c4-diagrams.md)
3. Deep dive into patterns: [05-State Persistence](05-state-persistence.md), [07-Circuit Breaker](07-circuit-breaker.md)

**For Engineers:**
1. Read [03-Components](03-components.md) to understand responsibilities
2. Learn [04-Async Communication](04-async-communication.md) for integration points
3. Follow [08-Deployment](08-deployment.md) for K8S setup

**For DevOps/SREs:**
1. Review [08-Deployment](08-deployment.md) manifests
2. Understand [07-Circuit Breaker](07-circuit-breaker.md) monitoring requirements
3. Check [05-State Persistence](05-state-persistence.md) for backup strategy

---

## Architecture Principles

1. **Resilience First**: Multi-tier persistence + circuit breakers
2. **Async by Default**: Non-blocking task distribution
3. **Stateful Workflows**: Survive restarts without user intervention
4. **Fail-Fast**: Circuit breakers prevent resource waste
5. **Observable**: LangSmith + LangGraph for debugging

---

## Document Status

Last Updated: April 15, 2026  
Version: 1.0  
Status: Production-Ready
