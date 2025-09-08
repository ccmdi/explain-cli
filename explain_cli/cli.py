#!/usr/bin/env python3
import argparse
import subprocess
import sys
import shutil
import pyperclip
import inquirer
from .config import get_ai_command, show_interactive_config, load_config, get_prompt_for_verbosity
from .styles import print_info, print_success, print_error, print_warning, print_provider, print_result, print_config, print_clipboard_success, create_spinner, ask_copy_raw

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

def explain_pr(force_select=False):
    """Handle pull request explanation"""
    
    # Check if gh is available
    if not shutil.which('gh'):
        print_error("GitHub CLI (gh) not available - PR explanation requires gh CLI")
        sys.exit(1)
    
    # Check if we're in a PR branch
    current_pr_check = run_command(['gh', 'pr', 'view'])
    
    if force_select or current_pr_check is None or current_pr_check == "":
        # Show interactive selection (either forced or not in a PR branch)
        pr_number = select_pr_interactive()
        diff_content = run_command(['gh', 'pr', 'diff', str(pr_number)])
    else:
        # In a PR branch, use current PR
        diff_content = run_command(['gh', 'pr', 'diff'])
    
    if not diff_content or diff_content == "":
        print_error("Could not get PR diff or PR has no changes")
        sys.exit(1)
    
    base_prompt = """Provide an explanation for a pull request suitable for a GitHub description, based on the following diff. Format it as Markdown with 'Summary' and 'Changes' sections. Be specific and don't describe broad intent; the description is for code review. Here is the diff:"""
    
    # Apply verbosity setting
    config = load_config()
    verbosity = config.get('verbosity', 'balanced')
    prompt = get_prompt_for_verbosity(base_prompt, verbosity)
    
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
            print_info("Would you like to select from recent commits instead?")
            try:
                response = input("Select from recent commits? (y/N): ").strip().lower()
                if response == 'y':
                    ref = select_commit_interactive()
                else:
                    sys.exit(1)
            except (KeyboardInterrupt, EOFError):
                sys.exit(1)
    
    base_prompt = """Provide a summary for a commit message based on the following diff. Describe the changes and the motivation. Be specific and don't describe broad intent; the description is for code review. Here is the diff:"""
    
    # Apply verbosity setting
    config = load_config()
    verbosity = config.get('verbosity', 'balanced')
    prompt = get_prompt_for_verbosity(base_prompt, verbosity)
    
    diff_content = run_command(['git', 'show', ref])
    if not diff_content:
        print_error("Could not get commit diff")
        sys.exit(1)
    
    return prompt, diff_content

def explain_diff(ref):
    """Handle diff between current repo state and a commit"""
    # Check if commit exists
    if run_command(['git', 'cat-file', '-e', ref]) is None:
        print_error(f"Could not find commit '{ref}'. Please provide a valid commit SHA, tag, or branch.")
        sys.exit(1)
    
    base_prompt = f"""Provide a summary of the changes between the current repository state and commit '{ref}'. Describe what has changed and the main differences. Be specific and don't describe broad intent; the description is for code review. Here is the diff:"""
    
    # Apply verbosity setting
    config = load_config()
    verbosity = config.get('verbosity', 'balanced')
    prompt = get_prompt_for_verbosity(base_prompt, verbosity)
    
    diff_content = run_command(['git', 'diff', ref])
    if not diff_content:
        print_error(f"No differences found between current state and commit '{ref}'")
        sys.exit(1)
    
    return prompt, diff_content

def main():
    parser = argparse.ArgumentParser(description='Explain Git commits or GitHub PRs using AI')
    
    # Main command group
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('-P', '--pull-request', action='store_true', help='Explain current pull request (or select interactively with --select)')
    group.add_argument('-C', '--commit', nargs='?', const='HEAD', help='Explain commit (defaults to HEAD)')
    group.add_argument('-D', '--diff', metavar='COMMIT', help='Explain diff between current repo state and specified commit')
    
    # Config commands
    group.add_argument('--config', action='store_true', help='Open interactive configuration menu')
    
    # Options
    parser.add_argument('-c', '--clipboard', action='store_true', help='Copy result to clipboard instead of printing to stdout')
    parser.add_argument('-s', '--select', action='store_true', help='Force interactive selection (works with -P for PRs, -C for commits)')
    
    args = parser.parse_args()
    
    # Handle config commands first
    if args.config:
        show_interactive_config()
        return
    
    # Require one of the main commands
    if not any([args.pull_request, args.commit is not None, args.diff]):
        parser.error('Must specify one of: -P/--pull-request, -C/--commit, -D/--diff, or --config')
    
    check_dependencies()
    
    if args.pull_request:
        prompt, diff_content = explain_pr(force_select=args.select)
    elif args.diff:
        prompt, diff_content = explain_diff(args.diff)
    else:
        prompt, diff_content = explain_commit(args.commit, force_select=args.select)
    
    # Send to AI provider
    try:
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