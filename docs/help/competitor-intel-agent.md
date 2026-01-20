# Competitor Intelligence Agent User Guide

**Agent Name:** DHG Competitor Intelligence Agent  
**Purpose:** Market analysis and competitive positioning for CME activities  
**Best For:** Analyzing competitor offerings, market intelligence, differentiation strategies  

---

## What This Agent Does

The Competitor Intelligence Agent monitors and analyzes the CME marketplace to help you understand the competitive landscape. It extracts competitor activity data, identifies market trends, analyzes funders and providers, and generates differentiation strategies.

**Key Capabilities:**
- Analyze competitor CME activities
- Extract activity metadata (provider, funder, format, credits, topics)
- Generate competitive differentiation summaries
- Provide market intelligence reports
- Validate and monitor competitor URLs
- Track top providers and funders
- Analyze format distribution trends
- Set up continuous monitoring

---

## When to Use This Agent

Use the Competitor Intelligence Agent when you need to:
- **Research competitors** before launching a new CME activity
- **Identify market gaps** in specific therapeutic areas
- **Differentiate your offering** from existing activities
- **Track industry trends** (formats, topics, providers)
- **Monitor specific competitors** for new activities
- **Analyze funder activity** to identify partnership opportunities
- **Validate competitor claims** by checking source URLs

---

## Example Prompts

### 1. Analyze Competitor Activity
```
Analyze this competitor CME activity: https://www.medscape.org/viewarticle/diabetes-management-2024
Extract provider, funder, format, credits, topics, and tell me how we can differentiate.
```

### 2. Extract Activity Data
```
Extract detailed activity data from these URLs:
- https://www.webmd.com/cme/heart-failure-update
- https://www.accme.org/provider-activity/cardiology-2024
Include provider, funder, date, format, credits, and topics.
```

### 3. Get Differentiation Strategy
```
We're planning a CME on obesity pharmacotherapy. 
What are competitors doing in this space? 
How can we differentiate our offering?
```

### 4. Market Intelligence Report
```
Generate a market intelligence report for diabetes CME activities in the last 6 months.
Include: top providers, common formats, trending topics, major funders.
```

### 5. Validate Competitor URLs
```
Validate these competitor URLs and tell me if they're still active:
- https://www.medscape.org/cme/hypertension-2023
- https://www.webmd.com/cme/copd-management
- https://www.accme.org/activity/12345
```

### 6. List Available Sources
```
What CME data sources are available for competitive analysis?
```

### 7. Top Providers by Source
```
Who are the top CME providers on Medscape?
```

### 8. Top Funders
```
Who are the top 10 funders of CME activities in cardiology?
```

### 9. Format Distribution Trends
```
What's the distribution of CME formats (webinar, online course, live event, etc.) in oncology?
```

### 10. Set Up Monitoring
```
Set up monitoring for new CME activities on diabetes from Medscape and WebMD.
Alert me weekly with summaries.
```

---

## How to Have a Conversation

**Start with a specific competitor or topic:**

**You:** "Analyze this competitor CME: https://www.medscape.org/viewarticle/obesity-glp1-2024"

**Agent:** Will extract:
- Provider: Medscape Education
- Funder: Novo Nordisk (example)
- Format: Online activity
- Credits: 1.0 AMA PRA Category 1
- Topics: Obesity, GLP-1 agonists, weight management
- Launch date: 2024-01-15

**You:** "How can we differentiate if we're creating a similar activity?"

**Agent:** Will provide differentiation strategy:
- Novel angles not covered
- Underserved audience segments
- Unique formats or interactive elements
- Expert faculty gaps
- Emerging topics not addressed

**Then expand:**
- "Who else is doing obesity CME?"
- "What formats are most popular for endocrinology CME?"
- "Set up monitoring for new obesity CME activities"

---

## What You'll Get

### Competitor Activity Analysis
- **Provider:** Organization offering the CME
- **Funder:** Commercial sponsor or grant supporter
- **Format:** Webinar, online course, live event, podcast, etc.
- **Credits:** AMA PRA Category 1, nursing, pharmacy, etc.
- **Topics:** Clinical focus areas
- **Launch Date:** When activity went live
- **URL:** Source link (validated)
- **Differentiation Summary:** How to position against this competitor

### Market Intelligence Report
- **Top Providers:** Leading CME organizations in the space
- **Trending Topics:** Most common clinical focus areas
- **Format Distribution:** Breakdown by activity type
- **Funder Activity:** Major commercial supporters
- **Market Gaps:** Underserved topics or audiences
- **Emerging Trends:** New formats, topics, or approaches

### Differentiation Strategy
- **Content Gaps:** Topics competitors aren't covering
- **Audience Gaps:** Underserved specialties or experience levels
- **Format Opportunities:** Innovative delivery methods
- **Expert Positioning:** Unique faculty or perspectives
- **Timing Advantages:** Market entry windows

### URL Validation Results
- **Status:** Active, inactive, redirected, or error
- **Response Time:** Speed of page load
- **Content Type:** CME activity, landing page, error page
- **Last Checked:** Timestamp of validation

### Provider/Funder Lists
- **Top 10 Providers:** Ranked by activity volume
- **Top 10 Funders:** Ranked by activity support
- **Activity Counts:** Number of offerings per provider/funder
- **Trends:** Growth or decline over time

### Format Distribution
- **Webinar:** X% of activities
- **Online Course:** X% of activities
- **Live Event:** X% of activities
- **Podcast/Audio:** X% of activities
- **Other:** X% of activities
- **Trends:** Format popularity over time

---

## Data Sources

The agent monitors these CME sources:

| Source | Coverage | Specialty Focus |
|--------|----------|-----------------|
| **ACCME** | Accredited providers | All specialties |
| **Medscape** | High-volume provider | Primary care, cardiology, oncology |
| **WebMD** | High-volume provider | Primary care, neurology, psychiatry |

More sources are added over time. Use the  endpoint to see the current list.

---

## Compliance & Ethics

### What We Monitor
- **Public CME activity listings** - Freely available information
- **Provider websites** - Publicly accessible data
- **Funder disclosures** - Transparency statements

### What We Don't Do
- **Scrape behind logins** - No unauthorized access
- **Copy proprietary content** - Data extraction only (metadata)
- **Violate terms of service** - Respectful monitoring practices

### How We Use This Data
- **Market research** - Understand competitive landscape
- **Differentiation** - Position your offerings uniquely
- **Trend analysis** - Identify opportunities and gaps

**Note:** All competitive intelligence is derived from publicly available information. Always verify findings independently.

---

## Tips for Best Results

1. **Provide complete URLs** - Full links, not shortened or redirected URLs
2. **Specify the therapeutic area** - "cardiology" vs "medicine" narrows results
3. **Define your time frame** - "last 6 months" vs "all time"
4. **Name your target audience** - "cardiologists" vs "all physicians"
5. **Ask for specific competitors** - "Medscape activities" vs "all activities"
6. **Request differentiation explicitly** - "How can we differentiate?" triggers strategic analysis
7. **Set up monitoring early** - Continuous tracking reveals trends over time
8. **Validate before launch** - Check competitor URLs to ensure data is current

---

## Common Use Cases

### Use Case 1: Pre-Launch Competitive Analysis
**Goal:** Understand the market before designing a new CME  
**Prompt:** "We're planning a CME on [topic]. What are competitors doing? How can we differentiate?"  
**Output:** Competitor landscape + differentiation strategy

### Use Case 2: Extract Competitor Data
**Goal:** Get detailed metadata from specific competitor activities  
**Prompt:** "Extract activity data from [URL list]. Include provider, funder, format, credits, topics."  
**Output:** Structured data for each URL

### Use Case 3: Market Trend Analysis
**Goal:** Identify trending topics and formats  
**Prompt:** "Generate a market intelligence report for [specialty] CME in the last [time period]."  
**Output:** Trends, top providers/funders, format distribution, gaps

### Use Case 4: Funder Research
**Goal:** Identify potential commercial supporters  
**Prompt:** "Who are the top funders of CME activities in [therapeutic area]?"  
**Output:** Ranked list of funders with activity counts

### Use Case 5: Provider Benchmarking
**Goal:** Compare your organization to competitors  
**Prompt:** "Who are the top CME providers in [specialty]? How many activities do they offer?"  
**Output:** Provider rankings with volume metrics

### Use Case 6: URL Monitoring
**Goal:** Track competitor activity launches  
**Prompt:** "Set up monitoring for new CME activities from [provider] on [topic]. Alert me weekly."  
**Output:** Automated monitoring with weekly summaries

### Use Case 7: Differentiation Review
**Goal:** Position your offering against a specific competitor  
**Prompt:** "Compare our planned CME on [topic] to this competitor activity: [URL]. How should we differentiate?"  
**Output:** Side-by-side comparison + strategic recommendations

---

## Differentiation Strategies

The agent helps you differentiate on these dimensions:

### 1. Content Differentiation
- **Novel Topics:** Cover emerging areas competitors haven't addressed
- **Depth:** Go deeper on a specific aspect (e.g., resistant hypertension vs general HTN)
- **Breadth:** Cover multiple related topics in one activity
- **Evidence:** Use the latest guidelines or studies competitors haven't integrated

### 2. Audience Differentiation
- **Specialty Focus:** Target a niche specialty (e.g., nephrologists vs all physicians)
- **Experience Level:** Serve advanced practitioners vs general audience
- **Practice Setting:** Focus on rural, hospital-based, or outpatient providers
- **Team-Based:** Include interprofessional learners (RN, PharmD, PA)

### 3. Format Differentiation
- **Interactive:** Case-based learning vs didactic lecture
- **Simulation:** Virtual patients or decision trees
- **Micro-Learning:** 5-10 minute modules vs 1-hour webinars
- **On-Demand:** Asynchronous vs live events
- **Blended:** Combine formats (video + case + assessment)

### 4. Faculty Differentiation
- **Thought Leaders:** Recruit guideline authors or KOLs
- **Diverse Perspectives:** Include community practitioners, not just academics
- **Patient Voices:** Incorporate patient stories or panels
- **International:** Global perspectives on disease management

### 5. Outcome Differentiation
- **Practice Change Focus:** Emphasize Moore Levels 5-7 (performance, patient, community outcomes)
- **Tools Provided:** Give learners job aids, algorithms, patient handouts
- **Follow-Up:** Include 6-week post-activity support or coaching
- **Quality Improvement:** Integrate CME with QI projects

---

## Technical Details

**Agent Type:** Competitive Intelligence Analyzer  
**Underlying Model:** Ollama (qwen2.5:14b) with market analysis prompting  
**Data Sources:**
- ACCME provider database
- Medscape CME listings
- WebMD CME listings
- (Additional sources added over time)

**Response Time:** 10-30 seconds for URL extraction; 15-45 seconds for market intelligence  
**Output Format:** Structured JSON with formatted text summaries  
**URL Validation:** Real-time HTTP checks with retry logic  

---

## Limitations

- **Public data only** - Cannot access activities behind login walls
- **Metadata focus** - Extracts activity info, not full content
- **Lag time** - New activities may take 24-48 hours to appear in sources
- **Source coverage** - Not all CME providers are monitored (yet)
- **Accuracy depends on source** - Provider website changes can affect data quality
- **Strategic recommendations are suggestive** - Human expertise required for final positioning decisions

---

## Related Agents

- **Research Agent** - Gather clinical evidence to support differentiation claims
- **Curriculum Agent** - Design curricula based on competitive gaps identified
- **Outcomes Agent** - Measure your CME's effectiveness vs competitor outcomes
- **QA/Compliance Agent** - Ensure your differentiated approach still meets ACCME standards

---

## Monitoring Setup

### How to Set Up Continuous Monitoring

**Prompt:** "Set up monitoring for [topic] CME activities from [sources]. Alert me [frequency]."

**Example:** "Set up monitoring for diabetes CME from Medscape and WebMD. Alert me weekly."

**What You'll Get:**
- Weekly email summaries (or your chosen frequency)
- New activity alerts with metadata
- Trend reports (monthly)
- Competitive shift notifications (when major providers launch in your space)

**Adjust Monitoring:**
- "Add [new topic] to my monitoring"
- "Remove [source] from my monitoring"
- "Change alert frequency to daily/weekly/monthly"
- "Pause monitoring for 30 days"

---

## Questions?

For technical support or feature requests, contact the DHG AI Factory team.

**Last Updated:** January 20, 2026  
**Version:** 1.0.0
