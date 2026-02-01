# Agent 2: Research Agent
## Literature Review, Epidemiology, Market Intelligence

**Agent Type:** LLM-powered with tools  
**Complexity:** Medium  
**Primary Output:** Research report with 30+ citations

---

## Role Definition

The Research Agent conducts comprehensive literature review, epidemiology research, and market intelligence gathering for the specified therapeutic area. It produces a structured research report that serves as the evidence foundation for Gap Analysis and all downstream agents.

---

## Inputs

### From Intake Form
| Field | Section | Purpose |
|-------|---------|---------|
| therapeutic_area | A | Primary research domain |
| disease_state | A | Specific condition focus |
| target_audience | B | Specialty context for relevance |
| geographic_focus | B | Regional epidemiology selection |
| supporter_company | C | Market intelligence focus |
| supporter_products | C | Product landscape context |
| known_gaps | D | Directed research areas |
| competitor_products | F | Competitive landscape |

### From Other Agents
None—Research Agent runs in parallel with Clinical Practice Agent at pipeline start.

---

## Outputs

### Research Report Structure

```yaml
research_output:
  metadata:
    agent_version: "2.0"
    execution_timestamp: datetime
    search_queries_executed: int
    sources_reviewed: int
    sources_cited: int
  
  epidemiology:
    prevalence:
      global: str
      us: str
      regional_variations: List[str]
    incidence:
      annual_new_cases: str
      trends: str
    demographics:
      age_distribution: str
      sex_distribution: str
      racial_ethnic_factors: str
    burden:
      mortality: str
      morbidity: str
      quality_of_life_impact: str
    projections:
      future_prevalence: str
      drivers_of_change: str
  
  economic_burden:
    direct_costs:
      annual_total: str
      per_patient: str
      cost_drivers: List[str]
    indirect_costs:
      productivity_loss: str
      caregiver_burden: str
    healthcare_utilization:
      hospitalizations: str
      ed_visits: str
      outpatient_visits: str
  
  treatment_landscape:
    current_standards:
      first_line: List[str]
      second_line: List[str]
      emerging: List[str]
    guideline_summary:
      major_guidelines: List[Dict]
      recent_updates: List[str]
      areas_of_consensus: List[str]
      areas_of_controversy: List[str]
    pipeline:
      phase_3: List[str]
      recently_approved: List[str]
  
  market_intelligence:
    supporter_context:
      company_position: str
      product_portfolio: List[str]
      recent_approvals: List[str]
      competitive_positioning: str
    market_dynamics:
      market_size: str
      growth_trajectory: str
      key_players: List[str]
  
  literature_synthesis:
    key_findings: List[Dict]
    evidence_gaps: List[str]
    research_priorities: List[str]
  
  citations:
    - id: str
      authors: str
      title: str
      journal: str
      year: int
      doi: str
      relevance: str
      key_finding: str
```

---

## System Prompt

```
You are a medical research specialist conducting literature review and market intelligence for continuing medical education grant applications. Your research must be:

1. COMPREHENSIVE: Cover epidemiology, treatment landscape, guidelines, and market context
2. CURRENT: Prioritize sources from the past 3 years; flag older foundational studies
3. AUTHORITATIVE: Prefer peer-reviewed journals, society guidelines, and government data
4. QUANTITATIVE: Include specific numbers, percentages, and statistics throughout
5. BALANCED: Present the full landscape, not just supporter-favorable data

CRITICAL REQUIREMENTS:
- Minimum 30 unique, verifiable citations
- Every statistic must have a citation
- Include publication year for all sources
- Distinguish between US and global data
- Flag any data older than 5 years
- Note conflicting evidence where it exists

OUTPUT FORMAT:
Produce a structured research report following the exact schema provided. Every section must contain specific, cited data points. Do not use placeholder language like "studies show" without naming the specific study.

PROHIBITED:
- Generic statements without citations
- Unsourced statistics
- Speculation presented as fact
- Promotional language about any product
- Outdated data without flagging
```

---

## Tools

### 1. PubMed Search
```python
@tool
def pubmed_search(
    query: str,
    max_results: int = 50,
    date_filter: str = "5 years"
) -> List[Dict]:
    """
    Search PubMed for relevant medical literature.
    
    Args:
        query: Search terms (supports MeSH terms and boolean operators)
        max_results: Maximum number of results to return
        date_filter: Time range for results
    
    Returns:
        List of article metadata including PMID, title, abstract, authors, journal, year
    """
```

### 2. Guidelines Search
```python
@tool
def guidelines_search(
    condition: str,
    societies: List[str] = None
) -> List[Dict]:
    """
    Search major medical society guidelines.
    
    Args:
        condition: Disease/condition to search
        societies: Optional list of specific societies (e.g., ["AHA", "ACC", "ESC"])
    
    Returns:
        List of guideline documents with publication dates and key recommendations
    """
```

### 3. Epidemiology Database
```python
@tool
def epidemiology_lookup(
    condition: str,
    metrics: List[str] = ["prevalence", "incidence", "mortality"],
    geography: str = "US"
) -> Dict:
    """
    Query epidemiological databases (CDC, WHO, disease registries).
    
    Args:
        condition: Disease/condition
        metrics: Which metrics to retrieve
        geography: Geographic focus
    
    Returns:
        Epidemiological data with sources
    """
```

### 4. Market Intelligence
```python
@tool
def market_intelligence(
    therapeutic_area: str,
    company: str = None,
    products: List[str] = None
) -> Dict:
    """
    Gather market landscape information.
    
    Args:
        therapeutic_area: Treatment area
        company: Optional company focus
        products: Optional specific products
    
    Returns:
        Market size, competitive landscape, pipeline information
    """
```

### 5. Clinical Trials Search
```python
@tool
def clinical_trials_search(
    condition: str,
    phase: List[str] = ["Phase 3", "Phase 4"],
    status: str = "recruiting"
) -> List[Dict]:
    """
    Search ClinicalTrials.gov for relevant trials.
    
    Args:
        condition: Disease/condition
        phase: Trial phases to include
        status: Trial status filter
    
    Returns:
        List of relevant clinical trials with key details
    """
```

---

## Execution Flow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│  1. Parse intake data               │
│     - Extract therapeutic area      │
│     - Identify disease state        │
│     - Note geographic focus         │
│     - Capture supporter context     │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  2. Epidemiology research           │
│     - Query epidemiology databases  │
│     - Search for prevalence data    │
│     - Gather burden statistics      │
│     - Document projections          │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  3. Literature review               │
│     - Execute PubMed searches       │
│     - Identify key studies          │
│     - Extract relevant findings     │
│     - Note evidence gaps            │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  4. Guidelines analysis             │
│     - Search society guidelines     │
│     - Extract recommendations       │
│     - Identify recent updates       │
│     - Note areas of controversy     │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  5. Market intelligence             │
│     - Analyze treatment landscape   │
│     - Research supporter position   │
│     - Map competitive landscape     │
│     - Identify pipeline products    │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  6. Synthesize and structure        │
│     - Compile all findings          │
│     - Verify citation accuracy      │
│     - Format per output schema      │
│     - Quality check completeness    │
└─────────────────────────────────────┘
  │
  ▼
OUTPUT: research_output
```

---

## Quality Criteria

### Completeness Checklist
- [ ] Epidemiology section has prevalence, incidence, burden, projections
- [ ] Economic burden includes direct and indirect costs
- [ ] Treatment landscape covers current standards and pipeline
- [ ] Guidelines from 2+ major societies included
- [ ] Market intelligence covers supporter and competitive context
- [ ] Literature synthesis identifies evidence gaps

### Citation Requirements
- [ ] Minimum 30 unique citations
- [ ] 70%+ citations from past 5 years
- [ ] Every quantitative claim has citation
- [ ] No citation appears without being referenced in text
- [ ] DOIs included where available

### Data Currency
- [ ] Epidemiology data from past 3 years preferred
- [ ] Guidelines reflect most recent versions
- [ ] Market data current within 12 months
- [ ] Older foundational studies explicitly dated

---

## Example Output Excerpt

```yaml
epidemiology:
  prevalence:
    global: "Approximately 64 million people worldwide have heart failure, representing 1-2% of the adult population in developed countries (Savarese et al., Lancet 2023)"
    us: "An estimated 6.7 million Americans ≥20 years have heart failure, projected to exceed 8 million by 2030 (Tsao et al., Circulation 2023)"
    regional_variations:
      - "Higher prevalence in Southern states (4.2%) vs. Western states (2.8%) (CDC BRFSS 2022)"
      - "Rural populations show 25% higher prevalence than urban (Jackson et al., JAMA Cardiol 2023)"
  
  incidence:
    annual_new_cases: "Approximately 1 million new cases diagnosed annually in the US (Virani et al., Circulation 2023)"
    trends: "Age-adjusted incidence declining 2% annually since 2015, attributed to improved hypertension and CAD management (Shah et al., JACC 2024)"
  
  burden:
    mortality: "Heart failure is listed on 13.4% of all death certificates; 5-year mortality remains 50% despite modern therapy (Heidenreich et al., Circulation 2022)"
    quality_of_life_impact: "KCCQ scores average 55/100 in symptomatic HF, comparable to end-stage renal disease (Nassif et al., JACC HF 2023)"

citations:
  - id: "savarese2023"
    authors: "Savarese G, Becher PM, Lund LH, et al."
    title: "Global burden of heart failure: a comprehensive and updated review of epidemiology"
    journal: "Cardiovascular Research"
    year: 2023
    doi: "10.1093/cvr/cvac013"
    relevance: "Primary source for global prevalence estimates"
    key_finding: "64 million people affected globally"
```

---

## Error Handling

| Error | Response |
|-------|----------|
| Insufficient search results | Broaden search terms, try alternative databases |
| Conflicting data sources | Include both with notation of discrepancy |
| Missing epidemiology data | Flag gap, use closest available proxy with disclaimer |
| Outdated guidelines | Note age, search for interim updates or position statements |
| Market data unavailable | Note limitation, proceed with available public information |

---

## Dependencies

### Upstream
- Intake form (validated)

### Downstream
- Gap Analysis Agent (primary consumer)
- Clinical Practice Agent (parallel, may share findings)
- All subsequent agents (reference as needed)

---

## Testing Scenarios

### Test Case 1: Common Condition (Heart Failure)
- Expected: Abundant literature, multiple guidelines, rich epidemiology
- Verify: Citation count exceeds 40, multiple guideline sources

### Test Case 2: Rare Disease (Amyloidosis)
- Expected: Limited literature, specialized guidelines
- Verify: Handles sparse data gracefully, flags limitations

### Test Case 3: Emerging Therapeutic Area (Gene Therapy)
- Expected: Rapidly evolving landscape, limited long-term data
- Verify: Emphasizes recency, notes evidence limitations

---

*Research Agent output quality directly determines the evidence foundation for the entire grant package.*
