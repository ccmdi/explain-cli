# explain-git

Explain Git commits and PRs using Claude Code or Gemini CLI.

## Usage

```bash
# Explain current commit
explain -C

# Explain specific commit
explain -C abc1234

# Explain current PR (must be in PR branch)
explain -P

# Explain diff between current state and commit
explain -D abc1234

# Copy to clipboard instead of stdout
explain -C -c
explain -P -c
explain -D abc1234 -c
```

## Requirements

- `gh` CLI (GitHub)
- `gemini` CLI / `claude` code