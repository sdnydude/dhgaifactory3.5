/**
 * Static catalog of all 17 registered LangGraph graphs.
 * graphId values match exactly the keys in langgraph.json.
 */

export type AgentCategory = "content" | "recipe" | "qa" | "infra";

export interface AgentDeepDocs {
  executionFlow: string;
  qualityCriteria: string;
  errorHandling: string;
  inputSchema: string;
}

export interface AgentCatalogEntry {
  graphId: string;
  name: string;
  icon: string;
  description: string;
  category: AgentCategory;
  pipelineOrder: number;
  upstream: string[];
  downstream: string[];
  inputs: string[];
  outputs: string[];
  deepDocs: AgentDeepDocs;
}

export const AGENT_CATALOG: AgentCatalogEntry[] = [
  // =========================================================================
  // CONTENT AGENTS
  // =========================================================================
  {
    graphId: "research",
    name: "Research Agent",
    icon: "\uD83D\uDD2C", // microscope
    description: "Literature review, epidemiology, and market intelligence gathering with 30+ citations.",
    category: "content",
    pipelineOrder: 1,
    upstream: [],
    downstream: ["gap_analysis", "needs_assessment", "grant_writer"],
    inputs: ["therapeutic_area", "disease_state", "target_audience", "geographic_focus", "supporter_company", "known_gaps"],
    outputs: ["research_output"],
    deepDocs: {
      executionFlow:
        "1. Parse intake form for therapeutic area and disease state\n" +
        "2. Execute PubMed and Perplexity literature searches (30+ sources target)\n" +
        "3. Compile epidemiology data: prevalence, incidence, demographics, burden\n" +
        "4. Analyze economic burden: direct costs, indirect costs, healthcare utilization\n" +
        "5. Map treatment landscape: current therapies, pipeline agents, guideline evolution\n" +
        "6. Identify market context: competitor products, supporter product positioning\n" +
        "7. Synthesize evidence gaps and emerging research directions\n" +
        "8. Assemble structured research report with full citation list",
      qualityCriteria:
        "- Minimum 30 unique cited sources\n" +
        "- All epidemiology data includes recency (within 3 years preferred)\n" +
        "- Economic data cites specific dollar amounts with source attribution\n" +
        "- Treatment landscape covers both guideline-recommended and real-world use\n" +
        "- No unsupported claims; every statistic has a citation",
      errorHandling:
        "- PubMed API timeout: retry up to 3 times with exponential backoff\n" +
        "- Insufficient sources (<15): log warning, proceed with available data, flag in metadata\n" +
        "- Perplexity unavailable: fall back to PubMed-only search\n" +
        "- 5-minute total execution timeout with graceful partial output",
      inputSchema:
        "therapeutic_area: string (required) -- Primary research domain\n" +
        "disease_state: string (required) -- Specific condition\n" +
        "target_audience: string -- Specialty context for relevance filtering\n" +
        "geographic_focus: string -- Regional epidemiology selection\n" +
        "supporter_company: string -- Market intelligence focus\n" +
        "supporter_products: string[] -- Product landscape context\n" +
        "known_gaps: string[] -- Directed research areas\n" +
        "competitor_products: string[] -- Competitive landscape",
    },
  },
  {
    graphId: "clinical_practice",
    name: "Clinical Practice Agent",
    icon: "\uD83C\uDFE5", // hospital
    description: "Standard-of-care analysis, practice patterns, and barrier identification.",
    category: "content",
    pipelineOrder: 1,
    upstream: [],
    downstream: ["gap_analysis"],
    inputs: ["therapeutic_area", "disease_state", "target_audience", "practice_settings", "known_barriers"],
    outputs: ["clinical_output"],
    deepDocs: {
      executionFlow:
        "1. Analyze current clinical guidelines for the therapeutic area\n" +
        "2. Map standard-of-care diagnostic and treatment pathways\n" +
        "3. Identify real-world practice deviations from guidelines\n" +
        "4. Categorize barriers: knowledge, competence, performance, system-level\n" +
        "5. Quantify practice-guideline deltas with supporting data\n" +
        "6. Assess geographic and setting-based variations\n" +
        "7. Compile barrier impact analysis on patient outcomes",
      qualityCriteria:
        "- Clear separation of guideline-recommended vs actual practice\n" +
        "- Each barrier categorized using established taxonomy\n" +
        "- Practice deviations quantified (percentages, frequencies)\n" +
        "- Quality metrics include established measures and benchmarks\n" +
        "- Regional/setting variations documented when available",
      errorHandling:
        "- Guideline data not found: use most recent available, note currency in metadata\n" +
        "- Practice pattern data sparse: flag confidence level in output\n" +
        "- 5-minute execution timeout with partial output capture",
      inputSchema:
        "therapeutic_area: string (required)\n" +
        "disease_state: string (required)\n" +
        "target_audience: string\n" +
        "practice_settings: string[] -- Care environment context\n" +
        "geographic_focus: string\n" +
        "known_gaps: string[]\n" +
        "known_barriers: string[]",
    },
  },
  {
    graphId: "gap_analysis",
    name: "Gap Analysis Agent",
    icon: "\uD83D\uDD0D", // magnifying glass
    description: "Synthesizes research and clinical data into 5+ evidence-based, prioritized educational gaps.",
    category: "content",
    pipelineOrder: 2,
    upstream: ["research", "clinical_practice"],
    downstream: ["needs_assessment", "learning_objectives"],
    inputs: ["research_output", "clinical_output", "known_gaps", "educational_priorities"],
    outputs: ["gap_analysis_output"],
    deepDocs: {
      executionFlow:
        "1. Ingest research output (epidemiology, evidence, treatment landscape)\n" +
        "2. Ingest clinical practice output (practice patterns, barriers, deviations)\n" +
        "3. Cross-reference evidence with practice to identify disconnects\n" +
        "4. Generate minimum 5 prioritized educational gaps\n" +
        "5. Quantify each gap: guideline recommendation vs current practice delta\n" +
        "6. Categorize barriers per gap (knowledge, competence, performance, system)\n" +
        "7. Assess patient impact for each gap\n" +
        "8. Prioritize by addressability through education and impact severity",
      qualityCriteria:
        "- Minimum 5 distinct gaps identified\n" +
        "- Each gap has quantified practice-guideline delta\n" +
        "- Barrier categorization uses established taxonomy\n" +
        "- Patient impact stated with supporting evidence\n" +
        "- Priority ranking justified with clear rationale",
      errorHandling:
        "- Missing upstream output: cannot proceed, return error with missing dependency\n" +
        "- Fewer than 5 gaps identified: retry with broadened scope up to 3 times\n" +
        "- Insufficient quantification: flag gaps as qualitative-only in metadata",
      inputSchema:
        "research_output: object (required) -- Full research agent output\n" +
        "clinical_output: object (required) -- Full clinical practice output\n" +
        "known_gaps: string[] -- Pre-identified gaps from intake\n" +
        "educational_priorities: string[] -- Supporter priorities\n" +
        "outcome_goals: string[] -- Desired impact areas",
    },
  },
  {
    graphId: "needs_assessment",
    name: "Needs Assessment Agent",
    icon: "\uD83D\uDCDD", // memo
    description: "Flagship 3,100+ word narrative document with cold open framework and character thread.",
    category: "content",
    pipelineOrder: 3,
    upstream: ["gap_analysis", "research", "clinical_practice"],
    downstream: ["learning_objectives", "prose_quality"],
    inputs: ["gap_analysis_output", "research_output", "clinical_output", "therapeutic_area", "activity_title"],
    outputs: ["needs_assessment_output"],
    deepDocs: {
      executionFlow:
        "1. Receive prioritized gaps, research evidence, and clinical practice data\n" +
        "2. Construct cold open: create character (patient or clinician), humanizing detail, turn statement\n" +
        "3. Weave character thread through minimum 4 document appearances\n" +
        "4. Write 3,100+ word narrative integrating all gaps with evidence\n" +
        "5. Ensure prose density >= 80% (flowing prose vs lists/bullets)\n" +
        "6. Embed citations throughout from research output\n" +
        "7. Assemble complete document with section structure\n" +
        "8. Compute quality metrics: word count, prose density, citation count, character appearances",
      qualityCriteria:
        "- Minimum 3,100 words total\n" +
        "- Cold open: 50-100 words with character name, age, humanizing detail, turn statement\n" +
        "- Character thread: minimum 4 appearances across sections\n" +
        "- Prose density >= 80%\n" +
        "- All gaps from gap analysis represented\n" +
        "- Pharmaceutical grant reviewer-ready quality",
      errorHandling:
        "- Word count below 3,100: retry generation with explicit expansion instructions\n" +
        "- Prose density below 80%: re-write list-heavy sections as flowing paragraphs\n" +
        "- Character thread < 4 appearances: add character references in revision pass\n" +
        "- 5-minute timeout with checkpoint save",
      inputSchema:
        "gap_analysis_output: object (required) -- Prioritized gaps with evidence\n" +
        "research_output: object (required) -- Epidemiology, literature, market context\n" +
        "clinical_output: object (required) -- Practice patterns, barriers\n" +
        "therapeutic_area: string\n" +
        "disease_state: string\n" +
        "target_audience: string\n" +
        "activity_title: string\n" +
        "accreditation_types: string[]",
    },
  },
  {
    graphId: "learning_objectives",
    name: "Learning Objectives Agent",
    icon: "\uD83C\uDFAF", // target
    description: "6+ measurable objectives mapped to Moore's Expanded Outcomes Framework.",
    category: "content",
    pipelineOrder: 4,
    upstream: ["needs_assessment", "gap_analysis"],
    downstream: ["curriculum_design", "research_protocol", "marketing_plan"],
    inputs: ["needs_assessment_output", "gap_analysis_output", "target_audience", "educational_format"],
    outputs: ["learning_objectives_output"],
    deepDocs: {
      executionFlow:
        "1. Receive revised needs assessment and prioritized gaps\n" +
        "2. Apply Moore's Expanded Outcomes Framework taxonomy\n" +
        "3. Generate minimum 6 measurable learning objectives\n" +
        "4. Map each objective to a specific gap\n" +
        "5. Assign Moore level (3a-6) with appropriate action verbs\n" +
        "6. Define measurement methodology for each objective\n" +
        "7. Distribute objectives across Moore levels with rationale\n" +
        "8. Verify gap coverage is complete",
      qualityCriteria:
        "- Minimum 6 objectives\n" +
        "- Each objective traces to an identified gap\n" +
        "- Moore level specified with correct action verb taxonomy\n" +
        "- Measurement methodology defined and practical\n" +
        "- Level distribution includes higher-order outcomes (Level 4+)",
      errorHandling:
        "- Fewer than 6 objectives: expand from highest-priority gaps\n" +
        "- Missing gap mapping: reject and retry with explicit gap-objective alignment\n" +
        "- Invalid Moore level verbs: auto-correct from framework verb list",
      inputSchema:
        "needs_assessment_output: object (required)\n" +
        "gap_analysis_output: object (required)\n" +
        "target_audience: string\n" +
        "educational_format: string\n" +
        "outcome_goals: string[]\n" +
        "moore_level_target: string -- Target outcome level",
    },
  },
  {
    graphId: "curriculum_design",
    name: "Curriculum Design Agent",
    icon: "\uD83D\uDCDA", // books
    description: "Educational design specification with format, structure, and innovation rationale.",
    category: "content",
    pipelineOrder: 5,
    upstream: ["learning_objectives", "gap_analysis", "needs_assessment"],
    downstream: ["grant_writer"],
    inputs: ["learning_objectives_output", "gap_analysis_output", "target_audience", "educational_format", "duration"],
    outputs: ["curriculum_output"],
    deepDocs: {
      executionFlow:
        "1. Review learning objectives with Moore levels and measurement\n" +
        "2. Select primary educational format and modality\n" +
        "3. Design session structure with time allocation\n" +
        "4. Specify instructional methods aligned to objective levels\n" +
        "5. Define faculty requirements and specifications\n" +
        "6. Create assessment strategy mapped to objectives\n" +
        "7. Write innovation section justifying educational approach\n" +
        "8. Compile complete curriculum specification",
      qualityCriteria:
        "- Format selection justified with pedagogical rationale\n" +
        "- Every learning objective has a corresponding instructional method\n" +
        "- Assessment strategy maps to measurement methodology\n" +
        "- Innovation section demonstrates differentiation from standard CME\n" +
        "- Faculty specs include specialty, experience level, and role",
      errorHandling:
        "- Objective-method mismatch: realign and regenerate affected sections\n" +
        "- Duration constraints violated: rebalance session structure\n" +
        "- Innovation section too generic: retry with specific pedagogical references",
      inputSchema:
        "learning_objectives_output: object (required)\n" +
        "gap_analysis_output: object (required)\n" +
        "needs_assessment_output: object\n" +
        "target_audience: string\n" +
        "practice_settings: string[]\n" +
        "educational_format: string\n" +
        "innovation_elements: string[]\n" +
        "duration: string\n" +
        "modality: string",
    },
  },
  {
    graphId: "research_protocol",
    name: "Research Protocol Agent",
    icon: "\uD83E\uDDEA", // test tube
    description: "IRB-ready educational outcomes research protocol with study design and endpoints.",
    category: "content",
    pipelineOrder: 5,
    upstream: ["learning_objectives", "gap_analysis", "curriculum_design"],
    downstream: ["grant_writer"],
    inputs: ["learning_objectives_output", "gap_analysis_output", "target_audience", "estimated_reach"],
    outputs: ["protocol_output"],
    deepDocs: {
      executionFlow:
        "1. Define study type as educational outcomes research\n" +
        "2. Establish primary and secondary endpoints from learning objectives\n" +
        "3. Design study methodology (pre-post, longitudinal, comparative)\n" +
        "4. Define study population from target audience\n" +
        "5. Calculate sample size from estimated reach\n" +
        "6. Create data collection instruments (surveys, knowledge assessments)\n" +
        "7. Define analysis plan with statistical methods\n" +
        "8. Write protocol narrative suitable for IRB review",
      qualityCriteria:
        "- Primary endpoint clearly defined and measurable\n" +
        "- Study design appropriate for educational intervention\n" +
        "- Sample size justified with rationale\n" +
        "- Data collection instruments described in detail\n" +
        "- Analysis plan includes specific statistical tests",
      errorHandling:
        "- Missing learning objectives: cannot proceed, return dependency error\n" +
        "- Sample size too small for significance: flag in protocol with limitations\n" +
        "- Endpoint measurement infeasible: propose alternative measurement approach",
      inputSchema:
        "learning_objectives_output: object (required)\n" +
        "gap_analysis_output: object (required)\n" +
        "curriculum_output: object\n" +
        "target_audience: string\n" +
        "estimated_reach: number\n" +
        "outcome_goals: string[]\n" +
        "moore_level_target: string\n" +
        "measurement_preferences: string[]",
    },
  },
  {
    graphId: "marketing_plan",
    name: "Marketing Plan Agent",
    icon: "\uD83D\uDCE3", // megaphone
    description: "Multi-channel audience generation strategy with budget allocation and timeline.",
    category: "content",
    pipelineOrder: 5,
    upstream: ["learning_objectives", "needs_assessment"],
    downstream: ["grant_writer"],
    inputs: ["learning_objectives_output", "needs_assessment_output", "target_audience", "marketing_budget"],
    outputs: ["marketing_output"],
    deepDocs: {
      executionFlow:
        "1. Define target audience profile from intake and upstream data\n" +
        "2. Estimate audience universe size by specialty and geography\n" +
        "3. Select marketing channels (digital, email, social, society, KOL)\n" +
        "4. Allocate budget across channels with ROI projection\n" +
        "5. Create channel-specific strategies and messaging\n" +
        "6. Build timeline from launch date backward\n" +
        "7. Define KPIs and measurement for each channel\n" +
        "8. Compile comprehensive marketing plan document",
      qualityCriteria:
        "- Channel selection justified with audience reach data\n" +
        "- Budget allocation totals match marketing_budget input\n" +
        "- Projected reach is realistic and supported by channel benchmarks\n" +
        "- Timeline includes specific milestones and deadlines\n" +
        "- KPIs defined for each channel with measurement method",
      errorHandling:
        "- Budget not specified: use industry benchmarks, flag assumption\n" +
        "- Audience universe too small: recommend broader targeting, document rationale\n" +
        "- Channel data unavailable: use conservative reach estimates",
      inputSchema:
        "learning_objectives_output: object\n" +
        "needs_assessment_output: object\n" +
        "target_audience: string (required)\n" +
        "practice_settings: string[]\n" +
        "geographic_focus: string\n" +
        "estimated_reach: number\n" +
        "marketing_budget: number\n" +
        "marketing_channels: string[]\n" +
        "launch_date: string",
    },
  },
  {
    graphId: "grant_writer",
    name: "Grant Writer Agent",
    icon: "\uD83D\uDCBC", // briefcase
    description: "Assembles all upstream outputs into a cohesive, submission-ready grant package.",
    category: "content",
    pipelineOrder: 6,
    upstream: ["needs_assessment", "learning_objectives", "curriculum_design", "research_protocol", "marketing_plan"],
    downstream: ["prose_quality"],
    inputs: ["needs_assessment_output", "learning_objectives_output", "curriculum_output", "protocol_output", "marketing_output"],
    outputs: ["grant_package_output"],
    deepDocs: {
      executionFlow:
        "1. Collect all upstream agent outputs\n" +
        "2. Verify completeness: all required sections present\n" +
        "3. Write cover letter with recipient, date, signatory\n" +
        "4. Assemble executive summary from across all sections\n" +
        "5. Integrate needs assessment, objectives, curriculum, protocol, marketing\n" +
        "6. Ensure cross-section consistency (terminology, data, narrative)\n" +
        "7. Add budget breakdown and organizational credentials\n" +
        "8. Produce final formatted grant package document",
      qualityCriteria:
        "- All upstream sections included without truncation\n" +
        "- Cross-section terminology is consistent\n" +
        "- Cover letter is 300-400 words, professional tone\n" +
        "- Narrative thread from needs assessment carries through\n" +
        "- Budget figures match requested amount",
      errorHandling:
        "- Missing upstream section: cannot proceed, return dependency list\n" +
        "- Inconsistent data across sections: flag conflicts, use most recent source\n" +
        "- Word count exceeds typical limits: summarize least critical sections",
      inputSchema:
        "needs_assessment_output: object (required)\n" +
        "learning_objectives_output: object (required)\n" +
        "curriculum_output: object (required)\n" +
        "protocol_output: object (required)\n" +
        "marketing_output: object (required)\n" +
        "gap_analysis_output: object -- For reference\n" +
        "research_output: object -- For citation reference\n" +
        "project_title: string\n" +
        "supporter_company: string\n" +
        "requested_amount: number\n" +
        "budget_breakdown: object",
    },
  },

  // =========================================================================
  // QA GATE AGENTS
  // =========================================================================
  {
    graphId: "prose_quality",
    name: "Prose Quality Agent",
    icon: "\u2728", // sparkles
    description: "De-AI-ification scoring, banned pattern detection, prose density validation.",
    category: "qa",
    pipelineOrder: 7,
    upstream: ["needs_assessment", "grant_writer"],
    downstream: ["compliance_review"],
    inputs: ["needs_assessment_output", "grant_package_output"],
    outputs: ["prose_quality_pass_1", "prose_quality_pass_2"],
    deepDocs: {
      executionFlow:
        "1. Receive document (needs assessment for Pass 1, full package for Pass 2)\n" +
        "2. Scan for banned AI writing patterns (e.g., 'delve', 'it is important to note')\n" +
        "3. Calculate prose density: ratio of flowing prose to lists/bullets\n" +
        "4. Verify word counts by section against minimums\n" +
        "5. Check cold open compliance (Pass 1 only): character, detail, turn statement\n" +
        "6. Verify character thread appearances (Pass 1 only): minimum 4\n" +
        "7. Score overall quality (0-100)\n" +
        "8. Return pass/fail with detailed per-issue feedback",
      qualityCriteria:
        "- Overall score >= 75 for pass\n" +
        "- Zero instances of banned patterns\n" +
        "- Prose density >= 80%\n" +
        "- Word count minimums met for all sections\n" +
        "- Cold open meets framework requirements (Pass 1)",
      errorHandling:
        "- Score below threshold: return detailed revision instructions per issue\n" +
        "- Banned patterns found: list each with location and suggested replacement\n" +
        "- Retry loop: up to 3 quality iterations before human escalation",
      inputSchema:
        "Pass 1: needs_assessment_output (object, required)\n" +
        "Pass 2: grant_package_output (object, required)\n" +
        "pass_number: 1 | 2\n" +
        "scope: 'needs_assessment' | 'full_package'",
    },
  },
  {
    graphId: "compliance_review",
    name: "Compliance Review Agent",
    icon: "\u2705", // check mark
    description: "ACCME standards verification, independence review, and fair balance assessment.",
    category: "qa",
    pipelineOrder: 8,
    upstream: ["prose_quality", "grant_writer"],
    downstream: [],
    inputs: ["grant_package_output", "prose_quality_pass_2", "supporter_company", "accreditation_types"],
    outputs: ["compliance_result"],
    deepDocs: {
      executionFlow:
        "1. Verify prose quality gate has passed (prerequisite)\n" +
        "2. Check ACCME Standard 1: Independence from commercial interest\n" +
        "3. Check ACCME Standard 2: Resolution of conflicts of interest\n" +
        "4. Check ACCME Standard 3: Content validation (fair balance)\n" +
        "5. Check ACCME Standard 4-6: Additional requirements as applicable\n" +
        "6. Verify off-label content has required disclosures\n" +
        "7. Confirm supporter/competitor product balanced coverage\n" +
        "8. Produce compliance assessment with pass/fail and remediation guidance",
      qualityCriteria:
        "- All applicable ACCME standards addressed\n" +
        "- Independence from supporter influence verified\n" +
        "- Fair balance confirmed: competitor products represented\n" +
        "- Off-label disclosures present where required\n" +
        "- Certification readiness determination made",
      errorHandling:
        "- Compliance failure: return specific standard violations with remediation steps\n" +
        "- Missing prose quality pass: block execution, return prerequisite error\n" +
        "- Ambiguous compliance: flag for human review with rationale",
      inputSchema:
        "grant_package_output: object (required) -- Complete grant package\n" +
        "prose_quality_pass_2: object (required) -- Must have passed\n" +
        "supporter_company: string\n" +
        "supporter_products: string[]\n" +
        "competitor_products: string[]\n" +
        "accreditation_types: string[]\n" +
        "off_label_content: boolean",
    },
  },

  // =========================================================================
  // INFRASTRUCTURE AGENTS
  // =========================================================================
  {
    graphId: "citation_checker",
    name: "Citation Checker Agent",
    icon: "\uD83D\uDCCE", // paperclip
    description: "PubMed verification of citations, outputs registry_request for gateway.",
    category: "infra",
    pipelineOrder: 0,
    upstream: [],
    downstream: ["registry"],
    inputs: ["citations_to_verify"],
    outputs: ["verification_results", "registry_request"],
    deepDocs: {
      executionFlow:
        "1. Receive list of citations to verify\n" +
        "2. Query PubMed API for each citation by PMID or title/author\n" +
        "3. Validate: title match, author match, publication date, journal\n" +
        "4. Classify each: verified, not_found, retracted, outdated, landmark\n" +
        "5. Generate registry_request with verification results\n" +
        "6. Output structured verification report",
      qualityCriteria:
        "- Every citation checked against PubMed\n" +
        "- Retracted papers flagged immediately\n" +
        "- Verification status recorded per citation\n" +
        "- Registry request formatted for gateway agent",
      errorHandling:
        "- PubMed API rate limit: implement backoff and retry\n" +
        "- Citation not found: mark as not_found, suggest alternatives\n" +
        "- API timeout: partial results returned with unverified list",
      inputSchema:
        "citations_to_verify: Array<{pmid?: string, title: string, authors?: string, journal?: string}>\n" +
        "project_id: string",
    },
  },
  {
    graphId: "registry",
    name: "Registry Agent",
    icon: "\uD83D\uDDC4\uFE0F", // file cabinet
    description: "Gateway for all agent writes to Registry API with idempotency and dead letter queue.",
    category: "infra",
    pipelineOrder: 0,
    upstream: ["citation_checker"],
    downstream: [],
    inputs: ["registry_request"],
    outputs: ["registry_response"],
    deepDocs: {
      executionFlow:
        "1. Receive registry_request from upstream agent\n" +
        "2. Validate request schema and required fields\n" +
        "3. Check idempotency key to prevent duplicate writes\n" +
        "4. Execute write to Registry API (POST/PATCH)\n" +
        "5. On success: return confirmation with entity ID\n" +
        "6. On failure: route to dead letter queue for manual review",
      qualityCriteria:
        "- All writes are idempotent (safe to retry)\n" +
        "- Failed writes captured in dead letter queue\n" +
        "- Response includes entity ID and status\n" +
        "- Request validation prevents malformed data reaching API",
      errorHandling:
        "- Registry API unavailable: retry 3 times, then dead letter queue\n" +
        "- Validation failure: return error with specific field issues\n" +
        "- Duplicate write detected: return existing entity without re-writing",
      inputSchema:
        "registry_request: {operation: 'create'|'update', entity_type: string, data: object, idempotency_key: string}\n" +
        "project_id: string",
    },
  },

  // =========================================================================
  // RECIPE GRAPHS
  // =========================================================================
  {
    graphId: "needs_package",
    name: "Needs Package",
    icon: "\uD83D\uDCE6", // package
    description: "Research + Clinical parallel, then Gap, LO, Needs, Prose QA Pass 1, Human Review.",
    category: "recipe",
    pipelineOrder: 10,
    upstream: [],
    downstream: ["curriculum_package"],
    inputs: ["intake_form"],
    outputs: ["research_output", "clinical_output", "gap_analysis_output", "learning_objectives_output", "needs_assessment_output", "prose_quality_pass_1"],
    deepDocs: {
      executionFlow:
        "1. Validate intake form completeness\n" +
        "2. Launch Research + Clinical Practice agents in parallel (asyncio.gather)\n" +
        "3. Merge parallel results into shared state\n" +
        "4. Run Gap Analysis (requires both upstream outputs)\n" +
        "5. Run Learning Objectives\n" +
        "6. Run Needs Assessment\n" +
        "7. Run Prose Quality Pass 1\n" +
        "8. If prose fails: retry loop (up to 3x) then human escalation\n" +
        "9. Route to Human Review checkpoint",
      qualityCriteria:
        "- All 6 agent outputs present in final state\n" +
        "- Prose quality Pass 1 has passed\n" +
        "- No error records in state\n" +
        "- Human review checkpoint reached",
      errorHandling:
        "- Parallel agent failure: capture error, continue with available output if possible\n" +
        "- Quality gate failure: retry loop with max 3 iterations\n" +
        "- Unrecoverable error: checkpoint state and escalate to human review",
      inputSchema:
        "intake_form: object (required) -- Full CME intake form (10 sections, 47 fields)\n" +
        "project_id: string\n" +
        "project_name: string",
    },
  },
  {
    graphId: "curriculum_package",
    name: "Curriculum Package",
    icon: "\uD83D\uDCE6", // package
    description: "Needs Package outputs + Curriculum, Protocol, Marketing in parallel, Human Review.",
    category: "recipe",
    pipelineOrder: 11,
    upstream: ["needs_package"],
    downstream: ["grant_package"],
    inputs: ["needs_package_outputs", "intake_form"],
    outputs: ["curriculum_output", "protocol_output", "marketing_output"],
    deepDocs: {
      executionFlow:
        "1. Receive completed needs package state\n" +
        "2. Launch Curriculum Design + Research Protocol + Marketing Plan in parallel\n" +
        "3. Merge parallel results into shared state\n" +
        "4. Validate all three outputs present\n" +
        "5. Route to Human Review checkpoint",
      qualityCriteria:
        "- All 3 parallel agent outputs present\n" +
        "- No conflicts between parallel outputs\n" +
        "- State includes all needs_package outputs plus new outputs",
      errorHandling:
        "- Parallel agent failure: other agents continue, failed agent retried\n" +
        "- All three fail: escalate to human review with partial state\n" +
        "- Timeout: 5 minutes per agent, 10 minutes total for parallel batch",
      inputSchema:
        "needs_package_outputs: object (required) -- All outputs from needs_package\n" +
        "intake_form: object (required)",
    },
  },
  {
    graphId: "grant_package",
    name: "Grant Package",
    icon: "\uD83C\uDFC6", // trophy
    description: "Full 11 agents, Prose QA 2 passes, Compliance gate, Human Review.",
    category: "recipe",
    pipelineOrder: 12,
    upstream: ["curriculum_package"],
    downstream: ["full_pipeline"],
    inputs: ["all_upstream_outputs", "intake_form"],
    outputs: ["grant_package_output", "prose_quality_pass_2", "compliance_result"],
    deepDocs: {
      executionFlow:
        "1. Receive all upstream outputs from needs + curriculum packages\n" +
        "2. Run Grant Writer agent (assembles full package)\n" +
        "3. Run Prose Quality Pass 2 on complete package\n" +
        "4. If prose fails: retry loop (up to 3x)\n" +
        "5. Run Compliance Review\n" +
        "6. If compliance fails: route revision instructions back\n" +
        "7. Route to Human Review checkpoint",
      qualityCriteria:
        "- Grant package assembled from all 9 content agent outputs\n" +
        "- Prose quality Pass 2 passed\n" +
        "- Compliance review passed\n" +
        "- Package ready for pharmaceutical submission",
      errorHandling:
        "- Grant assembly incomplete: return missing section list\n" +
        "- Prose quality failure after 3 retries: escalate with revision notes\n" +
        "- Compliance failure: return specific remediation steps",
      inputSchema:
        "all_upstream_outputs: object (required) -- Combined needs + curriculum package state\n" +
        "intake_form: object (required)",
    },
  },
  {
    graphId: "full_pipeline",
    name: "Full Pipeline",
    icon: "\uD83D\uDE80", // rocket
    description: "Complete end-to-end pipeline with 3-way human review routing (approved/revision/rejected).",
    category: "recipe",
    pipelineOrder: 13,
    upstream: [],
    downstream: [],
    inputs: ["intake_form"],
    outputs: ["grant_package_output", "compliance_result", "human_review_decision"],
    deepDocs: {
      executionFlow:
        "1. Execute needs_package recipe (agents 2-6 + prose QA pass 1)\n" +
        "2. Human Review Gate 1: approve to continue or request revision\n" +
        "3. Execute curriculum_package recipe (agents 7-9 in parallel)\n" +
        "4. Human Review Gate 2: approve to continue or request revision\n" +
        "5. Execute grant_package recipe (agent 10 + prose QA pass 2 + compliance)\n" +
        "6. Human Review Gate 3: 3-way routing\n" +
        "   - Approved: mark complete, store final outputs\n" +
        "   - Revision: route back to specified agent with notes\n" +
        "   - Rejected: mark cancelled with reason",
      qualityCriteria:
        "- All 11 content agents executed successfully\n" +
        "- Both prose quality passes passed\n" +
        "- Compliance review passed\n" +
        "- All human review gates cleared\n" +
        "- Final package submission-ready",
      errorHandling:
        "- Human review timeout: escalate via notification\n" +
        "- Revision requested: re-run from specified agent forward\n" +
        "- Rejected: archive state with reason, no further processing",
      inputSchema:
        "intake_form: object (required) -- Full CME intake form\n" +
        "project_id: string\n" +
        "project_name: string",
    },
  },
];

/** Lookup a single catalog entry by graphId. */
export function getCatalogEntry(graphId: string): AgentCatalogEntry | undefined {
  return AGENT_CATALOG.find((a) => a.graphId === graphId);
}

/** Category display metadata. */
export const CATEGORY_META: Record<AgentCategory, { label: string; order: number }> = {
  content: { label: "Content Agents", order: 1 },
  recipe: { label: "Recipe Graphs", order: 2 },
  qa: { label: "QA Gates", order: 3 },
  infra: { label: "Infrastructure", order: 4 },
};
