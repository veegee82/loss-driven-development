---
description: Show the current LDD trace for this task, and summarize the last 5 entries from .ldd/trace.log if it exists in the project.
---

Display the current LDD trace block (the one mandated by `skills/using-ldd/SKILL.md` §"The LDD trace — mandatory visible output") for the task currently in flight. If no LDD task is active right now, say so plainly — do NOT invent a trace.

Then, if a file `.ldd/trace.log` exists in the current project root, show the last 5 non-blank entries as a compact table. If the file does not exist, say "no persisted trace in this project yet" and do not create it speculatively — the trace log is populated automatically as LDD skills invoke.

If the user asks for the full trace history (`--all` / "all" / "everything"), show the entire log. Otherwise default to the last 5.

Do not produce the trace for tasks that predate the current session unless the log file has entries. The block is the live state, not a retrospective reconstruction.
