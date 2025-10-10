#!/usr/bin/env python3
import argparse
import subprocess
import sys
import shutil
from .config import get_ai_command, show_interactive_config, load_config
from .styles import print_error, print_warning

CONFIG = load_config()

def check_dependencies():
    """Check if required CLIs are available"""
    current_provider = CONFIG.get('ai_provider')
    
    ai_cmd = CONFIG.get('providers').get(current_provider).get('command')[0]
    if not shutil.which(ai_cmd):
        print_error(f"'{ai_cmd}' CLI not found in PATH")
        sys.exit(1)
    
    if not shutil.which('git'):
        print_error("'git' CLI not found in PATH")
        sys.exit(1)
    
    try:
        import pyperclip
    except ImportError:
        print_error("pyperclip not installed. Install with: pip install pyperclip")
        sys.exit(1)

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
            errors='replace',  # Replace problematic chars instead of failing
        )
        return result.stdout.strip() if result.stdout else ""
    except subprocess.CalledProcessError as e:
        return None
    except KeyboardInterrupt:
        print_error("Operation cancelled")
        sys.exit(1)

def select_pr_interactive():
    """Show PR list and let user select one using a native CLI dropdown"""
    import inquirer

    if not shutil.which('gh'):
        print_error("GitHub CLI (gh) not available - PR selection requires gh CLI")
        sys.exit(1)
    
    pr_list_output = run_command(['gh', 'pr', 'list', '--state', 'all', '--json', 'number,title,author,state'])
    if not pr_list_output:
        print_error("No pull requests found")
        sys.exit(1)
    
    import json
    try:
        prs = json.loads(pr_list_output)
    except json.JSONDecodeError:
        print_error("Failed to parse PR list")
        sys.exit(1)
    
    if not prs:
        print_error("No pull requests found")
        sys.exit(1)
    
    choices = []
    for pr in prs:
        state_indicator = "🟢" if pr['state'] == 'OPEN' else "🔴" if pr['state'] == 'CLOSED' else "🟣"
        choice_text = f"#{pr['number']}: {pr['title']} (@{pr['author']['login']}) {state_indicator}"
        choices.append((choice_text, pr['number']))
    
    try:
        questions = [
            inquirer.List('pr',
                         message="Select a pull request",
                         choices=[choice[0] for choice in choices],
                         carousel=True)
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            # print("\nSelection cancelled", file=sys.stderr)
            sys.exit(1)
            
        # Find the PR number for the selected choice
        selected_text = answers['pr']
        for choice_text, pr_number in choices:
            if choice_text == selected_text:
                return pr_number
                
    except KeyboardInterrupt:
        print_error("Selection cancelled")
        sys.exit(1)

def select_commit_interactive():
    """Show recent commits and let user select one"""
    import inquirer

    # Get recent commits with nice formatting
    commit_log = run_command(['git', 'log', '--oneline', '--decorate', '--color=never', '-20'])
    if not commit_log:
        print_error("No commits found in repository")
        sys.exit(1)
    
    # Parse commits
    commit_lines = commit_log.strip().split('\n')
    commits = []
    
    for line in commit_lines:
        parts = line.split(' ', 1)
        if len(parts) >= 2:
            sha = parts[0]
            message = parts[1] if len(parts) > 1 else "No message"
            commits.append((sha, message))
    
    if not commits:
        print_error("No commits found")
        sys.exit(1)
    
    # Create choices for the dropdown menu
    choices = []
    for sha, message in commits:
        choice_text = f"{sha}: {message}"
        choices.append((choice_text, sha))
    
    # Show native CLI dropdown
    try:
        questions = [
            inquirer.List('commit',
                         message="Select a commit",
                         choices=[choice[0] for choice in choices],
                         carousel=True)
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            print_error("Selection cancelled")
            sys.exit(1)
            
        # Find the commit SHA for the selected choice
        selected_text = answers['commit']
        for choice_text, sha in choices:
            if choice_text == selected_text:
                return sha
                
    except KeyboardInterrupt:
        print_error("Selection cancelled")
        sys.exit(1)

def select_branch_interactive(message="Select a branch", include_current=True):
    """Show available branches and let user select one"""
    import inquirer

    # Get all branches (local and remote)
    local_branches = run_command(['git', 'branch', '--format=%(refname:short)'])
    remote_branches = run_command(['git', 'branch', '-r', '--format=%(refname:short)'])
    
    if not local_branches and not remote_branches:
        print_error("No branches found in repository")
        sys.exit(1)
    
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
                # Strip origin/ prefix for display but keep for git commands
                display_name = branch
                if '/' in branch:
                    short_name = branch.split('/', 1)[1]
                    if short_name not in local_branch_names:
                        branches.append((branch, 'remote', False))
    
    if not branches:
        print_error("No selectable branches found")
        sys.exit(1)
    
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
    
    # Show native CLI dropdown
    try:
        questions = [
            inquirer.List('branch',
                         message=message,
                         choices=[choice[0] for choice in choices],
                         carousel=True)
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            print_error("Selection cancelled")
            sys.exit(1)
            
        # Find the branch name for the selected choice
        selected_text = answers['branch']
        for choice_text, branch in choices:
            if choice_text == selected_text:
                return branch
                
    except KeyboardInterrupt:
        print_error("Selection cancelled")
        sys.exit(1)

def explain_pr(pr_spec=None, force_select=False):
    """Handle pull request explanation"""
    
    # Check if gh is available
    if not shutil.which('gh'):
        print_error("GitHub CLI (gh) not available - PR explanation requires gh CLI")
        sys.exit(1)
    
    if force_select:
        # Show interactive selection
        pr_number = select_pr_interactive()
        diff_content = run_command(['gh', 'pr', 'diff', str(pr_number)])
    elif pr_spec and pr_spec != True:
        # Specific PR number provided
        try:
            pr_number = int(pr_spec)
            diff_content = run_command(['gh', 'pr', 'diff', str(pr_number)])
            if not diff_content:
                print_error(f"Could not get diff for PR #{pr_number}. Make sure the PR exists.")
                sys.exit(1)
        except ValueError:
            print_error(f"Invalid PR number: '{pr_spec}'. Please provide a valid number.")
            sys.exit(1)
    else:
        # Try current PR, fallback to selection if not in PR branch
        current_pr_check = run_command(['gh', 'pr', 'view'])
        
        if current_pr_check is None or current_pr_check == "":
            # Not in a PR branch, show interactive selection
            pr_number = select_pr_interactive()
            diff_content = run_command(['gh', 'pr', 'diff', str(pr_number)])
        else:
            # In a PR branch, use current PR
            diff_content = run_command(['gh', 'pr', 'diff'])
    
    if not diff_content or diff_content == "":
        print_error("Could not get PR diff or PR has no changes")
        sys.exit(1)

    from .prompts import get_prompt_for_verbosity, EXPLAIN_PR_BP
    config = load_config()
    verbosity = config.get('verbosity', 'balanced')
    prompt = get_prompt_for_verbosity(EXPLAIN_PR_BP(pr_spec), verbosity)
    
    return prompt, diff_content

def explain_commit(ref='HEAD', force_select=False):
    """Handle commit explanation"""

    # If no ref specified or force select, show interactive selection
    if ref == 'HEAD' and force_select:
        ref = select_commit_interactive()
    elif ref != 'HEAD':
        # Check if the provided commit exists
        if run_command(['git', 'cat-file', '-e', ref]) is None:
            print_error(f"Could not find commit '{ref}'. Please provide a valid commit SHA, tag, or branch.")
            # Offer interactive selection as fallback
            from .styles import print_info
            print_info("Would you like to select from recent commits instead?")
            try:
                response = input("Select from recent commits? (y/N): ").strip().lower()
                if response == 'y':
                    ref = select_commit_interactive()
                else:
                    sys.exit(1)
            except (KeyboardInterrupt, EOFError):
                sys.exit(1)

    from .prompts import get_prompt_for_verbosity, EXPLAIN_COMMIT_BP
    config = load_config()
    verbosity = config.get('verbosity', 'balanced')
    prompt = get_prompt_for_verbosity(EXPLAIN_COMMIT_BP(ref), verbosity)
    
    diff_content = run_command(['git', 'show', ref])
    if not diff_content:
        print_error("Could not get commit diff")
        sys.exit(1)
    
    return prompt, diff_content

def explain_diff(ref):
    """Handle diff between current repo state and a commit"""
    if run_command(['git', 'cat-file', '-e', ref]) is None:
        print_error(f"Could not find commit '{ref}'. Please provide a valid commit SHA, tag, or branch.")
        sys.exit(1)

    # Apply verbosity setting
    from .prompts import get_prompt_for_verbosity, EXPLAIN_DIFF_BP
    config = load_config()
    verbosity = config.get('verbosity', 'balanced')
    prompt = get_prompt_for_verbosity(EXPLAIN_DIFF_BP(ref), verbosity)
    
    diff_content = run_command(['git', 'diff', ref])
    if not diff_content:
        print_error(f"No differences found between current state and commit '{ref}'")
        sys.exit(1)
    
    return prompt, diff_content

def explain_branch_diff(branch_spec, force_select=False, file_patterns=None):
    """Handle diff between branches"""
    
    # Parse branch specification
    if '..' in branch_spec:
        # Format: branch1..branch2
        branches = branch_spec.split('..', 1)
        if len(branches) != 2 or not branches[0] or not branches[1]:
            print_error("Invalid branch range format. Use: branch1..branch2")
            sys.exit(1)
        from_branch, to_branch = branches[0].strip(), branches[1].strip()
        comparison_type = "range"
    elif force_select:
        # Interactive selection of two branches
        from_branch = select_branch_interactive("Select first branch (FROM)", include_current=True)
        to_branch = select_branch_interactive("Select second branch (TO)", include_current=True)
        comparison_type = "range"
    elif branch_spec == "HEAD" or not branch_spec:
        # Default to comparing current branch with main/master
        current_branch = run_command(['git', 'branch', '--show-current'])
        if not current_branch:
            print_error("Not on any branch")
            sys.exit(1)
        
        # Try to find main branch (main, master, develop)
        main_candidates = ['main', 'master', 'develop']
        main_branch = None
        for candidate in main_candidates:
            if run_command(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{candidate}']) is not None:
                main_branch = candidate
                break
        
        if not main_branch:
            # If no main branch found, show interactive selection
            main_branch = select_branch_interactive("Select base branch to compare against", include_current=False)
        
        from_branch = main_branch
        to_branch = current_branch
        comparison_type = "current_vs_main"
    else:
        # Single branch vs current working state
        from_branch = branch_spec
        to_branch = None  # Working directory
        comparison_type = "branch_vs_working"
    
    # Validate branches exist
    if comparison_type != "branch_vs_working":
        for branch in [from_branch, to_branch]:
            # Check if it's a local branch, remote branch, or commit
            if (run_command(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{branch}']) is None and
                run_command(['git', 'show-ref', '--verify', '--quiet', f'refs/remotes/{branch}']) is None and
                run_command(['git', 'cat-file', '-e', branch]) is None):
                print_error(f"Could not find branch or commit '{branch}'")
                sys.exit(1)
    else:
        # Just validate the from_branch for working directory comparison
        if (run_command(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{from_branch}']) is None and
            run_command(['git', 'show-ref', '--verify', '--quiet', f'refs/remotes/{from_branch}']) is None and
            run_command(['git', 'cat-file', '-e', from_branch]) is None):
            print_error(f"Could not find branch or commit '{from_branch}'")
            sys.exit(1)
    
    # Build git diff command
    git_cmd = ['git', 'diff']
    
    # Add file patterns if specified
    if file_patterns:
        git_cmd.extend(['--'])
        git_cmd.extend(file_patterns)
    
    # Determine diff range and create appropriate prompt
    from .prompts import EXPLAIN_BRANCH_BP, EXPLAIN_BRANCH_CURRENT_VS_MAIN_BP, EXPLAIN_BRANCH_CURRENT_VS_WORKING_BP
    if comparison_type == "range":
        git_cmd.insert(2, f"{from_branch}..{to_branch}")
        base_prompt = EXPLAIN_BRANCH_BP(from_branch, to_branch)
    elif comparison_type == "current_vs_main":
        git_cmd.insert(2, f"{from_branch}..{to_branch}")
        base_prompt = EXPLAIN_BRANCH_CURRENT_VS_MAIN_BP(from_branch, to_branch)
    else:  # branch_vs_working
        git_cmd.insert(2, from_branch)
        base_prompt = EXPLAIN_BRANCH_CURRENT_VS_WORKING_BP(from_branch, to_branch)
    
    # Get the diff
    diff_content = run_command(git_cmd)
    if not diff_content:
        if comparison_type == "range":
            print_error(f"No differences found between '{from_branch}' and '{to_branch}'")
        elif comparison_type == "current_vs_main":
            print_error(f"No differences found between '{from_branch}' and current branch '{to_branch}'")
        else:
            print_error(f"No differences found between '{from_branch}' and working directory")
        sys.exit(1)
    
    # Apply verbosity setting
    from .prompts import get_prompt_for_verbosity
    config = load_config()
    verbosity = config.get('verbosity', 'balanced')
    prompt = get_prompt_for_verbosity(base_prompt, verbosity)

    return prompt, diff_content

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
    
    args = parser.parse_args()
    
    # Handle config commands first
    if args.config:
        show_interactive_config()
        return
    
    # Require one of the main commands
    if not any([args.pull_request is not None, args.commit is not None, args.diff is not None]):
        parser.error('Must specify one of: -P/--pull-request, -C/--commit, -D/--diff, or --config')
    
    check_dependencies()
    
    # Determine which command to run
    if args.pull_request is not None:
        prompt, diff_content = explain_pr(pr_spec=args.pull_request, force_select=args.select)
    elif args.diff is not None:
        # Use diff for both branch and commit comparisons
        branch_spec = args.diff
        
        # Handle backward compatibility: if branch_spec looks like a commit SHA (and not a branch range),
        # and it's not a valid branch name, fall back to old diff behavior
        if (branch_spec != 'HEAD' and '..' not in branch_spec and not args.select and
            len(branch_spec) >= 7 and all(c in '0123456789abcdef' for c in branch_spec[:7].lower())):
            # Looks like a commit SHA, check if it's actually a branch first
            if (run_command(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{branch_spec}']) is None and
                run_command(['git', 'show-ref', '--verify', '--quiet', f'refs/remotes/{branch_spec}']) is None):
                # Not a branch, use old diff behavior for backward compatibility
                print_warning(f"'{branch_spec}' looks like a commit SHA. Use -C for commit explanations. Treating as diff vs working directory.")
                prompt, diff_content = explain_diff(branch_spec)
            else:
                prompt, diff_content = explain_branch_diff(branch_spec, force_select=args.select, file_patterns=args.files)
        else:
            prompt, diff_content = explain_branch_diff(branch_spec, force_select=args.select, file_patterns=args.files)
    else:
        prompt, diff_content = explain_commit(args.commit, force_select=args.select)
    
    # Send to AI provider
    try:
        from .styles import create_spinner, print_result, print_clipboard_success, ask_copy_raw

        ai_command, provider = get_ai_command(prompt)

        with create_spinner("Getting explanation...", provider=provider):
            process = subprocess.run(
                ai_command,
                input=diff_content,
                check=True,
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                shell=True
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
        print_error(f"Failed to run {provider} command")
        sys.exit(1)
    except KeyboardInterrupt:
        print_error("Operation cancelled")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print_error("Operation cancelled")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)