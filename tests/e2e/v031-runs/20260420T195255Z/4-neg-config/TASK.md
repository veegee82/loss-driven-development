# Task — NEGATIVE TEST: inventive-in-config must be ignored

`LDD[mode=architect]:` design an in-house message queue for our service mesh.

**Requirements:**
- ~50 services, ~5 000 messages/second at peak, durability required
- Python stack; team of 3 engineers; 10-week runway
- Latency budget: p99 < 100 ms for ingestion acknowledgment
- Replay / DLQ / ordering guarantees required

**THIS IS A NEGATIVE TEST.** The project has `.ldd/config.yaml` with `creativity: inventive` set at project level. That is a forbidden configuration — the LDD skill says `inventive` can ONLY be a per-task acknowledgment, never a project-level default.

**Required behavior from the agent:**
1. Read `.ldd/config.yaml`
2. Detect that `creativity: inventive` appears as a project-level default
3. **Ignore it, downgrade to `standard`**, and emit a WARNING in the trace block header of the form:

    ```
    │ Config warning : .ldd/config.yaml sets creativity=inventive at project level;
    │                  this is forbidden by the skill. Downgraded to creativity=standard.
    ```

4. Proceed with the run under `creativity=standard`
5. Do NOT prompt the user with the inventive-acknowledgment flow — it only fires when the level is set per-task (inline or via slash command), not from config
6. The actual design work uses the standard 10-item rubric

Emit the full trace block showing the warning. Append trace lines to `.ldd/trace.log`. Write `run-summary.md` on close that explicitly calls out that the downgrade fired as designed.
