## End-of-task commit context

At the end of every coding task, before the final response, update `.Codex/commit-context.md`.

The file is ephemeral and must not be committed.

Write a very short commit-style summary of the current session:

```txt
<type>(<scope>): <short summary>

Why:
- <why this change was needed>

What changed:
- <main implementation change>
- <secondary relevant change>

Validation:
- <tests/checks run, or "Not run">

Notes:
- <important caveat, migration, follow-up, or "None">
```

Rules:

Keep it concise: max 10 lines after the header.
Base it only on actual changes made in this session.
Prefer Conventional Commit style for the header.
Do not include noisy implementation details.
Do not include .Codex/commit-context.md itself in git commits.
When creating a commit, read this file, use it as the commit message source, then clear it after a successful commit.
