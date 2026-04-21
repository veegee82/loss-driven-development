<!-- captured via scripts/capture-red-green.py
     model: deepseek/deepseek-chat-v3.1
     temperature: 0.7
     scenario: regression-and-recovery
     prompt: "LDD: I'm optimizing worker process startup time. The rubric is 6 items (p50 < 500 ms, p99 < 800 ms, no zombie threads, no stale caches, warmup deterministic, cold-start <= 1200 ms). Per-iteration loss:\n\n- i1: 4/6 violations after first optimization pass (loss = 0.667).\n- i2: 5/6 — REGRESSION: I cached the wrong object, p99 got worse (loss = 0.833).\n- i3: 1/6 — reverted the bad cache, different approach, almost there (loss = 0.167).\n\nThe trajectory is NOT monotonic: it regresses from i1 to i2, then recovers from i2 to i3. End-to-end net direction is descent (0.667 → 0.167). Emit the full LDD trace block showing the regression and recovery." -->

{
    "trajectory": [
        {
            "iteration": "i1",
            "violations": 4,
            "loss": 0.667,
            "comment": "After first optimization pass"
        },
        {
            "iteration": "i2",
            "violations": 5,
            "loss": 0.833,
            "comment": "REGRESSION: Cached the wrong object, p99 got worse"
        },
        {
            "iteration": "i3",
            "violations": 1,
            "loss": 0.167,
            "comment": "Reverted the bad cache, different approach, almost there"
        }
    ],
    "net_direction": "descent",
    "net_improvement": 0.5
}