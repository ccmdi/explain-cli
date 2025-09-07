#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / 'config.json'

DEFAULT_CONFIG = {
    'ai_provider': 'gemini',  # 'gemini' or 'claude'
    'providers': {
        'gemini': {
            'command': ['gemini', '-p'],
            'description': 'Google Gemini CLI'
        },
        'claude': {
            'command': ['claude', '-c', '-p'],
            'description': 'Claude Code'
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

def show_config():
    """Display current configuration"""
    config = load_config()
    current_provider = config.get('ai_provider', 'gemini')
    
    print("Current configuration:")
    print("  Available providers:")
    for name, details in config['providers'].items():
        active = "* " if name == current_provider else "  "
        print(f"    {active}{name}: {details['description']} ({' '.join(details['command'][:-1])})")
    # print(f"  Config file: {CONFIG_FILE}")