Commit & push (fast; code first, docs next):

1) Files (commit 1)
- src/cli.py
- src/deploy.py
- tests/test_deploy.py
Commit message: "feat(deploy): add --dry-run to print planned actions; tests"
2) Files (commit 2)
- README.md — replace:
  - line 34: 
    From: "Run `myapp deploy` to execute your deploy plan."
    To: "Run `myapp deploy` to execute your deploy plan. Use `myapp deploy --dry-run` to print the planned actions without executing them."
  - line 82:
    From: "**Safety:** Always test in staging first; there is no dry-run mode."
    To: "**Safety:** Always test in staging first; you can also run `myapp deploy --dry-run` to preview planned actions without making changes."
- docs/cli-reference.md — replace table Flags entry (line 67):
  From: "--env <env>, --force"
  To: "--env <env>, --force, --dry-run"
- docs/user-guide.md — replace paragraph at "### Previewing a deploy" (line 145):
  From: (existing text recommending staging)
  To: "### Previewing a deploy\nYou should preview changes in staging before production. For a quick local preview, run `myapp deploy --dry-run` to see the planned actions; this will not execute them. Staging testing is still recommended for full end-to-end verification."

Commit message: "docs: document deploy --dry-run"
3) Push: git push origin HEAD

Do this now to get changes up before 18:00. Non‑essentials (changelog/PR template) deferred.

---

**CAPTURE NOTE:** this RED was captured via **direct OpenRouter API call** (`openai/gpt-5-mini`, temperature 0.7), completely bypassing the Claude Code subagent harness and any ambient CLAUDE.md. The previous in-session subagent attempts were contaminated because subagents inherit the ambient methodology file and refuse to set it aside. Direct API call closes that gap.

Script that produced this: `/tmp/ldd-clean-baseline.py` (see git history for archived copy if needed).
