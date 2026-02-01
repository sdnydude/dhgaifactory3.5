# Agent 9: Marketing Plan Agent
## Audience Generation Strategy and Budget

**Agent Type:** LLM-powered  
**Complexity:** Medium  
**Primary Output:** Multi-channel marketing plan with budget and timeline

---

## Role Definition

The Marketing Plan Agent creates a comprehensive audience generation strategy to reach the target healthcare professionals with the educational activity. The plan must demonstrate how the projected reach will be achieved, with specific channel strategies, timeline, and budget allocation.

---

## Inputs

### From Other Agents
| Agent | Data Used |
|-------|-----------|
| Learning Objectives Agent (6) | Key messages for marketing |
| Needs Assessment Agent (5) | Urgency and hook for promotion |

### From Intake Form
| Field | Section | Purpose |
|-------|---------|---------|
| target_audience | B | Audience definition |
| practice_settings | B | Channel targeting |
| geographic_focus | B | Geographic targeting |
| estimated_reach | G | Reach targets |
| marketing_budget | G | Budget constraints |
| marketing_channels | G | Preferred channels |
| launch_date | G | Timeline anchor |

---

## Outputs

### Marketing Plan Structure

```yaml
marketing_output:
  metadata:
    agent_version: "2.0"
    execution_timestamp: datetime
    total_budget: float
    projected_reach: int
  
  executive_summary:
    strategy_overview: str
    key_channels: List[str]
    projected_outcomes: str
    budget_summary: str
  
  target_audience_profile:
    primary_audience:
      specialty: str
      practice_settings: List[str]
      geographic_scope: str
      estimated_universe: int
    secondary_audiences:
      - segment: str
        rationale: str
        estimated_size: int
    audience_insights:
      key_motivators: List[str]
      barriers_to_engagement: List[str]
      preferred_channels: List[str]
      optimal_timing: str
  
  key_messages:
    primary_message: str
    supporting_messages:
      - message: str
        target_segment: str
    call_to_action: str
    compliance_considerations: str
  
  channel_strategy:
    channels:
      - channel_name: str
        channel_type: str  # "email", "social", "society", "journal", etc.
        description: str
        target_audience_fit: str
        tactics:
          - tactic: str
            timing: str
            cost: float
            expected_reach: int
            expected_conversion: float
        total_channel_budget: float
        projected_registrations: int
    
    channel_mix_rationale: str
    integration_strategy: str
  
  budget_allocation:
    total_budget: float
    allocation_by_channel:
      - channel: str
        budget: float
        percentage: float
    allocation_by_phase:
      - phase: str
        budget: float
        activities: List[str]
    contingency: float
    cost_per_registration_target: float
  
  timeline:
    phases:
      - phase_name: str
        start_date: str
        end_date: str
        activities:
          - activity: str
            timing: str
            responsible_party: str
    key_milestones:
      - milestone: str
        date: str
        success_criteria: str
  
  performance_metrics:
    kpis:
      - metric: str
        target: str
        measurement_method: str
    tracking_plan: str
    optimization_triggers: str
  
  compliance_and_independence:
    disclosure_requirements: str
    content_restrictions: str
    regulatory_considerations: str
```

---

## System Prompt

```
You are a healthcare marketing strategist developing an audience generation plan for a continuing medical education activity. Your plan must:

1. TARGETED: Focus resources on channels that reach the specific audience
2. REALISTIC: Budget and reach projections must be achievable
3. COMPLIANT: Adhere to CME marketing regulations
4. INTEGRATED: Channels should work together, not in isolation
5. MEASURABLE: Include KPIs and tracking mechanisms

CHANNEL SELECTION PRINCIPLES:
- Society partnerships reach engaged, relevant audiences
- Email remains highest-converting channel for HCP education
- Social media works for awareness but low direct conversion
- Journal advertising builds credibility but high cost-per-registration
- Peer-to-peer outreach is effective but resource-intensive

BUDGET ALLOCATION GUIDELINES:
- Cost per registration typically $50-150 for live events
- Cost per registration typically $15-50 for online activities
- Allocate 60-70% to highest-performing channels
- Reserve 10-15% for optimization/contingency

COMPLIANCE REQUIREMENTS:
- Marketing must be independent of supporter
- No promotion of specific products
- Educational content must be foregrounded
- Appropriate disclosures required

OUTPUT FORMAT:
Produce a comprehensive marketing plan that could be executed by a marketing team. Include specific tactics, timing, and budget for each channel.
```

---

## Channel Options and Characteristics

### Channel Matrix

| Channel | Reach | Conversion | Cost | Best For |
|---------|-------|------------|------|----------|
| Email (house list) | Medium | High (3-5%) | Low | Existing audience |
| Email (rented list) | High | Medium (0.5-1.5%) | Medium | Audience expansion |
| Society partnership | Medium | High (2-4%) | Medium | Credibility, targeted reach |
| Journal advertising | High | Low (0.1-0.3%) | High | Awareness, credibility |
| Social media (organic) | Low | Very Low | Low | Awareness, engagement |
| Social media (paid) | Medium | Low (0.3-0.8%) | Medium | Targeted awareness |
| Conference presence | Low | Medium | High | Face-to-face engagement |
| Peer referral | Low | High (5-10%) | Low | High-value registrations |
| Search/SEO | Variable | Medium | Low-Medium | Intent-driven discovery |
| Aggregator sites | Medium | Low (0.5-1%) | Medium | Volume, discovery |

### Channel Selection by Audience

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CHANNEL SELECTION BY AUDIENCE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PRIMARY CARE PHYSICIANS                                                    │
│  └─ Email (high volume needed)                                              │
│  └─ AAFP/ACP partnerships                                                   │
│  └─ Primary care journal advertising                                        │
│  └─ CME aggregator listings                                                 │
│                                                                             │
│  CARDIOLOGISTS                                                              │
│  └─ ACC/AHA partnerships                                                    │
│  └─ Specialty journal advertising (JACC, Circulation)                       │
│  └─ Conference presence (ACC annual meeting)                                │
│  └─ Targeted email                                                          │
│                                                                             │
│  NURSE PRACTITIONERS / PHYSICIAN ASSISTANTS                                 │
│  └─ AANP/AAPA partnerships                                                  │
│  └─ Clinical Advisor, JAAPA advertising                                     │
│  └─ Email with CE emphasis                                                  │
│  └─ Social media (higher engagement)                                        │
│                                                                             │
│  MULTI-SPECIALTY                                                            │
│  └─ CME aggregators (Medscape, MDLinx)                                      │
│  └─ Broad email campaigns                                                   │
│  └─ Search optimization                                                     │
│  └─ Multiple society partnerships                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Execution Flow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│  1. Analyze inputs                  │
│     - Define target audience        │
│     - Note reach targets            │
│     - Review budget constraints     │
│     - Extract key messages          │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  2. Develop audience profile        │
│     - Characterize primary audience │
│     - Identify secondary audiences  │
│     - Research audience insights    │
│     - Estimate addressable universe │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  3. Craft key messages              │
│     - Primary message               │
│     - Supporting messages           │
│     - Call to action                │
│     - Compliance review             │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  4. Select channels                 │
│     - Evaluate channel fit          │
│     - Prioritize by effectiveness   │
│     - Plan integration              │
│     - Document rationale            │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  5. Develop channel tactics         │
│     - Specific tactics per channel  │
│     - Timing for each tactic        │
│     - Cost estimates                │
│     - Reach projections             │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  6. Create budget allocation        │
│     - Allocate by channel           │
│     - Allocate by phase             │
│     - Include contingency           │
│     - Calculate cost per reg        │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  7. Build timeline                  │
│     - Phase definitions             │
│     - Activity scheduling           │
│     - Milestone identification      │
│     - Responsibility assignment     │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  8. Define performance metrics      │
│     - KPIs per channel              │
│     - Tracking mechanisms           │
│     - Optimization triggers         │
│     - Reporting cadence             │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  9. Address compliance              │
│     - Disclosure requirements       │
│     - Content restrictions          │
│     - Independence standards        │
│     - Regulatory considerations     │
└─────────────────────────────────────┘
  │
  ▼
OUTPUT: marketing_output
```

---

## Quality Criteria

### Strategy Quality
- [ ] Channel mix appropriate for audience
- [ ] Integration between channels clear
- [ ] Timing optimized for audience availability
- [ ] Messages tailored to audience needs

### Budget Quality
- [ ] Total budget aligns with intake
- [ ] Allocation prioritizes high-performing channels
- [ ] Cost per registration is realistic
- [ ] Contingency included

### Timeline Quality
- [ ] Adequate lead time before launch
- [ ] Phases logically sequenced
- [ ] Milestones achievable
- [ ] Optimization windows included

### Compliance Quality
- [ ] Independence maintained
- [ ] Disclosures specified
- [ ] Content restrictions noted
- [ ] Regulatory requirements addressed

---

## Example Output Excerpt

```yaml
executive_summary:
  strategy_overview: |
    This marketing plan targets 500 cardiologists and primary care physicians 
    managing heart failure patients through a multi-channel strategy 
    emphasizing society partnerships and targeted email outreach. The 
    12-week campaign leverages ACC partnership opportunities and specialty 
    email lists to achieve cost-effective reach.
  key_channels:
    - "ACC partnership (primary)"
    - "Targeted email campaigns"
    - "Cardiology journal digital advertising"
    - "CME aggregator listings"
  projected_outcomes: "500 registrations at projected cost of $85/registration"
  budget_summary: "$42,500 total marketing investment"

channel_strategy:
  channels:
    - channel_name: "American College of Cardiology Partnership"
      channel_type: "society"
      description: "Partnership with ACC for member communications and website placement"
      target_audience_fit: "Direct access to engaged cardiologists"
      tactics:
        - tactic: "ACC website activity listing"
          timing: "Weeks 1-12"
          cost: 5000.00
          expected_reach: 15000
          expected_conversion: 0.015
        - tactic: "ACC member email (2 sends)"
          timing: "Weeks 3 and 7"
          cost: 8000.00
          expected_reach: 50000
          expected_conversion: 0.025
        - tactic: "CardioSource digital banner"
          timing: "Weeks 4-10"
          cost: 4000.00
          expected_reach: 25000
          expected_conversion: 0.008
      total_channel_budget: 17000.00
      projected_registrations: 195

    - channel_name: "Targeted Email Campaigns"
      channel_type: "email"
      description: "Email campaigns to rented HCP lists"
      target_audience_fit: "High-intent channel for CME-seeking physicians"
      tactics:
        - tactic: "Primary care list (3 sends)"
          timing: "Weeks 2, 5, 9"
          cost: 6000.00
          expected_reach: 75000
          expected_conversion: 0.012
        - tactic: "Cardiology list (3 sends)"
          timing: "Weeks 2, 5, 9"
          cost: 4500.00
          expected_reach: 30000
          expected_conversion: 0.018
      total_channel_budget: 10500.00
      projected_registrations: 144

budget_allocation:
  total_budget: 42500.00
  allocation_by_channel:
    - channel: "ACC Partnership"
      budget: 17000.00
      percentage: 40.0
    - channel: "Targeted Email"
      budget: 10500.00
      percentage: 24.7
    - channel: "Journal Digital Advertising"
      budget: 7500.00
      percentage: 17.6
    - channel: "CME Aggregators"
      budget: 3500.00
      percentage: 8.2
    - channel: "Contingency"
      budget: 4000.00
      percentage: 9.4
  cost_per_registration_target: 85.00

timeline:
  phases:
    - phase_name: "Pre-Launch"
      start_date: "Week -4"
      end_date: "Week 0"
      activities:
        - activity: "Finalize all creative assets"
          timing: "Week -4"
          responsible_party: "Marketing team"
        - activity: "Secure society partnerships"
          timing: "Week -4 to -2"
          responsible_party: "Partnership manager"
        - activity: "Set up tracking/analytics"
          timing: "Week -2"
          responsible_party: "Digital team"
    
    - phase_name: "Launch"
      start_date: "Week 1"
      end_date: "Week 3"
      activities:
        - activity: "Activate all channels"
          timing: "Week 1"
          responsible_party: "Marketing team"
        - activity: "First email campaign send"
          timing: "Week 2"
          responsible_party: "Email marketing"
        - activity: "Monitor initial performance"
          timing: "Week 1-3"
          responsible_party: "Analytics team"
```

---

## Error Handling

| Error | Response |
|-------|----------|
| Budget insufficient for reach target | Prioritize highest-converting channels, adjust reach expectations |
| Target audience too broad | Focus on primary segment, treat others as secondary |
| Timeline too compressed | Extend timeline or reduce channel count |
| Reach projections unrealistic | Use conservative conversion rates, document assumptions |
| Compliance concerns | Flag for review, suggest compliant alternatives |

---

## Dependencies

### Upstream
- Learning Objectives Agent output (key messages)
- Needs Assessment Agent output (urgency hooks)
- Intake form (audience, budget, timeline)

### Downstream
- Grant Writer Agent (marketing section)

---

## Testing Scenarios

### Test Case 1: Specialty-Focused Activity
- Expected: Society partnership prominent
- Verify: Specialty-specific channels prioritized

### Test Case 2: Broad Primary Care Audience
- Expected: Volume-oriented approach
- Verify: High-reach channels emphasized

### Test Case 3: Limited Budget
- Expected: Focused channel selection
- Verify: Resources concentrated on highest ROI channels

---

*The marketing plan ensures the educational activity reaches its intended audience.*
