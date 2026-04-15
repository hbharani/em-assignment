# 3. Architecture Components

Detailed descriptions of each component, their responsibilities, and design rationale.

---

## 1. FastAPI Gateway

**Role:** Entry point for all client requests

**Responsibilities:**
- HTTP request handling and routing
- Session management and extraction
- Authentication and authorization
- Rate limiting and request validation
- Response formatting and serialization
- Idempotency key validation (`X-Idempotency-Key` header)
- Request tracing headers propagation

**Deployment:** 
- 3 replicas (load-balanced) for high availability
- Exposed via Ingress + LoadBalancer Service

**Key Features:**
- WebSocket support for streaming responses
- Graceful shutdown handling (drain requests in-flight)
- Health check endpoints for K8S liveness/readiness probes
- Circuit breaker aware (handles 429 Too Many Requests from orchestrator)
- Metrics exposed to Prometheus

**Example Request Handling:**
```python
@app.post("/agent/run")
async def run_agent(request: AgentRequest):
    # 1. Extract or generate session_id
    session_id = request.session_id or uuid4()
    
    # 2. Check idempotency
    request_id = request.headers.get("X-Idempotency-Key") or uuid4()
    cached = await redis.get(f"request:{session_id}:{request_id}:result")
    if cached:
        return json.loads(cached)
    
    # 3. Fetch prior state
    state = await redis.get(f"session:{session_id}:state")
    
    # 4. Forward to orchestrator
    result = await orchestrator.execute(session_id, request.payload, priors state)
    
    # 5. Cache result
    await redis.set(f"request:{session_id}:{request_id}:result", result, ex=3600)
    
    return result
```

---

## 2. LangGraph Orchestrator

**Role:** Workflow coordination engine

**Responsibilities:**
- Parse and validate agent workflow definitions
- Execute nodes sequentially or conditionally (if/else branching)
- Manage LLM communication (Gemini API calls)
- Enqueue tool execution tasks to Redis Streams
- Handle loops and retry logic
- Checkpoint execution state after each decision point
- Emit execution traces to LangSmith for observability
- Handle timeouts and graceful degradation

**State Management:**
- **In-memory**: Active workflows being processed
- **Redis**: Hot cache for fast recovery (<50ms)
- **PostgreSQL**: Archive for audit, compliance, replay

**Async Communication Pattern:**
- Publishes tasks to Redis Streams channels (e.g., `tasks:search`, `tasks:database`)
- Awaits worker completion via Redis Streams results channel
- **Non-blocking**: Multiple orchestrator instances can process workflows concurrently
- Subscription pattern: `XREAD BLOCK 30000 STREAMS tasks:* 0` (30s timeout)

**Example Node Execution:**
```python
async def execute_node(orchestrator, node_name, node_config, state):
    if node_config.type == "llm":
        # LLM Call
        response = await gemini.generate(node_config.prompt, state)
        state.messages.append(response)
    
    elif node_config.type == "tool":
        # Enqueue to Redis Streams
        task_id = f"task_{state.session_id}_{state.step}"
        await redis.xadd(
            f"tasks:{node_config.tool_type}",
            {
                "task_id": task_id,
                "session_id": state.session_id,
                "tool": node_config.tool,
                "params": json.dumps(node_config.params)
            }
        )
        
        # Wait for result
        result = await wait_for_result(
            task_id, 
            timeout=node_config.timeout or 30
        )
        state.tool_results.append(result)
    
    # Checkpoint after node
    checkpoint = {
        "session_id": state.session_id,
        "step": state.step,
        "state": state.to_dict(),
        "timestamp": time.time()
    }
    await redis.set(f"session:{session_id}:checkpoint:{step}", checkpoint, ex=86400)
    await send_async(postgres.insert_checkpoint, checkpoint)
    
    # Send trace to LangSmith
    await langsmith.log_run(
        trace_id=f"session_{session_id}_step_{step}",
        node=node_name,
        inputs={"state": state},
        outputs={"next_node": determine_next_node(state)}
    )
```

**Deployment:**
- 2 replicas (stateless, can scale horizontally)
- Service DNS: `ai-orchestrator:8001`
- Resource limits: 1000m CPU, 2Gi memory

---

## 3. Agent Worker Pods

**Role:** Execute tools, API calls, and compute-intensive tasks

**Responsibilities:**
- Listen to Redis Streams for incoming task messages via consumer group
- Deserialize and validate task payloads
- Check circuit breaker status for the tool before execution
- Run actual tool/function implementations
- Fetch and execute tool definitions from ConfigMaps
- Return structured results via Redis Streams result channel
- Acknowledge task completion in consumer group (prevents re-delivery)
- Handle timeouts, retries, and send heartbeats
- Report execution metrics to Prometheus
- Handle circuit breaker failures gracefully (cache, skip, synthesize)

**Consumer Groups:**
- Name: `workers:tools` (tracks which messages workers have consumed)
- Each worker is a consumer in the group
- Exactly-once delivery semantics via acknowledgment (XACK)
- Automatic retry on worker crash: pending entries re-released after timeout

**Auto-scaling:**
- Horizontal Pod Autoscaler (HPA) based on:
  - Redis Streams pending entries (high pending = more workers needed)
  - CPU/Memory utilization
  - Custom metrics (task latency)

**Isolation & Resilience:**
- Each worker is independent; pod failures don't cascade
- Async pattern: Not blocked waiting for orchestrator
- Circuit breaker per tool: Fail fast on broken tools
- Graceful shutdown: Finish current task, acknowledge completion, exit

**Example Worker Loop:**
```python
async def worker_loop():
    while True:
        try:
            # Read from stream with consumer group
            messages = await redis.xreadgroup(
                groupname="workers:tools",
                consumername=f"worker_{pod_name}_{container_id}",
                streams={
                    "tasks:search": ">",
                    "tasks:database": ">",
                    "tasks:external_api": ">"
                },
                count=1,
                block=1000  # 1 second timeout
            )
            
            for stream, task_messages in messages:
                for task_id, task in task_messages:
                    await process_task(stream, task_id, task)
                    
                    # Acknowledge completion
                    await redis.xack(stream, "workers:tools", task_id)
        
        except asyncio.CancelledError:
            # Graceful shutdown
            log("Worker shutting down gracefully")
            break
        except Exception as e:
            log(f"Worker error: {e}")
            await asyncio.sleep(5)  # Backoff before retry

async def process_task(stream, task_id, task):
    tool_name = task.get("tool")
    params = json.loads(task.get("params"))
    timeout = int(task.get("timeout", 30))
    
    # Check circuit breaker
    circuit_breaker = circuit_breakers[tool_name]
    result = await circuit_breaker.call(
        execute_tool,
        tool_name,
        params,
        timeout=timeout
    )
    
    # If circuit breaker is open, result will be error
    # Otherwise, tool was executed
    
    # Send result back via Redis Streams
    session_id = task.get("session_id")
    await redis.xadd(
        f"results:{session_id}",
        {
            "task_id": task_id,
            "result": json.dumps(result),
            "timestamp": time.time()
        }
    )
    
    # Report metrics
    prometheus.histogram("worker_task_duration_seconds", duration).observe(duration)
    prometheus.counter("worker_tasks_completed_total", tool=tool_name).inc()
```

**Deployment:**
- StatefulSet: Maintains persistent state per worker
- Replicas: 2-20 (controlled by HPA)
- Resource limit: 500m CPU, 1Gi memory per pod
- Graceful termination period: 30s

---

## 4. Redis Cache & Streams

**Role:** High-speed temporary state storage and async task distribution

**Responsibilities:**
- Store active session state and execution checkpoints (String/Hash data structures)
- Enable rapid state recovery (sub-millisecond latency)
- Support multi-step workflow continuity across pod restarts
- Distribute tasks asynchronously (Redis Streams)
- Accumulate task results and heartbeats
- Serve as communication backbone between orchestrator and workers

**Two Data Structures:**

**Strings/Hashes (Caching):**
- `session:{session_id}:state` - Current agent state
- `session:{session_id}:checkpoint:{step}` - Checkpoint at each step
- `request:{session_id}:{request_id}:result` - Request result for deduplication
- `request:{session_id}:{request_id}:processing` - In-flight request marker
- `task_result:{task_id}` - Cached tool execution result
- `circuit_breaker:{tool_name}:metrics` - Circuit breaker state & failure count

**Streams (Messaging):**
- `tasks:search` - Tool execution task queue for search tools
- `tasks:database` - Task queue for database operations
- `tasks:external_api` - Task queue for external API calls
- `results:{session_id}` - Results channel per session
- TTL: Messages kept for last N entries or time-window

**Consumer Groups:**
- `workers:tools` - All worker consumers grouped together
- Pending entries: Tasks consumed but not acknowledged
- Entry-ID tracking: Which message each consumer read up to

**Configuration:**
- TTL on keys: 24-86400s (prevents stale data accumulation)
- Persistence: RDB snapshots (recovery on restart)
- Memory management: LRU eviction policy
- Stream retention: Keep last 10,000 messages or 1 hour
- Replication: Single instance or Redis Sentinel for HA

**Performance Characteristics:**
- SET/GET: O(1), <1ms latency
- XADD: O(1), append-only
- XREAD with consumer group: O(N), N= num messages to read
- Memory usage: ~100 bytes per session checkpoint

---

## 5. LangSmith (Observability)

**Role:** Observability and debugging platform for LLM agents

**Responsibilities:**
- Collect and visualize execution traces from LangGraph nodes
- Track token usage and API costs per agent run
- Debug agent behavior and decision-making
- Identify bottlenecks and performance issues
- Store historical logs for analysis and replay
- Provide web UI for trace inspection

**Integration Points:**
- **LangGraph Orchestrator**: Emits traces on every node execution
  - Node name, inputs, outputs, timing
  - LLM prompts and completions
  - Tool execution times and results
- **Workers**: Tool execution times and results captured
- **Metrics**: Token counts, latency histograms

**Trace Structure:**
```json
{
  "trace_id": "session_sess_abc_step_5",
  "run_id": "run_12345",
  "name": "tool_executor_node",
  "start_time": "2026-04-15T10:30:45Z",
  "end_time": "2026-04-15T10:30:50Z",
  "status": "success",
  "inputs": {
    "tool": "search",
    "params": {"query": "..."}
  },
  "outputs": {
    "results": [...]
  },
  "metadata": {
    "session_id": "sess_abc123",
    "step": 5,
    "llm_calls": 0,
    "tokens_used": 0
  }
}
```

**Deployment:**
- Cloud-hosted: `https://smith.langchain.com`
- API Key: Stored in K8S Secret
- Network: Orchestrator sends traces asynchronously (non-blocking)

---

## 6. PostgreSQL Database

**Role:** Durable long-term storage

**Responsibilities:**
- Durably store workflow history and completed traces
- Persist agent memory and learned patterns
- Archive checkpoints for audit and replay capability
- Store user sessions and configuration state
- Support compliance and regulatory requirements

**Schema:**

**checkpoints** table:
```sql
CREATE TABLE checkpoints (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    step INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    state JSONB NOT NULL,
    node_name TEXT,
    tool_executed TEXT,
    tool_result JSONB,
    UNIQUE(session_id, step),
    INDEX idx_session_id (session_id),
    INDEX idx_timestamp (timestamp)
);
```

**execution_traces** table:
```sql
CREATE TABLE execution_traces (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    trace_id TEXT UNIQUE,
    node_name TEXT,
    step INTEGER,
    inputs JSONB,
    outputs JSONB,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_ms FLOAT,
    status TEXT,
    error_message TEXT,
    INDEX idx_session_id (session_id),
    INDEX idx_timestamp (start_time)
);
```

**agent_memory** table:
```sql
CREATE TABLE agent_memory (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    memory_key TEXT,
    memory_value JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_session_id (session_id),
    INDEX idx_memory_key (memory_key)
);
```

**sessions** table:
```sql
CREATE TABLE sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    user_id TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity TIMESTAMP DEFAULT NOW(),
    workflow_type TEXT,
    status TEXT,
    metadata JSONB,
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id)
);
```

**Configuration:**
- Replication: Primary + standby for HA
- Backups: Daily snapshots to S3
- Retention: Checkpoints kept for 30 days; traces archived after 1 year
- Performance: Connection pooling (PgBouncer) for orchestrator/workers
- Indexing: Composite indexes on high-cardinality lookups (session_id, timestamp)

**Deployment:**
- Managed service: AWS RDS, Google Cloud SQL, or self-hosted
- Connection string in K8S Secret
- Network: Private VPC, not exposed to internet

---

## See Also

- [02-C4 Diagrams](02-c4-diagrams.md) - Visual architecture
- [04-Async Communication](04-async-communication.md) - Redis Streams detail
- [05-State Persistence](05-state-persistence.md) - Checkpoint and recovery
