"""Versioned prompt modules — one per agent (item 21 / llm-prompts.md).

Agent modules import named constants from here; prompt literals never
live inline in agent code. Prompt changes ship as diffs to these files.
"""
