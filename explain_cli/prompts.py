BP = """* All descriptions are for code review. Focus on specific changes and not broad intent.* NEVER mention the context of the description, e.g NEVER SAY "based on the diff...", "based on the commit...", "this diff...", etc. NEVER EVEN SAY THE WORD "DIFF". Always just describe. THAT'S IT. * Try and stick to bullet points if there are more than a few changes."""

def EXPLAIN_DIFF_BP(ref): 
    return BP + f"""Provide a summary of the changes between the current repository state and commit '{ref}'. Describe what has changed and the main differences. Here is the diff:"""

def EXPLAIN_COMMIT_BP(ref):
    return BP + f"""Provide a summary for a commit message based on the following diff. Describe the changes and the motivation. Here is the diff:"""

def EXPLAIN_PR_BP(ref):
    return BP + f"""Provide an explanation for a pull request suitable for a GitHub description, based on the following diff. Format it as Markdown with 'Summary' and 'Changes' sections. Here is the diff:"""

def EXPLAIN_BRANCH_BP(from_branch, to_branch):
    return BP + f"""Provide a summary of the changes between branch '{from_branch}' and branch '{to_branch}'. Describe what has changed and the main differences. Here is the diff:"""

def EXPLAIN_BRANCH_CURRENT_VS_MAIN_BP(from_branch, to_branch):
    return BP + f"""Provide a summary of the changes between the base branch '{from_branch}' and the current branch '{to_branch}'. Describe what has changed and the main differences. Here is the diff:"""

def EXPLAIN_BRANCH_CURRENT_VS_WORKING_BP(from_branch, to_branch):
    return BP + f"""Provide a summary of the changes between branch '{from_branch}' and the current working directory state. Describe what has changed and the main differences. Here is the diff:"""

def get_prompt_for_verbosity(base_prompt, verbosity):
    """Adjust prompt based on verbosity level"""
    verbosity_modifiers = {
        'concise': " Keep the response concise and focused on the most important points.",
        'balanced': " Provide a well-balanced explanation with good detail.",
        'hyperdetailed': " Provide a comprehensive, detailed explanation with examples, context, and thorough analysis. Include technical details and reasoning behind changes."
    }
    
    modifier = verbosity_modifiers.get(verbosity, verbosity_modifiers['balanced'])
    return modifier + base_prompt