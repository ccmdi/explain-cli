#!/usr/bin/env python3
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
import sys

console = Console(stderr=True)

def print_info(message):
    """Print info message with blue styling"""
    console.print(f"[blue]ℹ[/blue] {message}")

def print_success(message):
    """Print success message with green styling"""
    console.print(f"[green]✓[/green] {message}")

def print_error(message):
    """Print error message with red styling"""
    console.print(f"[red]✗[/red] {message}")

def print_warning(message):
    """Print warning message with yellow styling"""
    console.print(f"[yellow]⚠[/yellow] {message}")

def print_provider(provider):
    """Print which AI provider is being used"""
    console.print(f"[dim]Using {provider} AI provider...[/dim]")

def print_result(content, is_markdown=True):
    """Print the AI result with nice formatting"""
    if is_markdown:
        # Rich can render markdown beautifully
        from rich.markdown import Markdown
        md = Markdown(content)
        console.print(md)
    else:
        # For plain text, just print normally to stdout (not stderr)
        print(content)

def print_config(config):
    """Print configuration with nice formatting"""
    current_provider = config.get('ai_provider', 'gemini')
    
    console.print("\n[bold]Configuration[/bold]")
    # console.print(f"  [green]Active provider:[/green] {current_provider}")
    console.print("  [blue]Available providers:[/blue]")
    
    for name, details in config['providers'].items():
        if name == current_provider:
            console.print(f"    [green]* {name}:[/green] {details['description']} ([dim]{' '.join(details['command'][:-1])}[/dim])")
        else:
            console.print(f"    [dim]  {name}:[/dim] {details['description']} ([dim]{' '.join(details['command'][:-1])}[/dim])")

def print_clipboard_success():
    """Print clipboard copy success message"""
    console.print("[green]✓[/green] Result copied to clipboard!")

def create_spinner(text, provider=None):
    """Create a spinner for long-running operations"""
    from rich.spinner import Spinner
    if provider:
        # Provider-specific colors with code-style formatting
        provider_colors = {
            'gemini': 'rgb(50,129,252)',
            'claude': 'rgb(217,119,87)',
            'default': 'cyan'
        }
        color = provider_colors.get(provider.lower(), provider_colors['default'])
        # Use code style (monospace, slightly highlighted) without visible backticks
        formatted_text = f"Getting explanation from [{color}]{provider}[/{color}]..."
        return console.status(f"[dim]{formatted_text}[/dim]", spinner="dots", spinner_style=color)
    else:
        return console.status(f"[dim]{text}[/dim]", spinner="dots")

def ask_copy_raw(content):
    """Ask user if they want to copy the raw markdown content"""
    try:
        console.print(f"\n[dim]Copy raw markdown to clipboard? (y/N):[/dim] ", end="")
        response = input().strip().lower()
        if response == 'y':
            import pyperclip
            pyperclip.copy(content)
            print_success("Raw markdown copied to clipboard!")
            return True
        return False
    except (KeyboardInterrupt, EOFError):
        console.print()
        return False