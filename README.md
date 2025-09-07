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