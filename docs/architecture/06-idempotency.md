# 6. Idempotency: Handling Duplicate Requests

## Problem Statement

In a stateful system, duplicate requests can cause serious problems:

**What happens when the same user request arrives twice?**

Without careful handling:
- **Double-execution**: Tool called twice → payment charged twice, email sent twice
- **Divergent states**: Workflow branches into two paths
- **Data corruption**: Conflicting results stored

Example:
```
User submits: "Transfer $100 to Bob"
    ↓
Request reaches gateway, forwarded to orchestrator
    ↓
Tool executes: deduct_account($100)
    ↓
Network hiccup; client doesn't receive response
    ↓
User (frustrated) clicks "retry"
    ↓
Duplicate request arrives
    ↓
Without idempotency: New transfer executed → Bob receives $200 total! ❌
```

---

## Solution: Request Deduplication via Session + Request ID

### 1. Unique Request Identification

Every request must include a stable, unique identifier:

```json
{
  "session_id": "sess_abc123",
  "request_id": "req_xyz789_v1",
  "payload": {...}
}
```

The `request_id` can come from:
- **Client-generated** (Stripe style): Client sets `X-Idempotency-Key` header
- **Server-generated**: Gateway generates UUID if not provided
- **Must be stable**: Same client retry uses same ID; allows deduplication window

### 2. Full Key Construction

```python
# In FastAPI Gateway
@app.post("/agent/run")
async def run_agent(request: AgentRequest, headers: dict):
    session_id = request.session_id or await redis.incr("session_counter")
    
    # Extract or generate idempotency key
    request_id = headers.get("X-Idempotency-Key") or str(uuid4())
    
    # Full dedup key
    full_key = f"{session_id}:{request_id}"
    
    return await handle_request(session_id, request_id, request.payload)
```

### 3. Deduplication Flow

```python
async def handle_request(session_id, request_id, payload):
    """
    Handle request with deduplication.
    Returns result either from cache or by executing workflow.
    """
    
    # Step 1: Check if already completed (within TTL)
    cached_result = await redis.get(f"request:{session_id}:{request_id}:result")
    
    if cached_result:
        log(f"Duplicate request {request_id}: returning cached result")
        prometheus.counter("duplicate_requests_from_cache").inc()
        return json.loads(cached_result)
    
    # Step 2: Check if currently being processed
    processing = await redis.get(f"request:{session_id}:{request_id}:processing")
    
    if processing:
        # Already in progress
        log(f"Request {request_id} already in progress")
        prometheus.counter("duplicate_requests_in_flight").inc()
        # Option A: Wait for completion (poll with timeout)
        # Option B: Return 202 Accepted with retry-after
        return {"status": "pending", "check_after": 5, "location": f"/status/{request_id}"}
    
    # Step 3: Mark as processing (atomic)
    await redis.set(
        f"request:{session_id}:{request_id}:processing",
        "true",
        ex=300  # 5 minute timeout (fails if orchestrator disappears)
    )
    
    try:
        # Step 4: Execute workflow
        log(f"Executing request {request_id}")
        result = await execute_workflow(session_id, request_id, payload)
        
        # Step 5: Cache result
        await redis.set(
            f"request:{session_id}:{request_id}:result",
            json.dumps(result),
            ex=3600  # 1 hour TTL
        )
        
        prometheus.counter("requests_completed_total", status="success").inc()
        return result
        
    except Exception as e:
        log(f"Request {request_id} failed: {e}")
        prometheus.counter("requests_completed_total", status="error").inc()
        raise
        
    finally:
        # Step 6: Clean up "in-progress" marker
        await redis.delete(f"request:{session_id}:{request_id}:processing")
```

---

## Checkpoint-Level Idempotency

Deduplication also occurs at the tool execution level. Each tool invocation has a unique `task_id`:

```json
{
  "task_id": "task_sess-abc_req-xyz_step-5",
  "session_id": "sess_abc123",
  "step": 5,
  "tool": "search",
  "params": {"query": "..."}
}
```

The `task_id` format: `task_{session_id}_{request_id}_{step}`

Workers check before executing:

```python
async def process_task(message):
    """Execute tool with checkpoint-level deduplication."""
    
    task_id = message.get("task_id")
    
    # Check if already executed
    cached_task_result = await redis.get(f"task_result:{task_id}")
    if cached_task_result:
        log(f"Task {task_id} already executed, returning cache")
        prometheus.counter("duplicate_task_executions_skipped").inc()
        return json.loads(cached_task_result)
    
    # Execute tool
    result = await execute_tool(
        message.get("tool"),
        json.loads(message.get("params"))
    )
    
    # Cache result
    await redis.set(f"task_result:{task_id}", json.dumps(result), ex=86400)
    
    prometheus.counter("task_executions_completed").inc()
    return result
```

---

## Duplicate Request Scenarios

| Scenario | Handling | Outcome |
|----------|----------|---------|
| **Duplicate within 1 hour** | Return cached result from Redis (instant) | No re-execution |
| **Duplicate during processing** | Return 202 Accepted; client polls until done | Single execution |
| **Same checkpoint executed twice** | Tool result cached by `task_id`; duplicates skipped | No double-charge |
| **User resubmits after 1 hour** | Cache expired; workflow re-executed | Intentional re-run (user knows) |
| **Tool side-effect already applied externally** | Tool must use idempotent operations (upsert, not insert) | Database consistency |

---

## Idempotent Tool Design

### Bad: Inherently Non-Idempotent

```python
async def transfer_funds(from_account, to_account, amount):
    """❌ Non-idempotent: Calling twice = double charge"""
    
    # Get current balance
    balance = await db.get_balance(from_account)
    
    # Deduct amount
    new_balance = balance - amount
    
    # Update
    await db.set_balance(from_account, new_balance)
    
    # If this function is called twice: Bob loses $200, not $100!
```

### Good: Idempotent via Upsert

```python
async def transfer_funds_idempotent(
    from_account,
    to_account,
    amount,
    transaction_id  # Unique identifier
):
    """✅ Idempotent: Safe to call multiple times"""
    
    # Check if already applied
    existing = await db.query(
        "SELECT * FROM transfers WHERE transaction_id = ?",
        (transaction_id,)
    )
    
    if existing:
        # Already executed; return cached result
        log(f"Transfer {transaction_id} already applied")
        return {"status": "already_applied", "result": existing}
    
    # Apply transfer (first time)
    await db.execute("""
        INSERT INTO transfers (transaction_id, from_account, to_account, amount)
        VALUES (?, ?, ?, ?)
    """, (transaction_id, from_account, to_account, amount))
    
    # Update account balances
    await db.execute(
        "UPDATE accounts SET balance = balance - ? WHERE id = ?",
        (amount, from_account)
    )
    await db.execute(
        "UPDATE accounts SET balance = balance + ? WHERE id = ?",
        (amount, to_account)
    )
    
    result = {"status": "success", "amount": amount}
    return result
    
    # Second call with same transaction_id: Returns {"status": "already_applied"}
    # Safe! Transaction applied exactly once.
```

### Best Practice: External API Calls

```python
async def call_external_api_idempotent(endpoint, payload, api_request_id):
    """Call external API with idempotency key."""
    
    # Check cache
    cached = await redis.get(f"api_call:{api_request_id}")
    if cached:
        return json.loads(cached)
    
    # Call API with idempotency-key header
    response = await httpx.post(
        endpoint,
        json=payload,
        headers={
            "X-Idempotency-Key": api_request_id,  # Tell API this is a replay
            "X-Request-ID": api_request_id
        }
    )
    
    result = response.json()
    
    # Cache
    await redis.set(f"api_call:{api_request_id}", json.dumps(result), ex=3600)
    
    return result
    
    # If called twice with same api_request_id:
    # - First call: API processes and returns 200 OK
    # - Second call: API recognizes idempotency key, returns 200 OK with cached results
    # - Our code returns from Redis cache anyway
```

---

## Kubernetes ConfigMap: Idempotency Policy

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: idempotency-config
  namespace: default
data:
  request_dedup_ttl: "3600"          # 1 hour cache for requests
  task_result_ttl: "86400"           # 24 hour cache for tool results
  processing_timeout: "300"          # 5 minute timeout for in-progress
  enable_automatic_retry: "true"
  retry_on_duplicate: "false"        # Don't auto-retry duplicates
  task_id_format: "task_{session}_{request}_{step}"
  cache_backend: "redis"             # Can be redis or memcached
  dedup_on: "request"                # Level: request, checkpoint, or both
```

---

## Monitoring & Alerting

```python
# Prometheus metrics for deduplication
duplicate_requests_total = Counter(
    'duplicate_requests_total',
    'Total duplicate requests',
    ['status']  # cached, in_flight, expired
)

duplicate_request_latency = Histogram(
    'duplicate_request_latency_ms',
    'Latency for duplicate request (should be near-instant)',
    buckets=(1, 5, 10, 50, 100)
)

# Dashboard queries:
# - rate(duplicate_requests_total{status="cached"}[5m]) : Duplicate hit rate
# - avg(duplicate_request_latency_ms) : Avg time to serve from cache
# - Alerts: If duplicate_request_latency_ms > 100ms → Cache issue
```

---

## HTTP Status Codes for Idempotency

```
POST /agent/run
├─ 200 OK: Request completed, result returned
├─ 202 Accepted: Request is being processed (poll for result)
├─ 409 Conflict: previous request for same idempotency key returned different result
└─ 429 Too Many Requests: System under load, retry after header

Headers:
├─ X-Idempotency-Key: (request) Unique key for deduplication
├─ Idempotency-Replay: (response) "true" if this is a cached replay
├─ Retry-After: (response) Seconds to wait before next poll
└─ Location: (response, 202) URL to check request status
```

Example Response:
```json
// First request
POST /agent/run with X-Idempotency-Key: key-123
Response: 200 OK
{"session_id": "sess_abc", "result": {...}}

// Duplicate during processing
POST /agent/run with X-Idempotency-Key: key-123
Response: 202 Accepted
{
  "status": "pending",
  "check_after": 5,
  "location": "/status/sess_abc?request_id=req-xyz"
}

// Duplicate after completion
POST /agent/run with X-Idempotency-Key: key-123
Response: 200 OK
{
  "session_id": "sess_abc",
  "result": {...},
  "idempotency_replay": true
}
```

---

## See Also

- [05-State Persistence](05-state-persistence.md) - Checkpoint structure
- [04-Async Communication](04-async-communication.md) - Task-level dedup
- [07-Circuit Breaker](07-circuit-breaker.md) - Tool resilience
