"""Versioned prompt modules for this agent.

One module per agent, named after the agent without the `_agent` suffix, each
exporting UPPERCASE string constants. Agent code imports these constants; it
never inlines prompt literals (see .claude/rules/llm-prompts.md).
"""
