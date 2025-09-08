#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / 'config.json'

DEFAULT_CONFIG = {
    'ai_provider': 'gemini',  # 'gemini' or 'claude'
    'verbosity': 'balanced',  # 'hyperdetailed', 'balanced', 'concise'
    'providers': {
        'gemini': {
            'command': ['gemini', '-p'],
            'description': 'Google Gemini CLI',
            'color': 'rgb(50,129,252)'
        },
        'claude': {
            'command': ['claude', '-c', '-p'],
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
    
    # Build menu options with current values
    current_provider = config.get('ai_provider', 'gemini')
    current_verbosity = config.get('verbosity', 'balanced')
    provider_color = config['providers'][current_provider].get('color', 'cyan')
    
    # Format choices to show current values directly
    choices = [
        f"Provider ({current_provider})",
        f"Verbosity ({current_verbosity})",
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
            choice_text = f"[{color}]{name}[/{color}] - {details['description']} (current)"
        else:
            choice_text = f"[{color}]{name}[/{color}] - {details['description']}"
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
        'concise': 'Short and sweet - minimal explanations',
        'balanced': 'Balanced - good detail without being overwhelming',
        'hyperdetailed': 'Hyperdetailed - comprehensive explanations with examples'
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
            # Extract the level name from the selection
            selected = answers['verbosity'].split(' - ')[0]
            config['verbosity'] = selected
            save_config(config)
            console.print(f"[green]✓[/green] Verbosity set to {selected}")
            
    except KeyboardInterrupt:
        pass

def get_prompt_for_verbosity(base_prompt, verbosity_level):
    """Adjust prompt based on verbosity level"""
    verbosity_modifiers = {
        'concise': " Keep the response concise and focused on the most important points.",
        'balanced': " Provide a well-balanced explanation with good detail.",
        'hyperdetailed': " Provide a comprehensive, detailed explanation with examples, context, and thorough analysis. Include technical details and reasoning behind changes."
    }
    
    modifier = verbosity_modifiers.get(verbosity_level, verbosity_modifiers['balanced'])
    return base_prompt + modifier