#!/usr/bin/env python3
import argparse
import subprocess
import sys
import shutil
from .config import get_ai_command, show_interactive_config, load_config
from .styles import print_error, print_warning
from .prompts import build_prompt

CONFIG = load_config()


def exit_with_error(message):
    """Print error message and exit with code 1"""
    print_error(message)
    sys.exit(1)


def is_valid_git_ref(ref):
    """Check if a ref is a valid branch (local/remote) or commit"""
    return (
        run_command(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{ref}']) is not None or
        run_command(['git', 'show-ref', '--verify', '--quiet', f'refs/remotes/{ref}']) is not None or
        run_command(['git', 'cat-file', '-e', ref]) is not None
    )


def is_branch(ref):
    """Check if a ref is specifically a branch (not just a commit)"""
    return (
        run_command(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{ref}']) is not None or
        run_command(['git', 'show-ref', '--verify', '--quiet', f'refs/remotes/{ref}']) is not None
    )


def interactive_select(items, message, key_name='item'):
    """
    Generic interactive selector using inquirer.

    Args:
        items: List of tuples (display_text, value)
        message: The prompt message to show
        key_name: The key name for inquirer (used internally)

    Returns:
        The selected value, or exits on cancellation
    """
    import inquirer

    try:
        questions = [
            inquirer.List(key_name,
                         message=message,
                         choices=[item[0] for item in items],
                         carousel=True)
        ]

        answers = inquirer.prompt(questions)
        if not answers:
            exit_with_error("Selection cancelled")

        selected_text = answers[key_name]
        for display_text, value in items:
            if display_text == selected_text:
                return value

        exit_with_error("Selection failed")

    except KeyboardInterrupt:
        exit_with_error("Selection cancelled")

def check_dependencies():
    """Check if required CLIs are available"""
    current_provider = CONFIG.get('ai_provider')

    ai_cmd = CONFIG.get('providers').get(current_provider).get('command')[0]
    if not shutil.which(ai_cmd):
        exit_with_error(f"'{ai_cmd}' CLI not found in PATH")

    if not shutil.which('git'):
        exit_with_error("'git' CLI not found in PATH")

    try:
        import pyperclip
    except ImportError:
        exit_with_error("pyperclip not installed. Install with: pip install pyperclip")

def run_command(cmd, shell=None):
    """Run command and return output, handle errors gracefully"""
    import os

    if shell is None:
        shell = os.name == 'nt'

    try:
        result = subprocess.run(
            cmd if isinstance(cmd, list) else cmd,
            shell=shell,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            errors='replace',
        )
        return result.stdout.strip() if result.stdout else ""
    except subprocess.CalledProcessError:
        return None
    except KeyboardInterrupt:
        exit_with_error("Operation cancelled")

def select_pr_interactive(repo=None):
    """Show PR list and let user select one using a native CLI dropdown"""
    import json

    if not shutil.which('gh'):
        exit_with_error("GitHub CLI (gh) not available - PR selection requires gh CLI")

    cmd = ['gh', 'pr', 'list', '--state', 'all', '--json', 'number,title,author,state']
    if repo:
        cmd.extend(['--repo', repo])

    pr_list_output = run_command(cmd)
    if not pr_list_output:
        exit_with_error(f"No pull requests found{f' in {repo}' if repo else ''}")

    try:
        prs = json.loads(pr_list_output)
    except json.JSONDecodeError:
        exit_with_error("Failed to parse PR list")

    if not prs:
        exit_with_error(f"No pull requests found{f' in {repo}' if repo else ''}")

    choices = []
    for pr in prs:
        state_indicator = "🟢" if pr['state'] == 'OPEN' else "🔴" if pr['state'] == 'CLOSED' else "🟣"
        choice_text = f"#{pr['number']}: {pr['title']} (@{pr['author']['login']}) {state_indicator}"
        choices.append((choice_text, pr['number']))

    return interactive_select(choices, "Select a pull request", 'pr')

def select_commit_interactive():
    """Show recent commits and let user select one"""
    commit_log = run_command(['git', 'log', '--oneline', '--decorate', '--color=never', '-20'])
    if not commit_log:
        exit_with_error("No commits found in repository")

    commit_lines = commit_log.strip().split('\n')
    commits = []

    for line in commit_lines:
        parts = line.split(' ', 1)
        if len(parts) >= 2:
            sha = parts[0]
            message = parts[1] if len(parts) > 1 else "No message"
            commits.append((sha, message))

    if not commits:
        exit_with_error("No commits found")

    choices = [(f"{sha}: {message}", sha) for sha, message in commits]
    return interactive_select(choices, "Select a commit", 'commit')

def select_branch_interactive(message="Select a branch", include_current=True):
    """Show available branches and let user select one"""
    local_branches = run_command(['git', 'branch', '--format=%(refname:short)'])
    remote_branches = run_command(['git', 'branch', '-r', '--format=%(refname:short)'])

    if not local_branches and not remote_branches:
        exit_with_error("No branches found in repository")

    current_branch = run_command(['git', 'branch', '--show-current'])
    branches = []

    # Add local branches
    if local_branches:
        for branch in local_branches.strip().split('\n'):
            branch = branch.strip()
            if branch and (include_current or branch != current_branch):
                is_current = branch == current_branch
                branches.append((branch, 'local', is_current))

    # Add remote branches (excluding HEAD and already seen local branches)
    if remote_branches:
        local_branch_names = [b[0] for b in branches]
        for branch in remote_branches.strip().split('\n'):
            branch = branch.strip()
            if branch and not branch.endswith('/HEAD'):
                if '/' in branch:
                    short_name = branch.split('/', 1)[1]
                    if short_name not in local_branch_names:
                        branches.append((branch, 'remote', False))

    if not branches:
        exit_with_error("No selectable branches found")

    # Create choices for the dropdown menu
    choices = []
    for branch, branch_type, is_current in branches:
        if is_current:
            choice_text = f"{branch} (current)"
        elif branch_type == 'remote':
            choice_text = f"{branch} (remote)"
        else:
            choice_text = branch
        choices.append((choice_text, branch))

    return interactive_select(choices, message, 'branch')

def explain_pr(pr_spec=None, force_select=False, repo=None):
    """Handle pull request explanation. Returns (base_prompt, diff_content)."""
    from .prompts import EXPLAIN_PR_BP

    if not shutil.which('gh'):
        exit_with_error("GitHub CLI (gh) not available - PR explanation requires gh CLI")

    def get_pr_diff(pr_num=None):
        """Get PR diff, optionally for a specific PR number and/or repo."""
        cmd = ['gh', 'pr', 'diff']
        if pr_num:
            cmd.append(str(pr_num))
        if repo:
            cmd.extend(['--repo', repo])
        return run_command(cmd)

    if force_select:
        pr_number = select_pr_interactive(repo=repo)
        diff_content = get_pr_diff(pr_number)
    elif pr_spec and pr_spec != True:
        try:
            pr_number = int(pr_spec)
            diff_content = get_pr_diff(pr_number)
            if not diff_content:
                exit_with_error(f"Could not get diff for PR #{pr_number}. Make sure the PR exists.")
        except ValueError:
            exit_with_error(f"Invalid PR number: '{pr_spec}'. Please provide a valid number.")
    else:
        if repo:
            # Remote repo specified but no PR number - must select interactively
            pr_number = select_pr_interactive(repo=repo)
            diff_content = get_pr_diff(pr_number)
        else:
            # Try current PR, fallback to selection if not in PR branch
            current_pr_check = run_command(['gh', 'pr', 'view'])
            if current_pr_check is None or current_pr_check == "":
                pr_number = select_pr_interactive()
                diff_content = get_pr_diff(pr_number)
            else:
                diff_content = get_pr_diff()

    if not diff_content or diff_content == "":
        exit_with_error("Could not get PR diff or PR has no changes")

    return EXPLAIN_PR_BP(pr_spec), diff_content

def explain_commit(ref='HEAD', force_select=False):
    """Handle commit explanation. Returns (base_prompt, diff_content)."""
    from .prompts import EXPLAIN_COMMIT_BP
    from .styles import print_info

    if ref == 'HEAD' and force_select:
        ref = select_commit_interactive()
    elif ref != 'HEAD':
        if not is_valid_git_ref(ref):
            print_error(f"Could not find commit '{ref}'. Please provide a valid commit SHA, tag, or branch.")
            print_info("Would you like to select from recent commits instead?")
            try:
                response = input("Select from recent commits? (y/N): ").strip().lower()
                if response == 'y':
                    ref = select_commit_interactive()
                else:
                    sys.exit(1)
            except (KeyboardInterrupt, EOFError):
                sys.exit(1)

    diff_content = run_command(['git', 'show', ref])
    if not diff_content:
        exit_with_error("Could not get commit diff")

    return EXPLAIN_COMMIT_BP(ref), diff_content

def explain_diff(ref):
    """Handle diff between current repo state and a commit. Returns (base_prompt, diff_content)."""
    from .prompts import EXPLAIN_DIFF_BP

    if not is_valid_git_ref(ref):
        exit_with_error(f"Could not find commit '{ref}'. Please provide a valid commit SHA, tag, or branch.")

    diff_content = run_command(['git', 'diff', ref])
    if not diff_content:
        exit_with_error(f"No differences found between current state and commit '{ref}'")

    return EXPLAIN_DIFF_BP(ref), diff_content

def explain_branch_diff(branch_spec, force_select=False, file_patterns=None):
    """Handle diff between branches. Returns (base_prompt, diff_content)."""
    from .prompts import EXPLAIN_BRANCH_BP, EXPLAIN_BRANCH_CURRENT_VS_MAIN_BP, EXPLAIN_BRANCH_CURRENT_VS_WORKING_BP

    # Parse branch specification
    if '..' in branch_spec:
        branches = branch_spec.split('..', 1)
        if len(branches) != 2 or not branches[0] or not branches[1]:
            exit_with_error("Invalid branch range format. Use: branch1..branch2")
        from_branch, to_branch = branches[0].strip(), branches[1].strip()
        comparison_type = "range"
    elif force_select:
        from_branch = select_branch_interactive("Select first branch (FROM)", include_current=True)
        to_branch = select_branch_interactive("Select second branch (TO)", include_current=True)
        comparison_type = "range"
    elif branch_spec == "HEAD" or not branch_spec:
        current_branch = run_command(['git', 'branch', '--show-current'])
        if not current_branch:
            exit_with_error("Not on any branch")

        # Try to find main branch (main, master, develop)
        main_branch = None
        for candidate in ['main', 'master', 'develop']:
            if is_branch(candidate):
                main_branch = candidate
                break

        if not main_branch:
            main_branch = select_branch_interactive("Select base branch to compare against", include_current=False)

        from_branch = main_branch
        to_branch = current_branch
        comparison_type = "current_vs_main"
    else:
        from_branch = branch_spec
        to_branch = None
        comparison_type = "branch_vs_working"

    # Validate branches exist
    if comparison_type != "branch_vs_working":
        for branch in [from_branch, to_branch]:
            if not is_valid_git_ref(branch):
                exit_with_error(f"Could not find branch or commit '{branch}'")
    else:
        if not is_valid_git_ref(from_branch):
            exit_with_error(f"Could not find branch or commit '{from_branch}'")

    # Build git diff command
    git_cmd = ['git', 'diff']
    if file_patterns:
        git_cmd.extend(['--'])
        git_cmd.extend(file_patterns)

    # Determine diff range and create appropriate prompt
    if comparison_type == "range":
        git_cmd.insert(2, f"{from_branch}..{to_branch}")
        base_prompt = EXPLAIN_BRANCH_BP(from_branch, to_branch)
    elif comparison_type == "current_vs_main":
        git_cmd.insert(2, f"{from_branch}..{to_branch}")
        base_prompt = EXPLAIN_BRANCH_CURRENT_VS_MAIN_BP(from_branch, to_branch)
    else:
        git_cmd.insert(2, from_branch)
        base_prompt = EXPLAIN_BRANCH_CURRENT_VS_WORKING_BP(from_branch, to_branch)

    diff_content = run_command(git_cmd)
    if not diff_content:
        if comparison_type == "range":
            exit_with_error(f"No differences found between '{from_branch}' and '{to_branch}'")
        elif comparison_type == "current_vs_main":
            exit_with_error(f"No differences found between '{from_branch}' and current branch '{to_branch}'")
        else:
            exit_with_error(f"No differences found between '{from_branch}' and working directory")

    return base_prompt, diff_content

def main():
    parser = argparse.ArgumentParser(
        description='Explain Git commits, GitHub PRs, or branch differences using AI',
        epilog='''
Examples:
  explain -C                    # Explain HEAD commit
  explain -C abc123             # Explain specific commit
  explain -C -s                 # Select commit interactively
  
  explain -P                    # Explain current PR
  explain -P 3                  # Explain specific PR number
  explain -P -s                 # Select PR interactively
  explain -P 123 -R owner/repo  # Explain PR from another GitHub repo
  
  explain -D                    # Compare current branch vs main/master
  explain -D feature..main      # Compare two branches
  explain -D main               # Compare main branch vs working directory
  explain -D abc123             # Compare commit vs working directory
  explain -D -s                 # Select branches interactively
  explain -D -f "*.py"          # Compare only Python files
  
  explain --config              # Configure AI provider and settings
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Main command group
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('-P', '--pull-request', nargs='?', const=True, metavar='NUMBER',
                      help='Explain pull request (current PR, specific number, or use --select for interactive)')
    group.add_argument('-C', '--commit', nargs='?', const='HEAD', metavar='REF',
                      help='Explain commit (defaults to HEAD, use SHA/tag/branch)')
    group.add_argument('-D', '--diff', metavar='SPEC', nargs='?', const='HEAD',
                      help='Explain differences. SPEC can be: branch1..branch2, branch-name, commit-sha, or omitted for current vs main/master')
    
    # Config commands
    group.add_argument('--config', action='store_true',
                      help='Open interactive configuration menu')
    
    # Options
    parser.add_argument('-c', '--clipboard', action='store_true',
                       help='Copy result to clipboard instead of printing to stdout')
    parser.add_argument('-s', '--select', action='store_true',
                       help='Force interactive selection menu')
    parser.add_argument('-f', '--files', metavar='PATTERN', nargs='+',
                       help='Filter diff to specific file patterns (e.g., "*.py" "src/*.js")')

    # Override options (don't change saved config)
    parser.add_argument('--style', metavar='STYLE',
                       choices=['default', 'code_review', 'release_notes', 'nontechnical', 'technical'],
                       help='Response style: default, code_review, release_notes, nontechnical, technical')
    parser.add_argument('-v', '--verbosity', metavar='LEVEL',
                       choices=['concise', 'balanced', 'hyperdetailed'],
                       help='Verbosity level: concise, balanced, hyperdetailed')
    parser.add_argument('-R', '--repo', metavar='OWNER/REPO',
                       help='GitHub repository (e.g., "facebook/react"). Works with -P for remote PRs.')
    
    args = parser.parse_args()
    
    # Handle config commands first
    if args.config:
        show_interactive_config()
        return
    
    # Require one of the main commands
    if not any([args.pull_request is not None, args.commit is not None, args.diff is not None]):
        parser.error('Must specify one of: -P/--pull-request, -C/--commit, -D/--diff, or --config')
    
    check_dependencies()

    # Warn if --repo is used with non-PR commands
    if args.repo and args.pull_request is None:
        print_warning("--repo only works with -P/--pull-request. Ignoring for this command.")

    # Determine which command to run
    if args.pull_request is not None:
        base_prompt, diff_content = explain_pr(pr_spec=args.pull_request, force_select=args.select, repo=args.repo)
    elif args.diff is not None:
        branch_spec = args.diff

        # Handle backward compatibility: if branch_spec looks like a commit SHA,
        # and it's not a valid branch name, fall back to old diff behavior
        if (branch_spec != 'HEAD' and '..' not in branch_spec and not args.select and
            len(branch_spec) >= 7 and all(c in '0123456789abcdef' for c in branch_spec[:7].lower())):
            if not is_branch(branch_spec):
                print_warning(f"'{branch_spec}' looks like a commit SHA. Use -C for commit explanations. Treating as diff vs working directory.")
                base_prompt, diff_content = explain_diff(branch_spec)
            else:
                base_prompt, diff_content = explain_branch_diff(branch_spec, force_select=args.select, file_patterns=args.files)
        else:
            base_prompt, diff_content = explain_branch_diff(branch_spec, force_select=args.select, file_patterns=args.files)
    else:
        base_prompt, diff_content = explain_commit(args.commit, force_select=args.select)

    # Build final prompt with CLI overrides (if any)
    prompt = build_prompt(base_prompt, verbosity_override=args.verbosity, style_override=args.style)

    # Send to AI provider
    from .styles import create_spinner, print_result, print_clipboard_success, ask_copy_raw

    try:
        ai_command, provider = get_ai_command(prompt)

        with create_spinner("Getting explanation...", provider=provider):
            process = subprocess.run(
                ai_command,  # Pass as list
                input=diff_content,
                check=True,
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                shell=False  # Don't use shell - let subprocess handle args properly
            )

        result = process.stdout.strip()

        if args.clipboard:
            import pyperclip
            pyperclip.copy(result)
            print_clipboard_success()
        else:
            print_result(result, is_markdown=True)
            ask_copy_raw(result)

    except subprocess.CalledProcessError:
        exit_with_error(f"Failed to run {provider} command")
    except KeyboardInterrupt:
        exit_with_error("Operation cancelled")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit_with_error("Operation cancelled")
    except Exception as e:
        exit_with_error(f"Unexpected error: {e}")