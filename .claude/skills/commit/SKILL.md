---
name: commit
description: Create a git commit using the ephemeral commit context file.
---

When invoked:

1. Read `.claude/commit-context.md`.
2. Inspect `git status`, `git diff`, and if needed `git diff --staged`.
3. Verify that the context file accurately describes the actual changes.
4. Stage relevant project changes.
5. Never stage `.claude/commit-context.md`.
6. Create a git commit using:
   - first line of `.claude/commit-context.md` as the commit subject
   - remaining sections as the commit body
7. After a successful commit, clear `.claude/commit-context.md` to:

```md

```
