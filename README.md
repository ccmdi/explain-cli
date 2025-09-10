# explain-cli

Explain Git commits, PRs, and branch differences using Claude Code or Gemini CLI.

## Install

```bash
# uv
uv tool install explain-cli
# uv (source)
uv tool install https://github.com/ccmdi/explain-cli.git

# pip
pip install explain-cli
# pip (source)
pip install https://github.com/ccmdi/explain-cli.git
```

## Commands

```bash
# Explain commits
explain -C                    # Current commit
explain -C -s                 # Pick from recent commits

# Explain PRs  
explain -P                    # Current PR
explain -P -s                 # Pick from all PRs

# Compare branches
explain -D                    # Compare your current work vs master/main
explain -D feature..main      # Compare two branches

# Interactive selection
explain -D -s                 # Pick branches to compare
explain -D -f "*.py"          # Only Python files
explain -C abc1234 -c         # Copy to clipboard

# Configuration
explain --config              # Set AI provider & verbosity
```

## Requirements

- `git`
- `gh` CLI (for PRs)
- `gemini` CLI or `claude` code