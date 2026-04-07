status: in_progress
phase: 1
feature: VS integration into 8 LangGraph agents (Wave 1) — Needs Assessment, Research, Clinical Practice, Learning Objectives, Curriculum Design, Research Protocol, Marketing Plan, Grant Writer
approach: Approach B (Two Waves) — Wave 1 wires VS into all agents + adds metrics. Wave 2 (separate /ship) builds Team Roster UI.
complexity: complex
tdd: no

## Spec
- Add vs_generate/vs_select to 36 primary generation nodes across 8 agents
- Follow gap_analysis_agent pattern: VS wraps primary generation, graceful fallback
- Grant Writer passes model="opus" through VS client
- Each agent state gets vs_distribution + vs_used fields
- Orchestrator collects VS distributions from all agents
- VS engine gets new metrics: spread, selection_delta per node/agent/phase
- Not in scope: Team Roster UI (Wave 2)

## Acceptance Criteria
- All 8 agents call VS on primary generation nodes
- Graceful fallback when VS engine is down
- VS metrics exposed at /metrics on VS engine
- No regression in agent output quality
- Orchestrator passes VS distributions through

## Nodes targeted per agent
- Needs Assessment (5): create_character, generate_cold_open, generate_disease_overview, generate_treatment_options, generate_practice_gaps
- Research (6): research_epidemiology, research_economic_burden, research_treatment_landscape, research_guidelines, research_market_intelligence, synthesize_research
- Clinical Practice (4): analyze_standard_of_care, analyze_real_world_practice, identify_barriers, analyze_specialty_perspectives
- Learning Objectives (3): draft_level_5_objectives, draft_level_4_objectives, draft_level_3_objectives
- Curriculum Design (5): design_format, design_content_outline, design_cases, specify_faculty, write_innovation_section
- Research Protocol (4): define_study_objectives, design_study, specify_outcomes, develop_statistical_plan
- Marketing Plan (3): develop_audience_profile, craft_key_messages, develop_channel_strategy
- Grant Writer (6): draft_cover_letter, draft_executive_summary, create_faculty_section, create_budget_section, draft_org_qualifications, draft_independence
