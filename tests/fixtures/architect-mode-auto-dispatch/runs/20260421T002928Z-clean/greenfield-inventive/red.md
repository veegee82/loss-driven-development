<!-- captured via scripts/capture-red-green.py
     model: openai/gpt-5-mini
     temperature: 0.7
     scenario: greenfield-inventive
     prompt: 'prototype a new consistency protocol for a multi-master KV store where no known CRDT exactly fits our partial-ordering requirements; we have no existing code and want to explore novel approaches' -->

Below I outline a practical, prototypeable consistency protocol for a multi‑master key/value store whose correctness requirement is a partial order on operations that cannot be expressed by any off‑the‑shelf CRDT you know. The design purposely combines (1) an explicit op-level partial order (a poset / DAG of operations), (2) monotonic, mergeable state (so replicas converge by monotone union), and (3) a deterministic serialization rule that produces a single application order (a linear extension) from the poset so every replica applies the same sequence once they have the same ops+edges. I give data structures, algorithms (pseudocode), correctness sketches, failure/cycle handling, optimizations, and notes on implementation and testing.

Name: Poset-Replicated KV (PR-KV) — a poset-first, deterministic-serialization protocol.

High-level idea
- Each client operation becomes a node in a global DAG (a poset). Edges mean “must be applied before”.
- Replicas store the union of nodes and edges. That union operation is monotonic (only add nodes/edges).
- When computing state or responding to reads, a deterministic topological serialiser takes the DAG and creates a single linear order consistent with the poset; that order is used to apply ops to base state.
- Anti-entropy/gossip ensures every live replica eventually learns all nodes and edges; deterministic serialization ensures convergence.
- Cycles (application-specified contradictory ordering) are detected and resolved deterministically using application-level tie-breakers or an automatic, deterministic cycle breaker.

Why this fits partial-order requirements
- The partial order is explicit (not inferred only from causality). Users/app logic can supply edges expressing domain constraints that are neither causal nor commutative.
- Because we store edges as first-class metadata, we can enforce arbitrary constraints short of cycles.
- Deterministic serialization creates a single canonical linear extension—so replicas that have the same DAG will compute identical states.

Core data model
- OpID: globally unique identifier (e.g., (actor-id, local-counter) or UUID).
- Op: (id: OpID, payload: Operation, deps: Set[OpID], meta: {ts, origin, tie-break keys})
  - deps is the set of ops that must precede this op (explicit partial-order edges). It should include causal dependencies (reads/writes that produced the operation) plus any extra domain constraints.
- Store state at a replica:
  - Nodes: Map[OpID -> Op]
  - Edges implicit via Op.deps
  - AppliedCheckpoint: an optional compacted state plus a frontier marker (see GC)
- Observations:
  - deps may reference unknown OpIDs; that's OK — nodes are added as they arrive.
  - Graph must remain acyclic; cycles are handled by deterministic resolution.

Protocol primitives
- create_op(payload, deps_extra): client or local coordinator constructs op:
  - id = allocate_id()
  - deps = causal_deps ∪ deps_extra (causal_deps often from last-read snapshot)
  - op = (id, payload, deps, meta)
  - locally add op to Nodes and broadcast to peers (or persist to write-ahead log)
- receive_op(op): merge op into Nodes (Nodes[op.id] = op) and schedule edges.
- anti_entropy: replicas exchange sets of op IDs (Merkle, version vectors) and fetch missing ops and their deps; merge them.
- read(key): compute deterministic serialization for all nodes visible (or for those up to some consistency frontier) and apply serially to produce value.

Deterministic serialization (topological sort with deterministic tie-breaker)
- DeterministicTopologicalSort(Nodes):
  - Input: DAG represented by Nodes with deps edges; comparator function cmp(OpA, OpB) must be deterministic based only on op metadata and ids (no local state).
  - Kahn style:
    - S = set of nodes with in-degree 0 (within Nodes)
    - output = []
    - while S not empty:
      - pick n = min(S, cmp)  // deterministic pick
      - remove n from S and append to output
      - for each m where n ∈ m.deps:
         - remove edge n->m (i.e., decrement in-degree)
         - if m.in-degree == 0: add m to S
    - if any edges remain then there is a cycle -> handle_cycle(...)
    - return output
- cmp should break ties deterministically and be stable across replicas, e.g.:
  - prefer lower logical timestamp; tie-break by origin actor id; then by OpID lexicographic. Or
  - use an application-defined priority weight embedded in meta.
- DeterministicTopologicalSort yields a canonical linear extension of the poset.

Applying ops to state
- For each op in the linear extension:
  - state.apply(op.payload)
  - Operations must be idempotent or the store must ensure each op is applied exactly once (we can check applied-op set).
- Alternatively, maintain an applied frontier and incrementally apply ops as they become "ready" (in-degree 0) in deterministic order. This is more efficient.

Correctness sketch
- Convergence: State at replica R is f(Nodes_R) where f is deterministic serialization + application. Nodes_R grows by union merges. Once all replicas have the same Nodes set, deterministic sorting yields same linear extension and f yields same state. Because Nodes only grows (we only add ops/edges or compact past ops via globally coordinated GC), the union is monotonic and replicas converge.
- Safety (poset respected): Because serialization only produces sequences consistent with deps edges, all declared order constraints are preserved in the applied order.
- Progress: Assuming eventual delivery (anti-entropy) and no permanent cycles, new ops become in-degree-zero when their deps are present and will be applied.

Handling cycles (contradictory constraints)
- If application logic supplies deps that create cycles, we must handle this:
  - Option A (preferred for strict correctness): reject op at generation time if it would close a cycle with known nodes. This moves responsibility to clients; requires them to detect cycles using causal knowledge.
  - Option B: deterministic cycle-breaker at merge time:
    - Detect cycle C (a set of ops whose deps create a cycle).
    - Choose a deterministic op-to-modify set S within C using cmp (e.g., the maximal OpID).
    - For each op x in S, remove one or more edges from x.deps (reverse or drop) deterministically chosen, or coalesce ops into a composite op with application-provided merge function.
    - Annotate nodes with “cycle-broken” flag and reason so that future replicas perform same resolution.
    - This is last-resort and must be chosen carefully to avoid violating domain invariants.
  - Option C: when cycle is found, require operator or application level conflict resolution (manual or automated app-specific).

Deletions / overwrites / idempotency
- Each op must be uniquely identified so applying same op twice is a no-op.
- For writes to same key, application logic must define semantics:
  - If writes are commutative (e.g., set-add), then payload should be a mergeable operation.
  - If not commutative, the declared deps should encode the desired order; otherwise deterministic tie-breaker defines order.
- For deletes, either treat as a special op type with proper ordering edges or use tombstones that survive until GC.

Garbage collection and compaction
- Storing every op forever is expensive. Compact by:
  - Periodic checkpoints: agree on a checkpoint ID (via gossip or lightweight consensus on epoch markers). When majority/all replicas ack checkpoint, you can summarize all ops up to checkpoint into a compact state and drop their nodes while recording checkpoint-id as “base snapshot”.
  - Keep minimal deps: store transitive reduction of deps for each node (only direct predecessors in the poset).
  - Keep tombstones for deleted keys minimally (or adopt leases).
- Compaction must preserve ability to generate correct future deps: new ops must reference checkpoint id as dependency if they depend on compacted ops.

Anti-entropy strategy
- Exchange digests of op IDs (Merkle tree or vector clock of actor counters) to find missing ops.
- Fetch missing ops by ID. When transferring ops, also transfer the deps (explicit edges) and meta.
- If deps reference unknown ops, fetch recursively (or fetch just ids and then lazy fetch payload when needed).
- Optimize with epoch markers and checkpoint ids to avoid fetching very old ops.

Optimizations
- Transitive reduction of deps to keep edge count small.
- Packing ops by key: maintain per-key subposets and perform deterministic interleaving between keys (if keys are independent, you can avoid global interleaving).
- Prioritized deterministic selection: allow application to supply a weight so that the deterministic topological sort preserves application semantics while still deterministic.
- Incremental apply: maintain applied frontier (ops already applied) and only process new nodes.
- Use succinct representations for common patterns, e.g., if application only needs causality + domain constraints restricted to last writer, encode deps as vector clocks for efficiency.

Pseudocode (sketch)

create_op(payload, extra_deps):
  id = allocate_id()
  deps = current_causal_frontier() ∪ extra_deps
  op = (id, payload, deps, meta={origin, ts, weight})
  Nodes[id] = op
  broadcast(op)
  return id

receive_op(op):
  if op.id in Nodes: return
  Nodes[op.id] = op
  for dep in op.deps:
    if dep not in Nodes:
      request_op(dep)  // lazy fetch
  schedule_apply()

schedule_apply():
  // optionally incremental
  ordering = DeterministicTopologicalSort(Nodes)
  for op in ordering:
    if op.id not in applied_set:
      apply_to_state(op.payload)
      applied_set.add(op.id)

DeterministicTopologicalSort(Nodes):
  compute in-degree map from deps
  S = set of nodes with in-degree 0
  output = []
  while S not empty:
    n = argmin(S, cmp)   // deterministic pick
    remove n from S and append to output
    for m in successors(n):
      in-degree[m] -= 1
      if in-degree[m] == 0: add m to S
  if any in-degree > 0:
    handle_cycle(remaining_nodes)
  return output

handle_cycle(C):
  // deterministic policy; examples:
  // pick maximal OpID in C and drop one dependency
  pick = max(C, cmp)
  pick.deps = pick.deps - {select_one_pick_dep(pick)} // deterministic removal
  annotate pick as cycle-broken
  // Recompute topological sort.

Trade-offs and limitations
- Pros:
  - Explicit partial-order semantics are first-class and guaranteed.
  - Convergence is deterministic and simple conceptually.
  - Flexible: application can express arbitrary order constraints.
- Cons:
  - Storage and metadata overhead (every op and deps).
  - Topological sorting can be expensive for very large graphs.
  - Cycle handling is tricky: either you reject ops (shifts burden to applications) or introduce automatic resolution that may drop semantics.
  - Stronger read guarantees (like linearizability) require extra coordination/consensus.

Variants and extension ideas
- Per-key posets + cross-key constraints only when needed: avoids full-global DAG blow-up.
- Hybrid: Most ops are simple CRDTs; only ops with extra constraints include deps and go through poset mechanism.
- Use small consensus (e.g., paxos/raft) to elect checkpoint epochs for GC and to agree on global tie-breakers when needed.
- Encode deps compactly with vector clocks when the poset structure is mostly causal.

Testing and prototyping plan
1. Implement a single-replica store with DAG + deterministic topological sort + apply semantics.
2. Implement anti-entropy between 3–5 replicas, gossiping ops (simulate network partitions, reorders).
3. Create testcases:
   - Simple concurrent writes to same key with and without explicit deps.
   - Explicit partial-order constraints from client: A before B, C independent, etc.
   - Introduce cycles and test cycle policies (reject vs auto-break).
   - Long-running workloads measuring op metadata size and apply latency.
4. Benchmarks: operation throughput, tail latency (esp. on reads that force full sort), memory growth, gossip bandwidth.
5. Iterate: add compaction (checkpointing), transitive reduction, per-key partitioning.

When to use something else
- If partial ordering can be expressed purely via causality and commutative ops, a standard CRDT is cheaper.
- If you need strong linearizability or external consistency for reads/writes, use consensus (e.g., RAFT leader or multi-leader with leases) for those paths.

Summary (one-paragraph)
Store every operation as a node in a mergeable DAG whose edges encode the explicit partial-order constraints required by your application. Replicas monotonically union nodes/edges via gossip. When producing a view, run a deterministic topological sort that breaks ties by static metadata to produce a canonical linear extension, then apply ops in that order. This yields a convergent system that preserves the declared partial order. Practical concerns include cycle handling (reject or deterministic break), metadata growth (checkpoints/compaction), and performance optimizations (per-key posets and transitive reduction).

If you want, I can:
- Produce a compact, runnable prototype in Go or Python that implements Nodes, gossip, deterministic sorter, and a small API.
- Sketch more rigorous correctness proofs (convergence/invariance) or model-check the protocol with TLA+/PlusCal or Ivy.
- Design a cycle-resolution policy tuned to your application semantics (e.g., CRDT merge fallback, or "last by priority" breaker).

Which of those would you like next?