# 1. System Overview

## About This Document

This document describes the architecture of a scalable, resilient AI Agent Platform built on Kubernetes, leveraging LangGraph for orchestration and Google Gemini as the LLM backbone. The system is designed to handle complex, multi-step agent workflows with state persistence and fault tolerance.

## Core Principles

1. **Stateful Workflows** - Agent state survives pod restarts without user intervention
2. **Async by Default** - Non-blocking task distribution via Redis Streams
3. **Resilience First** - Multi-tier persistence + circuit breakers prevent cascading failures
4. **Fail-Fast** - Circuit breakers detect broken tools early, preventing resource waste
5. **Observable** - LangSmith traces + LangGraph debugging for complete visibility

## System Architecture at a Glance

```
┌────────────────────────────────────────────────────────────┐
│              Kubernetes Cluster                             │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastAPI Gateway (x3 replicas, load-balanced)       │  │
│  │  ↓ Session validation, request routing              │  │
│  │  LangGraph Orchestrator (x2 replicas)               │  │
│  │  ↓ Async task dispatch via Redis Streams            │  │
│  │  Agent Worker Pods (x2-20 auto-scaling)             │  │
│  │  ↓ Tool execution with circuit breakers             │  │
│  │                                                        │  │
│  │  Persistence:                                         │  │
│  │  • Redis: Hot cache for fast recovery (<50ms)       │  │
│  │  • PostgreSQL: Durable audit trail (1-5s async)     │  │
│  │                                                        │  │
│  │  Observability:                                       │  │
│  │  • LangSmith: Trace collection & debugging          │  │
│  │  • Prometheus: Metrics & circuit breaker health     │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
         ↓                                      ↓
    Google Gemini API             External Tool APIs
```

## Key Components

### Request Flow

```
User Request
    ↓
FastAPI Gateway
  (1. Extract session_id)
  (2. Check idempotency key)
  (3. Fetch state from Redis)
    ↓
LangGraph Orchestrator
  (1. Resume or start workflow)
  (2. Execute current node)
  (3. Enqueue tool tasks to Redis Streams)
  (4. Wait for results)
  (5. Checkpoint state)
    ↓
Agent Workers
  (1. Consume from Redis Streams)
  (2. Check circuit breaker for tool)
  (3. Execute tool with fallback strategy)
  (4. Return result via Redis Streams)
    ↓
Response to User (+ session_id for resume)
```

## Reliability Guarantees

| Scenario | Handling |
|----------|----------|
| **Pod crashes during workflow** | Automatic recovery from Redis checkpoint; user sees no interruption |
| **Tool API fails intermittently** | Circuit breaker opens; orchestrator uses cached result or fallback |
| **Duplicate request arrives** | Request deduplication via `(session_id, request_id)` pair; cached result returned |
| **Redis cache clears** | Fallback to PostgreSQL; re-execute from last checkpoint |
| **Worker times out** | Redis Streams consumer group re-releases task; another worker picks it up |
| **Network partition** | Orchestrator waits for results with timeout; graceful failure and retry |

## Design Decisions

### Why Redis Streams (not HTTP)?
- **Non-blocking**: Orchestrators don't wait for workers
- **Fast**: In-memory, zero network latency
- **Reliable**: Exactly-once delivery via consumer groups
- **Natural backpressure**: Stream saturation prevents cascade

### Why Two-Tier Persistence?
- **Redis (Hot)**: Sub-millisecond recovery for active workflows
- **PostgreSQL (Durable)**: Audit trail, compliance, long-term recovery

### Why Per-Tool Circuit Breakers?
- **Fail-fast**: Prevent wasting resources on broken tools
- **Fallback options**: Orchestrator can synthesize, cache, or skip
- **Monitoring**: Prometheus metrics for SRE visibility

### Why Idempotency IDs?
- **Safety**: Duplicate requests don't cause double-execution
- **User experience**: Automatic retries are transparent
- **Cost**: Avoid wasting LLM tokens on re-runs

---

## Next Steps

- Read [02-C4 Diagrams](02-c4-diagrams.md) for architecture visualization
- Review [03-Components](03-components.md) for detailed responsibilities
- Dive into patterns: [04-Async Communication](04-async-communication.md), [05-State Persistence](05-state-persistence.md), [07-Circuit Breaker](07-circuit-breaker.md)
- See [08-Deployment](08-deployment.md) for Kubernetes setup
