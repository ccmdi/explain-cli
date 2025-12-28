#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / 'config.json'

DEFAULT_CONFIG = {
    'ai_provider': 'gemini',  # 'gemini' or 'claude'
    'verbosity': 'balanced',  # 'hyperdetailed', 'balanced', 'concise'
    'response_style': 'default',  # 'code_review', 'release_notes', 'nontechnical', 'technical', 'default'
    'response_structure': '',  # User-defined response structure template (empty = no structure enforced)
    'providers': {
        'gemini': {
            'command': ['gemini', '-p'],
            'description': 'Google Gemini CLI',
            'color': 'rgb(50,129,252)'
        },
        'claude': {
            'command': ['claude', '-p'],
            'description': 'Claude Code',
            'color': 'rgb(217,119,87)'
        }
    }
}

def load_config():
    """Load configuration from file, create default if doesn't exist"""
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        # Merge with defaults to ensure all keys exist
        merged_config = DEFAULT_CONFIG.copy()
        merged_config.update(config)
        return merged_config
    except (json.JSONDecodeError, IOError):
        # Return default config if file is corrupted
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except IOError as e:
        print(f"Warning: Could not save config: {e}", file=sys.stderr)

def get_ai_command(prompt):
    """Get the AI command based on current configuration"""
    config = load_config()
    provider = config.get('ai_provider', 'gemini')
    
    if provider not in config['providers']:
        print(f"Error: Unknown provider '{provider}'. Available: {list(config['providers'].keys())}", file=sys.stderr)
        provider = 'gemini'  # Fallback to default
    
    command = config['providers'][provider]['command'].copy()
    command.append(prompt)
    return command, provider

def set_provider(provider_name):
    """Set the AI provider"""
    config = load_config()
    
    if provider_name not in config['providers']:
        print(f"Error: Unknown provider '{provider_name}'. Available: {list(config['providers'].keys())}")
        return False
    
    config['ai_provider'] = provider_name
    save_config(config)
    # print(f"AI provider set to: {provider_name} ({config['providers'][provider_name]['description']})")
    return True

def show_interactive_config():
    """Show interactive configuration menu"""
    import inquirer
    from rich.console import Console

    console = Console(stderr=True)
    config = load_config()

    current_provider = config.get('ai_provider', 'gemini')
    current_verbosity = config.get('verbosity', 'balanced')
    current_style = config.get('response_style', 'default')
    current_structure = config.get('response_structure', '')
    structure_status = 'custom' if current_structure else 'none'

    choices = [
        f"Provider ({current_provider})",
        f"Verbosity ({current_verbosity})",
        f"Response Style ({current_style})",
        f"Response Structure ({structure_status})",
        "Exit"
    ]

    try:
        questions = [
            inquirer.List('action',
                         message="Configuration",
                         choices=choices,
                         carousel=True)
        ]

        answers = inquirer.prompt(questions)
        if not answers or answers['action'] == 'Exit':
            return

        if answers['action'].startswith('Provider'):
            _configure_provider(config)
        elif answers['action'].startswith('Verbosity'):
            _configure_verbosity(config)
        elif answers['action'].startswith('Response Style'):
            _configure_response_style(config)
        elif answers['action'].startswith('Response Structure'):
            _configure_response_structure(config)

    except KeyboardInterrupt:
        return

def _configure_provider(config):
    """Configure AI provider"""
    import inquirer
    from rich.console import Console
    
    console = Console(stderr=True)
    current_provider = config.get('ai_provider', 'gemini')
    
    # Create provider choices with colors
    choices = []
    for name, details in config['providers'].items():
        color = details.get('color', 'cyan')
        if name == current_provider:
            choice_text = f"{name} - {details['description']} (current)"
        else:
            choice_text = f"{name} - {details['description']}"
        choices.append((choice_text, name))
    
    try:
        questions = [
            inquirer.List('provider',
                         message="Select AI provider",
                         choices=[choice[0] for choice in choices],
                         carousel=True)
        ]
        
        answers = inquirer.prompt(questions)
        if answers:
            # Find the provider name for the selected choice
            selected_text = answers['provider']
            for choice_text, provider_name in choices:
                if choice_text == selected_text:
                    config['ai_provider'] = provider_name
                    save_config(config)
                    console.print(f"[green]✓[/green] Provider set to {provider_name}")
                    break
                    
    except KeyboardInterrupt:
        pass

def _configure_verbosity(config):
    """Configure verbosity level"""
    import inquirer
    from rich.console import Console
    
    console = Console(stderr=True)
    current_verbosity = config.get('verbosity', 'balanced')
    
    verbosity_options = {
        'concise': 'Short and sweet',
        'balanced': 'Good detail without being overwhelming',
        'hyperdetailed': 'Comprehensive explanations'
    }
    
    choices = []
    for level, description in verbosity_options.items():
        if level == current_verbosity:
            choices.append(f"{level} - {description} (current)")
        else:
            choices.append(f"{level} - {description}")
    
    try:
        questions = [
            inquirer.List('verbosity',
                         message="Select verbosity level",
                         choices=choices,
                         carousel=True)
        ]

        answers = inquirer.prompt(questions)
        if answers:
            selected = answers['verbosity'].split(' - ')[0]
            config['verbosity'] = selected
            save_config(config)
            console.print(f"[green]✓[/green] Verbosity set to {selected}")

    except KeyboardInterrupt:
        pass


def _configure_response_style(config):
    """Configure response style for different audiences"""
    import inquirer
    from rich.console import Console

    console = Console(stderr=True)
    current_style = config.get('response_style', 'default')

    style_options = {
        'default': 'General developer audience',
        'code_review': 'Technical code review (implementation details)',
        'release_notes': 'End users and stakeholders (user-friendly)',
        'nontechnical': 'Non-technical readers (simple terms)',
        'technical': 'Developers (precise technical details)'
    }

    choices = []
    for style, description in style_options.items():
        if style == current_style:
            choices.append(f"{style} - {description} (current)")
        else:
            choices.append(f"{style} - {description}")

    try:
        questions = [
            inquirer.List('style',
                         message="Select response style",
                         choices=choices,
                         carousel=True)
        ]

        answers = inquirer.prompt(questions)
        if answers:
            selected = answers['style'].split(' - ')[0]
            config['response_style'] = selected
            save_config(config)
            console.print(f"[green]✓[/green] Response style set to {selected}")

    except KeyboardInterrupt:
        pass


def _configure_response_structure(config):
    """Configure response structure template"""
    import inquirer
    from rich.console import Console

    console = Console(stderr=True)
    current_structure = config.get('response_structure', '')

    if current_structure:
        console.print("\n[bold]Current structure:[/bold]")
        console.print(f"[dim]{current_structure}[/dim]")

    choices = [
        "Edit structure (opens editor)",
        "Clear structure (no enforced format)",
        "Cancel"
    ]

    try:
        questions = [
            inquirer.List('action',
                         message="Response structure",
                         choices=choices,
                         carousel=True)
        ]

        answers = inquirer.prompt(questions)
        if not answers or answers['action'] == 'Cancel':
            return

        if answers['action'].startswith('Clear'):
            config['response_structure'] = ''
            save_config(config)
            console.print("[green]✓[/green] Response structure cleared")
        elif answers['action'].startswith('Edit'):
            _edit_structure_in_editor(config, console)

    except KeyboardInterrupt:
        pass


def _edit_structure_in_editor(config, console):
    """Open editor for user to define response structure"""
    import tempfile
    import subprocess
    import shutil

    current_structure = config.get('response_structure', '')

    # Default template to show user
    default_template = """# Summary
<2 sentence summary of the changes>

# Changes
<Bullet point list of changes, with no bolded text, and short sentences describing what was changed>"""

    content_to_edit = current_structure if current_structure else default_template

    # Find available editor
    editor = os.environ.get('EDITOR') or os.environ.get('VISUAL')
    if not editor:
        for ed in ['code', 'nvim', 'vim', 'nano', 'notepad']:
            if shutil.which(ed):
                editor = ed
                break

    if not editor:
        console.print("[red]No editor found. Set EDITOR environment variable.[/red]")
        return

    # Create temp file with current structure
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Response Structure Template\n")
        f.write("# Delete all content to clear the structure.\n")
        f.write("# Lines starting with # at the top are instructions and will be stripped.\n")
        f.write("# Your template starts below:\n\n")
        f.write(content_to_edit)
        temp_path = f.name

    try:
        use_shell = os.name == 'nt'
        if 'code' in editor:
            subprocess.run([editor, '--wait', temp_path], check=True, shell=use_shell)
        else:
            subprocess.run([editor, temp_path], check=True, shell=use_shell)

        # Read back the edited content
        with open(temp_path, 'r') as f:
            edited = f.read()

        # Strip instruction comments at the top
        lines = edited.split('\n')
        content_lines = []
        started = False
        for line in lines:
            if not started and line.startswith('#') and not line.startswith('# Summary') and not line.startswith('# Changes') and not line.startswith('# TL;DR') and not line.startswith('# What') and not line.startswith('# Why') and not line.startswith('# How') and not line.startswith('# Details'):
                continue
            started = True
            content_lines.append(line)

        new_structure = '\n'.join(content_lines).strip()

        config['response_structure'] = new_structure
        save_config(config)

        if new_structure:
            console.print("[green]✓[/green] Response structure saved")
        else:
            console.print("[green]✓[/green] Response structure cleared")

    except subprocess.CalledProcessError:
        console.print("[red]Editor exited with error[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except:
            pass