# 8. Deployment & Operations

Kubernetes manifests, deployment strategies, and operational checklists for production deployment.

---

## Kubernetes Manifest Structure

### 1. FastAPI Gateway Deployment

```yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: ai-agent-platform

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-gateway
  namespace: ai-agent-platform
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: ai-gateway
  template:
    metadata:
      labels:
        app: ai-gateway
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: gateway
        image: myregistry/ai-gateway:latest
        imagePullPolicy: Always
        ports:
        - name: http
          containerPort: 8000
          protocol: TCP
        env:
        - name: ORCHESTRATOR_URL
          value: "http://ai-orchestrator:8001"
        - name: REDIS_URL
          value: "redis://redis-cache:6379"
        - name: LANGSMITH_API_KEY
          valueFrom:
            secretKeyRef:
              name: langsmith-credentials
              key: api-key
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
      terminationGracePeriodSeconds: 30

---
apiVersion: v1
kind: Service
metadata:
  name: ai-gateway
  namespace: ai-agent-platform
spec:
  selector:
    app: ai-gateway
  type: LoadBalancer
  ports:
  - name: http
    port: 80
    targetPort: 8000
    protocol: TCP
```

### 2. LangGraph Orchestrator Deployment

```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-orchestrator
  namespace: ai-agent-platform
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ai-orchestrator
  template:
    metadata:
      labels:
        app: ai-orchestrator
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8001"
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - ai-orchestrator
              topologyKey: kubernetes.io/hostname
      containers:
      - name: orchestrator
        image: myregistry/ai-orchestrator:latest
        imagePullPolicy: Always
        ports:
        - name: http
          containerPort: 8001
          protocol: TCP
        env:
        - name: REDIS_URL
          value: "redis://redis-cache:6379"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: url
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: gemini-credentials
              key: api-key
        - name: LANGSMITH_API_KEY
          valueFrom:
            secretKeyRef:
              name: langsmith-credentials
              key: api-key
        resources:
          requests:
            cpu: 1000m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 15
          periodSeconds: 10
      terminationGracePeriodSeconds: 30

---
apiVersion: v1
kind: Service
metadata:
  name: ai-orchestrator
  namespace: ai-agent-platform
spec:
  selector:
    app: ai-orchestrator
  type: ClusterIP
  ports:
  - name: http
    port: 8001
    targetPort: 8001
```

### 3. Agent Workers StatefulSet

```yaml
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: ai-workers
  namespace: ai-agent-platform
spec:
  replicas: 5
  serviceName: ai-workers
  selector:
    matchLabels:
      app: ai-worker
  template:
    metadata:
      labels:
        app: ai-worker
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      containers:
      - name: worker
        image: myregistry/ai-worker:latest
        imagePullPolicy: Always
        ports:
        - name: metrics
          containerPort: 9090
          protocol: TCP
        env:
        - name: REDIS_URL
          value: "redis://redis-cache:6379"
        - name: WORKER_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: CONSUMER_GROUP
          value: "workers:tools"
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        livenessProbe:
          tcpSocket:
            port: 9090
          initialDelaySeconds: 20
          periodSeconds: 10
      terminationGracePeriodSeconds: 30

---
apiVersion: v1
kind: Service
metadata:
  name: ai-workers
  namespace: ai-agent-platform
spec:
  clusterIP: None
  selector:
    app: ai-worker
  ports:
  - name: metrics
    port: 9090
    targetPort: 9090
```

### 4. Horizontal Pod Autoscaler (HPA)

```yaml
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-workers-hpa
  namespace: ai-agent-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: StatefulSet
    name: ai-workers
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: redis_streams_pending_entries
      target:
        type: AverageValue
        averageValue: "100"  # If > 100 pending per pod, scale up
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 15
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 5
        periodSeconds: 15
      selectPolicy: Max
```

### 5. Redis StatefulSet

```yaml
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-cache
  namespace: ai-agent-platform
spec:
  serviceName: redis-cache
  replicas: 1
  selector:
    matchLabels:
      app: redis-cache
  template:
    metadata:
      labels:
        app: redis-cache
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        command:
          - redis-server
          - "--appendonly"
          - "yes"
          - "--maxmemory"
          - "4gb"
          - "--maxmemory-policy"
          - "allkeys-lru"
        resources:
          requests:
            cpu: 500m
            memory: 4Gi
          limits:
            cpu: 1000m
            memory: 4Gi
        volumeMounts:
        - name: redis-storage
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: redis-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 50Gi

---
apiVersion: v1
kind: Service
metadata:
  name: redis-cache
  namespace: ai-agent-platform
spec:
  clusterIP: None
  selector:
    app: redis-cache
  ports:
  - port: 6379
    targetPort: 6379
```

### 6. ConfigMaps

```yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: circuit-breaker-config
  namespace: ai-agent-platform
data:
  config.json: |
    {
      "tool:search": {
        "failure_threshold": 5,
        "window_seconds": 60,
        "cooldown_seconds": 30
      },
      "tool:database": {
        "failure_threshold": 3,
        "window_seconds": 30,
        "cooldown_seconds": 60
      }
    }

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: agent-persistence-config
  namespace: ai-agent-platform
data:
  checkpoint_interval: "1"
  redis_ttl: "86400"
  postgres_batch_size: "100"

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: idempotency-config
  namespace: ai-agent-platform
data:
  request_dedup_ttl: "3600"
  task_result_ttl: "86400"
  processing_timeout: "300"
```

### 7. Secrets

```yaml
---
apiVersion: v1
kind: Secret
metadata:
  name: postgres-credentials
  namespace: ai-agent-platform
type: Opaque
stringData:
  url: "postgresql://user:password@postgres.default.svc.cluster.local:5432/agent_db"

---
apiVersion: v1
kind: Secret
metadata:
  name: gemini-credentials
  namespace: ai-agent-platform
type: Opaque
stringData:
  api-key: "your-gemini-api-key-here"

---
apiVersion: v1
kind: Secret
metadata:
  name: langsmith-credentials
  namespace: ai-agent-platform
type: Opaque
stringData:
  api-key: "your-langsmith-api-key-here"
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] K8S cluster ready (EKS, GKE, AKS, or self-hosted)
- [ ] Namespace `ai-agent-platform` created
- [ ] Docker images built and pushed to registry
- [ ] All configs reviewed (CPU, memory, replicas)

### Infrastructure

- [ ] PostgreSQL database provisioned (managed service or self-hosted)
- [ ] PostgreSQL backups configured (daily snapshots to S3)
- [ ] Redis instance deployed (or external Redis)
- [ ] Redis persistence enabled (RDB or AOF)
- [ ] Network policies configured (pod-to-pod, pod-to-external)
- [ ] TLS/SSL certificates for ingress configured

### K8S Resources

- [ ] Namespace created
- [ ] Secrets created for all API keys and credentials
- [ ] ConfigMaps created for tool/agent definitions
- [ ] Deployments created (Gateway, Orchestrator)
- [ ] StatefulSet created (Workers, Redis, PostgreSQL)
- [ ] Services created (internal + load balancer)
- [ ] Ingress configured for external traffic
- [ ] Persistent Volume Claims bound

### Monitoring & Logging

- [ ] Prometheus deployed and scraping metrics
- [ ] Grafana dashboards created:
  - [ ] Circuit Breaker Health
  - [ ] Request/Response latencies
  - [ ] Redis/PostgreSQL performance
  - [ ] Pod resource utilization
- [ ] Alertmanager configured for critical alerts
- [ ] Log aggregation (ELK, Loki, CloudLogging) set up
- [ ] Log retention policies configured

### Health & Readiness

- [ ] Liveness probes verified (pod restarts on failure)
- [ ] Readiness probes verified (pod removed from LB if unhealthy)
- [ ] PodDisruptionBudgets created to prevent ungraceful evictions
- [ ] Pod Anti-Affinity rules prevent multiple pods on same node

### Validation

- [ ] Run smoke test: Simple agent workflow end-to-end
- [ ] Run load test: 100+ concurrent workflows
- [ ] Verify failover: Kill pod, check recovery
- [ ] Verify scaling: HPA triggers scale up/down
- [ ] Check logs for errors/warnings
- [ ] Monitor resource usage during test

### Post-Deployment

- [ ] Infrastructure backup/disaster recovery tested
- [ ] On-call runbook documented
- [ ] Escalation procedures documented
- [ ] Rollback plan tested
- [ ] Performance baselines established

---

## Operational Tasks

### Scaling

```bash
# Manually scale workers
kubectl scale statefulset ai-workers --replicas=10 -n ai-agent-platform

# Check HPA status
kubectl get hpa -n ai-agent-platform

# View HPA metrics
kubectl get hpa ai-workers-hpa --watch -n ai-agent-platform
```

### Debugging

```bash
# View logs for orchestrator
kubectl logs -f deployment/ai-orchestrator -n ai-agent-platform

# View logs for a worker
kubectl logs pod/ai-workers-0 -n ai-agent-platform

# Exec into pod for debugging
kubectl exec -it pod/ai-gateway-xyz -n ai-agent-platform -- /bin/bash

# Describe pod for events
kubectl describe pod/ai-workers-0 -n ai-agent-platform
```

### Updates & Rollouts

```bash
# Update image
kubectl set image deployment/ai-gateway \
  gateway=myregistry/ai-gateway:v1.1.0 \
  -n ai-agent-platform

# Check rollout status
kubectl rollout status deployment/ai-gateway -n ai-agent-platform

# Rollback if needed
kubectl rollout undo deployment/ai-gateway -n ai-agent-platform
```

### Backup & Recovery

```bash
# Backup PostgreSQL
kubectl exec -it postgres-0 -- pg_dump -U user db > backup.sql

# Backup Redis
kubectl exec -it redis-cache-0 -- redis-cli BGSAVE
kubectl cp ai-agent-platform/redis-cache-0:/data/dump.rdb ./redis-backup.rdb

# Restore from backup
kubectl exec -i postgres-0 -- psql -U user db < backup.sql
```

---

## High Availability (HA) Setup

### Replicas & Failures

| Component | Replicas | Failures Handled |
|-----------|----------|------------------|
| Gateway | 3 | 1 pod failure (L4 LB balances to 2 healthy) |
| Orchestrator | 2 | 1 pod failure (no state lost, stateless) |
| Workers | 5-20 | Up to (N-1) failures (work redistributed) |
| Redis | 1 → 3 (sentinel) | Automatic failover with Sentinel |
| PostgreSQL | 1 → 3 (replication) | Read replicas, async replication |

### Pod Disruption Budgets

```yaml
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: ai-gateway-pdb
  namespace: ai-agent-platform
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: ai-gateway

---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: ai-workers-pdb
  namespace: ai-agent-platform
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: ai-worker
```

---

## See Also

- [01-Overview](01-overview.md) - Architecture overview
- [02-C4 Diagrams](02-c4-diagrams.md) - Deployment topology
- [03-Components](03-components.md) - Component details
