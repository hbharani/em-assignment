# 4. Async Communication: Redis Streams

## Overview

Instead of synchronous HTTP calls between orchestrator and workers, the system uses **Redis Streams** for async task distribution. This provides non-blocking communication, natural backpressure, and exactly-once delivery semantics.

---

## Why Redis Streams?

| Aspect | Benefits |
|--------|----------|
| **Non-blocking** | Orchestrators don't wait for workers; continue processing other workflows |
| **Fast** | In-memory, zero network latency between K8S pods |
| **Reliable** | Exactly-once delivery via consumer groups and acknowledgment |
| **Backpressure** | Stream saturation naturally slows task production |
| **Persistence** | Optional RDB snapshots for recovery |
| **Scaling** | Multiple workers consume from same stream independently |

### Comparison: HTTP vs. Redis Streams

```
┌──────────────────────────────────────────────────────────────┐
│ Synchronous HTTP (Before)                                    │
├──────────────────────────────────────────────────────────────┤
│ Orchestrator calls: GET http://worker:9000/execute?tool=foo  │
│ Orchestrator WAITS (blocks) for response                     │
│ If worker slow/down: Orchestrator times out after 30s        │
│ Resource: Blocked connection, thread/coroutine held          │
│ Throughput: Low (limited by worker response time)            │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Async Redis Streams (After)                                  │
├──────────────────────────────────────────────────────────────┤
│ Orchestrator: redis.xadd(\"tasks:search\", {...})            │
│ Orchestrator continues immediately (non-blocking)            │
│ Orchestrator polls result stream or waits for notification    │
│ If worker slow: Result sits in stream; no timeout            │
│ Resource: Minimal (fire-and-forget)                          │
│ Throughput: High (decoupled from worker speed)               │
└──────────────────────────────────────────────────────────────┘
```

---

## Message Flow: Orchestrator → Workers

```
┌──────────────────────────┐
│  LangGraph Node          │
│  Needs: tool:search      │
└───────────┬──────────────┘
            │
            ▼
┌──────────────────────────────────────┐
│ Create Task Message:                 │
│ {                                    │
│   task_id: "task_sess_abc_step_5",   │
│   session_id: "sess_abc123",         │
│   tool: "search",                    │
│   params: "{\"query\": \"...\"}"     │
│   timeout: 30                        │
│ }                                    │
└───────────┬──────────────────────────┘
            │
            ▼
    ┌───────────────────────────┐
    │ XADD to Stream            │
    │ Key: tasks:search         │
    │ Result: MessageID         │
    │ Latency: O(1), <1ms       │◄── Non-blocking insert
    └───────────┬───────────────┘
                │
    ┌───────────┴────────────────────────┐
    │ (Orchestrator continues processing  │
    │  other workflows immediately)      │
    └────────────────────────────────────┘
                │
    ┌───────────▼─────────────────────────────┐
    │ Consumer Group Poll:                    │
    │ XREADGROUP group=workers:tools ...     │
    │ BLOCK 1000ms (1 second timeout)        │
    └───────────┬─────────────────────────────┘
                │ (Worker picks up task)
    ┌───────────▼─────────────────────┐
    │ Worker Receives Message         │
    │ Deserialize task data           │
    │ Check circuit breaker           │
    └───────────┬─────────────────────┘
                │
    ┌───────────▼─────────────────────┐
    │ Execute Tool                    │
    │ search(query=\"...\")            │
    │ Latency: 50-5000ms              │
    └───────────┬─────────────────────┘
                │
    ┌───────────▼──────────────────────┐
    │ Format Result:                   │
    │ {                                │
    │   task_id: ...,                  │
    │   status: \"success\",            │
    │   result: {...}                  │
    │ }                                │
    └───────────┬──────────────────────┘
                │
    ┌───────────▼────────────────────────────┐
    │ XADD Result to Results Stream          │
    │ Key: results:sess_abc123               │
    │ Latency: O(1), <1ms                    │
    └───────────┬────────────────────────────┘
                │
    ┌───────────▼────────────────────────────┐
    │ XACK Consumer Group                    │
    │ Confirms task processed                │
    │ Pending entry removed                  │
    └───────────┬────────────────────────────┘
                │
    ┌───────────▼──────────────────────────────────┐
    │ Orchestrator Polls Result Stream             │
    │ XREAD STREAMS results:sess_abc123 $         │
    │ (or: Notification via Pub/Sub)               │
    │ Retrieves result and continues               │
    └──────────────────────────────────────────────┘
```

---

## Redis Streams Data Structures

### Stream Entry Format

```
Stream: tasks:search
─────────────────────────────────────────

Message ID              Entry Data
───────────────         ─────────────────────────────────────
1713177045000-0    →    {
                          "task_id": "task_sess_abc_step_5",
                          "session_id": "sess_abc123",
                          "tool": "search",
                          "params": "{json}",
                          "timeout": "30"
                        }

1713177045100-0    →    {
                          "task_id": "task_sess_def_step_2",
                          "session_id": "sess_def456",
                          ...
                        }
```

### Consumer Group Tracking

```
Consumer Group: workers:tools
──────────────────────────────────────

Consumer            Last Entry ID    Pending Entries
─────────────       ──────────────   ────────────────
worker-pod-1        1713177045100-0  (none)
worker-pod-2        1713177045050-0  [1713177045075-0]
worker-pod-3        1713177045000-0  [1713177045020-0]

(Consumer-2 has 1 pending entry that crashed; will be re-assigned)
```

---

## Consumer Group & Exactly-Once Semantics

### Setup

```python
# Create consumer group (done once, typically during deployment)
try:
    await redis.xgroup_create(
        name="tasks:search",
        groupname="workers:tools",
        id="$"  # Start from latest entries
    )
except:
    pass  # Already exists
```

### Consumer Loop

```python
async def worker_loop():
    consumer_id = f"worker_{pod_name}_{uuid4()}"
    
    while True:
        # Read with blocking for efficiency
        entries = await redis.xreadgroup(
            groupname="workers:tools",
            consumername=consumer_id,
            streams={
                "tasks:search": ">",
                "tasks:database": ">",
                "tasks:api": ">"
            },
            count=1,              # Read 1 message at a time
            block=1000            # Wait up to 1 second
        )
        
        if not entries:
            continue  # Timeout, loop again
        
        for stream_name, messages in entries.items():
            for message_id, data in messages:
                result = await process_task(stream_name, message_id, data)
                
                # Acknowledge only after successful processing
                await redis.xack(stream_name, "workers:tools", message_id)
```

### Failure Handling

```
Scenario 1: Worker crashes during task processing
───────────────────────────────────────────────────

┌────────────────────┐
│ Worker reads entry │
│ task_id: 123       │
└────────┬───────────┘
         │
    ┌────▼──────────────────┐
    │ Processing...         │
    │ 50% through task      │
    │ CRASH! (Pod evicted)  │
    └───────┬───────────────┘
            │
      ┌─────▼─────────────────────────┐
      │ Entry remains PENDING         │
      │ (No XACK was sent)            │
      └─────┬──────┬──────┬───────────┘
            │      │      │
      ┌─────▼┐ ┌──▼──┐ ┌─▼────┐
      │W-Pod1│ │W-Pod2│ │W-Pod3│
      │ Idle │ │Idle  │ │Idle  │
      └──────┘ └──┬───┘ └──────┘
                  │
             ┌────┘
             │
      ┌──────▼──────────────────┐
      │ HPA scales new pod up   │
      │ New worker starts       │
      └──────┬──────────────────┘
             │
      ┌──────▼─────────────────────────────┐
      │ XAUTOCLAIM identifies pending:     │
      │ task_id: 123 was never ACKed       │
      │ Re-assign to new worker            │
      └──────┬─────────────────────────────┘
             │
      ┌──────▼────────────────┐
      │ New worker processes │
      │ task_id: 123         │◄────── Exactly-once: no duplicate
      │ (from beginning)     │
      └──────┬────────────────┘
             │
      ┌──────▼───────────────────┐
      │ XACK confirms completion │
      │ Entry removed from group │
      └────────────────────────┘
```

### Exactly-Once Guarantees

1. **Atomicity**: XREAD + processing + XACK
2. **Durability**: Redis persistence (RDB or AOF)
3. **Idempotency**: Worker checks `task_id` cache before executing
4. **Recovery**: Pending entries re-delivered on worker failure

---

## Configuration: Per-Stream Settings

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-streams-config
data:
  streams: |
    {
      "tasks:search": {
        "max_retention_entries": 10000,
        "max_retention_ms": 86400000,  # 24 hours
        "target_batch_size": 1,
        "block_timeout_ms": 1000,
        "consumer_group": "workers:tools"
      },
      "tasks:database": {
        "max_retention_entries": 5000,
        "max_retention_ms": 3600000,  # 1 hour
        "target_batch_size": 5,       # Batch DB calls
        "block_timeout_ms": 500,
        "consumer_group": "workers:tools"
      },
      "tasks:api": {
        "max_retention_entries": 20000,
        "max_retention_ms": 172800000,  # 48 hours
        "target_batch_size": 1,
        "block_timeout_ms": 100,       # Frequent polling
        "consumer_group": "workers:tools"
      }
    }
```

---

## Monitoring & Health Checks

```python
async def get_stream_health():
    health = {}
    
    for stream in ["tasks:search", "tasks:database", "tasks:api"]:
        info = await redis.xinfo_stream(stream)
        group_info = await redis.xinfo_groups(stream)
        
        for group in group_info:
            pending = group.get("pending", 0)
            consumers = group.get("consumers", 0)
            
            health[f"{stream}:{group['name']}"] = {
                "stream_length": info.get("length", 0),
                "pending_entries": pending,
                "active_consumers": consumers,
                "avg_pending_per_consumer": pending // max(consumers, 1)
            }
    
    return health

# Alert if pending > 1000
# Alert if any stream length growing exponentially
```

---

## See Also

- [03-Components](03-components.md#redis-cache--streams) - Redis component details
- [07-Circuit Breaker](07-circuit-breaker.md) - Failure handling for tools
- [08-Deployment](08-deployment.md) - Redis deployment configuration
