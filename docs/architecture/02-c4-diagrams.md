# 2. C4 Architecture Diagrams

## Context

The following three diagrams show the AI Agent Platform architecture at different levels of detail, following the C4 model.

---

## Level 1: System Context

Shows how the AI Agent Platform interacts with external entities:

```mermaid
graph TB
    User["👤 User/Client"]
    Platform["🤖 AI Agent Platform<br/>(K8S Cluster)"]
    Gemini["🧠 Google Gemini API"]
    ExternalServices["🌐 External Services<br/>(APIs, Databases)"]
    
    User -->|HTTP/REST| Platform
    Platform -->|LLM Calls| Gemini
    Platform -->|API Calls| ExternalServices
```

**Key Interactions:**
- **User → Platform**: RESTful HTTP requests to start/resume agent workflows
- **Platform → Gemini**: LLM API calls for agent reasoning and decision-making
- **Platform → External Services**: Tool execution (search, database queries, third-party APIs)

---

## Level 2: Container Architecture

Detailed view of the main containerized components and their interactions:

```mermaid
graph TB
    subgraph Client["Client Layer"]
        User["👤 User/Client<br/>(Browser, Mobile, Webhook)"]
    end
    
    subgraph K8S["Kubernetes Cluster"]
        subgraph API["API Gateway Pod"]
            FastAPI["FastAPI Gateway<br/>- Request Routing<br/>- Authentication<br/>- Rate Limiting"]
        end
        
        subgraph Orchestration["LangGraph Orchestrator Pod(s)"]
            LG["LangGraph Runtime<br/>- Workflow Coordination<br/>- Node Execution<br/>- State Management"]
        end
        
        subgraph Workers["Agent Worker Pods<br/>(Auto-scaling)"]
            W1["Worker 1<br/>- Tool Execution<br/>- Thinking Loop"]
            W2["Worker 2<br/>- Tool Execution<br/>- Thinking Loop"]
            WN["Worker N<br/>- Tool Execution<br/>- Thinking Loop"]
        end
        
        subgraph Queuing["Async Task Queue"]
            RST["Redis Streams<br/>- Task Distribution<br/>- Async Dispatch<br/>- Consumer Groups"]
        end
        
        subgraph Persistence["Persistence Layer"]
            Redis["Redis Cache<br/>- Session State<br/>- Quick Recovery<br/>- Streams"]
            Postgres["PostgreSQL<br/>- Workflow History<br/>- Agent Memory<br/>- Long-term State"]
        end
        
        subgraph Config["Configuration"]
            ConfigMap["ConfigMaps<br/>- Agent Configs<br/>- Tool Definitions"]
            Secrets["Secrets<br/>- API Keys<br/>- Credentials"]
        end
        
        subgraph Observability["Observability"]
            LS["LangSmith<br/>- Trace Collection<br/>- Agent Debugging<br/>- Metrics"]
        end
    end
    
    subgraph External["External Services"]
        Gemini["🧠 Google Gemini API<br/>(LLM)"]
        Tools["🔧 Tool APIs<br/>(Searches, Databases)"]
    end
    
    User -->|HTTP POST| FastAPI
    FastAPI -->|forward| LG
    LG -->|enqueue task| RST
    RST -->|pick up task| W1
    RST -->|pick up task| W2
    RST -->|pick up task| WN
    
    LG -->|read/write state| Redis
    LG -->|persist workflow| Postgres
    LG -->|send traces| LS
    
    W1 -->|tool calls| Tools
    W1 -->|fetch config| ConfigMap
    W1 -->|ack result| RST
    
    LG -->|LLM prompts| Gemini
    
    Gemini -->|completions| LG
    Tools -->|results| W1
```

**Component Interactions:**
- **FastAPI → LangGraph**: Forwards requests, passes session context
- **LangGraph → Redis Streams**: Asynchronously dispatches tool tasks
- **Workers → Redis Streams**: Pick up tasks, acknowledge completion
- **LangGraph → Redis/PostgreSQL**: Checkpoints state for recovery
- **Workers → Tools**: Execute external tool/API calls
- **LangGraph → Gemini**: LLM prompts and completions
- **LangGraph → LangSmith**: Sends execution traces for observability

---

## Level 3: Component & Data Flow

Detailed component interactions and execution state flow:

```mermaid
graph LR
    subgraph Request["Request Handling"]
        A["Request Arrives<br/>at FastAPI Gateway"]
        B["Extract Session ID<br/>Create if new"]
        C["Fetch Agent State<br/>from Redis/Postgres"]
        D["Validate & Enrich<br/>Context"]
    end
    
    subgraph Execution["Agent Execution"]
        E["LangGraph Orchestrator<br/>Starts Workflow"]
        F["Current Node<br/>Evaluation"]
        G{"Decision:<br/>LLM Call?<br/>Tool?<br/>End?"}
    end
    
    subgraph Persistence["State Persistence"]
        H["Save Execution State<br/>to Redis temp storage"]
        I["Checkpoint Created<br/>- Step #<br/>- Node<br/>- Variables"]
    end
    
    subgraph Fallback["Fault Recovery"]
        J{"Pod<br/>Restarts?"}
        K["Recover from Redis<br/>or Postgres"]
        L["Resume from<br/>Last Checkpoint"]
    end
    
    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G -->|Tool Call| H
    G -->|LLM Prompt| H
    H --> I
    I --> F
    I -.->|async persist| Postgres
    
    J -->|Yes| K
    K --> L
    L --> F
```

**Data Flow Annotations:**

1. **Request Phase**: Incoming request extracted, session validated, prior state loaded
2. **Execution Phase**: LangGraph processes current node, decides next action
3. **Tool/LLM Phase**: Based on decision:
   - **Tool Call**: Enqueue to Redis Streams, wait for worker result
   - **LLM Call**: Send prompt to Gemini, receive completion
4. **State Phase**: After each decision, checkpoint the execution state
   - **Immediate**: Store in Redis (hot cache)
   - **Async**: Background job persists to PostgreSQL
5. **Recovery Phase**: If pod crashes, new pod can recover from checkpoint and resume

---

## Component Relationships

| From | To | Via | Type | Purpose |
|------|----|----|------|---------|
| Client | Gateway | HTTP | Sync | Request submission |
| Gateway | Orchestrator | In-memory | Sync | Pass context to workflow |
| Orchestrator | Redis Streams | XADD | Async | Dispatch tool tasks |
| Orchestrator | Gemini | gRPC | Sync | LLM prompts |
| Workers | Redis Streams | XREAD | Async | Consume tasks |
| Workers | Tools | HTTP/gRPC | Sync | Execute function |
| Orchestrator | Redis | SET/GET | Sync | Checkpoint state |
| Orchestrator | PostgreSQL | SQL | Async | Archive traces |
| Orchestrator | LangSmith | HTTP | Async | Send traces |

---

## Deployment Topology

```
Internet
    ↓ (DNS: api.agent-platform.com)
┌─────────────────────────────────────┐
│ Ingress (nginx/Istio)               │
└────────┬────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Service: api-gateway (LoadBalancer) │
└────────┬────────────────────────────┘
         ↓ (Round-robin traffic)
┌─────────────────────────────────────┐
│ Pods: ai-gateway (x3 replicas)      │
│ • CPU: 500m, Memory: 1Gi            │
│ • Liveness/Readiness probes: 10s    │
└────────┬────────────────────────────┘
         ↓ (gRPC or Service DNS)
┌─────────────────────────────────────┐
│ Service: orchestrator (ClusterIP)   │
└────────┬────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Pods: ai-orchestrator (x2 replicas) │
│ • CPU: 1000m, Memory: 2Gi           │
│ • Affinity rules for spread         │
└────────┬────────────────────────────┘
         ↓ (Redis Streams)
┌────────────────────────────────────────┐
│ Service: redis-cache & redis-streams   │
│ (Can be external or StatefulSet)       │
└────────────────────────────────────────┘
         ↓
┌──────────────────────────────────────┐
│ Service: agent-workers (Headless)    │
└────────┬───────────────────────────┘
         ↓ (Controlled by HPA)
┌──────────────────────────────────────┐
│ StatefulSet: ai-workers (x2-20)      │
│ • CPU: 500m, Memory: 1Gi per pod     │
│ • Triggered by queue depth/CPU usage │
└──────────────────────────────────────┘
```

---

## See Also

- [03-Components](03-components.md) - Detailed component responsibilities
- [04-Async Communication](04-async-communication.md) - Redis Streams deep dive
- [08-Deployment](08-deployment.md) - Kubernetes manifests
