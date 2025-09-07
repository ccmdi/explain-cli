#!/usr/bin/env python3
import argparse
import subprocess
import sys
import shutil
import pyperclip
import inquirer
from .config import get_ai_command, set_provider, show_config, load_config
from .styles import print_info, print_success, print_error, print_warning, print_provider, print_result, print_config, print_clipboard_success, create_spinner, ask_copy_raw

CONFIG = load_config()

def check_dependencies():
    """Check if required CLIs are available"""
    current_provider = CONFIG.get('ai_provider')
    for cmd in ['gh', CONFIG.get('providers').get(current_provider).get('command')[0]]:
        if not shutil.which(cmd):
            print_error(f"'{cmd}' CLI not found in PATH")
            sys.exit(1)
    
    try:
        import pyperclip
    except ImportError:
        print_error("pyperclip not installed. Install with: pip install pyperclip")
        sys.exit(1)

def run_command(cmd, shell=False):
    """Run command and return output, handle errors gracefully"""
    try:
        result = subprocess.run(
            cmd if isinstance(cmd, list) else cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            errors='replace',  # Replace problematic chars instead of failing
        )
        return result.stdout.strip() if result.stdout else ""
    except subprocess.CalledProcessError as e:
        return None

def select_pr_interactive():
    """Show PR list and let user select one using a native CLI dropdown"""
    
    # Get PR list
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
    
    # Create choices for the dropdown menu
    choices = []
    for pr in prs:
        state_indicator = "🟢" if pr['state'] == 'OPEN' else "🔴" if pr['state'] == 'CLOSED' else "🟣"
        choice_text = f"#{pr['number']}: {pr['title']} (@{pr['author']['login']}) {state_indicator}"
        choices.append((choice_text, pr['number']))
    
    # Show native CLI dropdown
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
        # print("\nSelection cancelled", file=sys.stderr)
        sys.exit(1)

def explain_pr(force_select=False):
    """Handle pull request explanation"""
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
    
    prompt = """Provide a concise explanation for a pull request suitable for a GitHub description, based on the following diff. Format it as Markdown with 'Summary' and 'Key Changes' sections. Here is the diff:"""
    
    return prompt, diff_content

def explain_commit(ref='HEAD'):
    """Handle commit explanation"""
    # Check if commit exists
    if run_command(['git', 'cat-file', '-e', ref]) is None:
        print_error(f"Could not find commit '{ref}'. Please provide a valid commit SHA, tag, or branch.")
        sys.exit(1)
    
    prompt = """Provide a concise summary for a commit message based on the following diff. Describe the key changes and the motivation. Here is the diff:"""
    
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
    
    prompt = f"""Provide a concise summary of the changes between the current repository state and commit '{ref}'. Describe what has changed and the key differences. Here is the diff:"""
    
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
    group.add_argument('--config', action='store_true', help='Show current configuration')
    group.add_argument('--set-provider', metavar='PROVIDER', help='Set AI provider (gemini or claude)')
    
    # Options
    parser.add_argument('-c', '--clipboard', action='store_true', help='Copy result to clipboard instead of printing to stdout')
    parser.add_argument('-s', '--select', action='store_true', help='Force interactive PR selection (only works with -P)')
    
    args = parser.parse_args()
    
    # Handle config commands first
    if args.config:
        config = load_config()
        print_config(config)
        return
    
    if args.set_provider:
        if set_provider(args.set_provider):
            print_success(f"Provider set to {args.set_provider}")
        return
    
    # Require one of the main commands
    if not any([args.pull_request, args.commit is not None, args.diff]):
        parser.error('Must specify one of: -P/--pull-request, -C/--commit, -D/--diff, --config, or --set-provider')
    
    check_dependencies()
    
    if args.pull_request:
        prompt, diff_content = explain_pr(force_select=args.select)
    elif args.diff:
        prompt, diff_content = explain_diff(args.diff)
    else:
        prompt, diff_content = explain_commit(args.commit)
    
    # Send to AI provider
    try:
        ai_command, provider = get_ai_command(prompt)
        
        with create_spinner(f"Getting explanation from {provider}..."):
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
            # Ask if user wants to copy raw markdown
            ask_copy_raw(result)
            
    except subprocess.CalledProcessError:
        print_error(f"Failed to run {provider} command")
        sys.exit(1)

if __name__ == '__main__':
    main()