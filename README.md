# explain-cli

Explain Git commits and PRs using Claude Code or Gemini CLI.

## Install

```bash
# uv
uv tool install https://github.com/ccmdi/explain-cli.git

# pip
pip install https://github.com/ccmdi/explain-cli.git
```

## Usage

```bash
# Interactive commit/PR selection
explain -C -s  # Select from recent commits
explain -P -s  # Select from all PRs

# Direct usage
explain -C          # Current commit
explain -C abc1234  # Specific commit
explain -P          # Current PR
explain -D abc1234  # Diff vs commit

# Configuration
explain --config

# Copy to clipboard
explain -C -c
```

## Requirements

- `git`
- `gh` CLI (for PRs)
- `gemini` CLI or `claude` code