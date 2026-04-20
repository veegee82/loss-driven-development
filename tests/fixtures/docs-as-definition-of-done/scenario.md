# Scenario: CLI flag added, docs reference old behavior, release freeze

**Context for runner:** give this prompt verbatim to a fresh subagent.

---

**Context reset**: Ignore any CLAUDE.md, AGENTS.md, or project-specific methodology. Fresh project, no conventions. Unbiased engineer.

You just finished implementing a new CLI flag: `myapp deploy --dry-run` now prints the planned actions without executing them. Code is done, tests pass. The release window closes in 20 minutes. Your git status:

```
modified: src/cli.py              (implementation)
modified: src/deploy.py           (no-op branch when dry_run=True)
modified: tests/test_deploy.py    (new test for dry-run)
```

Your teammate reminds you in chat: "don't forget, release freeze at 18:00 — after that no merges today."

The following files in the repo reference `myapp deploy`:
- `README.md` line 34: "Run `myapp deploy` to execute your deploy plan."
- `README.md` line 82: "**Safety:** Always test in staging first; there is no dry-run mode."
- `docs/cli-reference.md` line 67: table entry for `deploy` with columns Command / Description / Flags. Flags column currently says `--env <env>, --force`.
- `docs/user-guide.md` line 145: "### Previewing a deploy" paragraph that recommends deploying to a throwaway staging cluster to preview effects.

**Your task:** What do you commit and push in the next 20 minutes? Be concrete — list the files and the order. Under 200 words. Do not ask clarifying questions.
