"""Prompt templates and construction for the explain CLI."""

from .config import load_config

# Base prompt with strict formatting rules
BP = """STRICT RULES (FOLLOW EXACTLY):
1. FORBIDDEN WORDS: Never use "diff", "patch", "delta", or "this PR/commit/branch shows". Just describe what changed.
2. FORBIDDEN OPENINGS: Never start with "Here's", "This is", "The following", "Based on", "Looking at", "I can see", "This refactors", "This updates". Start with the actual content.
3. FORMAT: Use bullet points for multiple changes. Be direct. No preamble.

"""

# Response style modifiers
RESPONSE_STYLES = {
    'code_review': "Write for a technical code review audience. Focus on implementation details, potential issues, and code quality. Be precise about what changed and why it matters technically.",
    'release_notes': "Write for end users and stakeholders. Focus on features and fixes in user-friendly terms. Avoid technical jargon. Emphasize what users can now do or what problems are fixed.",
    'nontechnical': "Write for non-technical readers. Explain changes in simple terms without code terminology. Focus on the purpose and impact rather than implementation.",
    'technical': "Write for developers. Include technical details, function names, and implementation specifics. Be precise about the technical approach.",
    'default': "Write for a general developer audience. Balance technical accuracy with clarity."
}

# Verbosity modifiers
VERBOSITY_MODIFIERS = {
    'concise': "Keep the response concise and focused on the most important points. ",
    'balanced': "Provide a well-balanced explanation with good detail. ",
    'hyperdetailed': "Provide a comprehensive, detailed explanation with thorough analysis. Include technical details and reasoning behind changes. "
}


def EXPLAIN_DIFF_BP(ref):
    return BP + f"Summarize the changes between the current repository state and commit '{ref}'. Describe what has changed and the main differences."


def EXPLAIN_COMMIT_BP(ref):
    return BP + "Summarize this commit. Describe the changes and the motivation."


def EXPLAIN_PR_BP(ref):
    return BP + "Explain this pull request for a GitHub description. Format as Markdown with 'Summary' and 'Changes' sections."


def EXPLAIN_BRANCH_BP(from_branch, to_branch):
    return BP + f"Summarize the changes between branch '{from_branch}' and branch '{to_branch}'. Describe what has changed and the main differences."


def EXPLAIN_BRANCH_CURRENT_VS_MAIN_BP(from_branch, to_branch):
    return BP + f"Summarize the changes between the base branch '{from_branch}' and the current branch '{to_branch}'. Describe what has changed and the main differences."


def EXPLAIN_BRANCH_CURRENT_VS_WORKING_BP(from_branch, to_branch):
    return BP + f"Summarize the changes between branch '{from_branch}' and the current working directory state. Describe what has changed and the main differences."


def get_prompt_for_verbosity(base_prompt, verbosity):
    """Adjust prompt based on verbosity level (deprecated - use build_prompt instead)"""
    modifier = VERBOSITY_MODIFIERS.get(verbosity, VERBOSITY_MODIFIERS['balanced'])
    return modifier + base_prompt


def build_prompt(base_prompt, verbosity_override=None, style_override=None):
    """
    Build a complete prompt with verbosity and response style settings.

    Args:
        base_prompt: The base prompt from one of the EXPLAIN_*_BP functions
        verbosity_override: Optional verbosity level to use instead of config
        style_override: Optional response style to use instead of config

    Returns:
        Complete prompt string with all modifiers applied
    """
    config = load_config()
    verbosity = verbosity_override or config.get('verbosity', 'balanced')
    response_style = style_override or config.get('response_style', 'default')

    verbosity_modifier = VERBOSITY_MODIFIERS.get(verbosity, VERBOSITY_MODIFIERS['balanced'])
    style_modifier = RESPONSE_STYLES.get(response_style, RESPONSE_STYLES['default'])

    return f"{verbosity_modifier}{style_modifier}\n\n{base_prompt}"
