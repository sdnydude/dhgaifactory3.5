# Findings: CME Database Schema Research

**Date:** 2026-03-12

---

## 1. Intake Form Structure (47 fields, 10 sections)

### Section A: Project Basics (6 fields)
| Field | Type | Required |
|-------|------|----------|
| `project_name` | string (max 200) | Yes |
| `therapeutic_area` | string (select) | Yes |
| `disease_state` | string (select, funding tier) | Yes |
| `target_audience_primary` | string[] (1-5) | Yes |
| `target_audience_secondary` | string[] (up to 3) | No |
| `target_hcp_types` | string[] (multi-select) | No |

### Section B: Supporter Information (5 fields)
| Field | Type | Required |
|-------|------|----------|
| `supporter_name` | string | Yes |
| `supporter_contact_name` | string | No |
| `supporter_contact_email` | string (email) | No |
| `grant_amount_requested` | number ($) | No |
| `grant_submission_deadline` | date | No |

### Section C: Educational Design (5 fields)
| Field | Type | Required |
|-------|------|----------|
| `learning_format` | string (select) | Yes |
| `duration_minutes` | number | No |
| `faculty_count` | number | No |
| `include_pre_test` | boolean | Yes |
| `include_post_test` | boolean | Yes |

### Section D: Clinical Focus (5 fields)
| Field | Type | Required |
|-------|------|----------|
| `clinical_topics` | string[] (tags) | Yes |
| `treatment_modalities` | string[] (multi) | No |
| `patient_population` | string (select) | No |
| `stage_of_disease` | string (select) | No |
| `comorbidities` | string[] (multi) | No |

### Section E: Educational Gaps (5 fields)
| Field | Type | Required |
|-------|------|----------|
| `knowledge_gaps` | string[] (tags) | No |
| `competence_gaps` | string[] (tags) | No |
| `performance_gaps` | string[] (tags) | No |
| `gap_evidence_sources` | string[] (multi) | No |
| `gap_priority` | string (high/med/low) | No |

### Section F: Outcomes & Measurement (5 fields)
| Field | Type | Required |
|-------|------|----------|
| `primary_outcomes` | string[] (multi) | No |
| `secondary_outcomes` | string[] (multi) | No |
| `measurement_approach` | string (select) | No |
| `moore_levels_target` | number[] (checkbox) | No |
| `follow_up_timeline` | string (select) | No |

### Section G: Content Requirements (5 fields)
| Field | Type | Required |
|-------|------|----------|
| `key_messages` | string[] (tags) | No |
| `required_references` | string[] (tags) | No |
| `excluded_topics` | string[] (tags) | No |
| `competitor_products_to_mention` | string[] (tags) | No |
| `regulatory_considerations` | string (select) | No |

### Section H: Logistics (5 fields)
| Field | Type | Required |
|-------|------|----------|
| `target_launch_date` | date | No |
| `expiration_date` | date | No |
| `distribution_channels` | string[] (multi) | No |
| `geo_restrictions` | string[] (multi) | No |
| `language_requirements` | string[] (multi) | No |

### Section I: Compliance & Disclosure (4 fields)
| Field | Type | Required |
|-------|------|----------|
| `accme_compliant` | boolean | Yes |
| `financial_disclosure_required` | boolean | Yes |
| `off_label_discussion` | boolean | Yes |
| `commercial_support_acknowledgment` | boolean | Yes |

### Section J: Additional (3 fields)
| Field | Type | Required |
|-------|------|----------|
| `special_instructions` | text | No |
| `reference_materials` | string[] (tags) | No |
| `internal_notes` | text | No |

---

## 2. Agent Output Structures (11 agents)

### Document Text Extraction Paths
| Agent | State Key | Document Text Path | Quality Score Path |
|-------|-----------|-------------------|-------------------|
| Research | `research_output` | `.research_document` | N/A |
| Clinical Practice | `clinical_output` | `.clinical_practice_document` | N/A |
| Gap Analysis | `gap_analysis_output` | `.gap_analysis_document` | N/A |
| Learning Objectives | `learning_objectives_output` | `.learning_objectives_document` | N/A |
| Needs Assessment | `needs_assessment_output` | `.complete_document` | `.quality_passed` (bool) |
| Curriculum Design | `curriculum_output` | `.curriculum_document` | N/A |
| Research Protocol | `protocol_output` | `.protocol_document` | N/A |
| Marketing Plan | `marketing_output` | `.marketing_document` | N/A |
| Grant Writer | `grant_package_output` | `.complete_document_markdown` | N/A |
| Prose Quality | `prose_quality_pass_1/2` | `.summary` | `.overall_score` (0-100) |
| Compliance | `compliance_result` | build from `.compliance_report` | `.compliance_report.overall_verdict` |

### Key Metrics Per Agent
| Agent | Metrics Available |
|-------|------------------|
| Research | `search_queries_executed`, `sources_reviewed`, `sources_cited`, `total_tokens`, `total_cost` |
| Clinical | `sources_analyzed`, `total_tokens`, `total_cost` |
| Gap Analysis | `gaps_identified`, `gaps_prioritized`, `total_tokens`, `total_cost` |
| Learning Objectives | `objectives_count`, `total_tokens`, `total_cost` |
| Needs Assessment | `word_count`, `section_word_counts`, `prose_density`, `character_appearances`, `total_tokens`, `total_cost` |
| Curriculum | `total_duration_minutes`, `active_learning_percentage`, `total_tokens`, `total_cost` |
| Protocol | `target_enrollment`, `study_duration_months`, `total_tokens`, `total_cost` |
| Marketing | `total_budget`, `projected_reach`, `cost_per_registration`, `total_tokens`, `total_cost` |
| Grant Writer | `sections_completed`, `total_tokens`, `total_cost` |
| Prose Quality | `overall_score`, `prose_density_score`, `ai_patterns_count`, `word_count_total` |
| Compliance | `remediation_required`, `overall_verdict`, `bias_issues`, `promotional_language` |

### Citation Sources (for `cme_source_references`)
| Agent | Citation Path | Format |
|-------|--------------|--------|
| Research | `.research_report.citations` | `[{title, authors, journal, pmid, year, doi, url}]` |
| Clinical | `.clinical_practice_report.citations` | Same format |
| Gap Analysis | `.gap_analysis_report.gaps[].evidence` | Evidence references within each gap |

---

## 3. Current Database State

### Existing Tables (6 CME tables)
- `cme_projects` — main project with JSONB `intake` and `outputs`
- `cme_agent_outputs` — individual outputs (5 rows for test project)
- `cme_review_assignments` — human review routing
- `cme_reviewer_config` — reviewer profiles
- `cme_lectures` — legacy
- `cme_segments` — legacy

### Columns Added This Session
- `cme_agent_outputs.document_text` (TEXT) — added
- `cme_agent_outputs.embedding` (vector(768)) — added
- `cme_agent_outputs.search_vector` (tsvector) — added

### Tables Still Needed
- `cme_documents` — versioned, immutable, compliance-ready documents
- `cme_intake_fields` — structured intake field extraction
- `cme_source_references` — literature and reference tracking

### Extensions Active
- `vector` 0.8.1 (pgvector)
- `pg_trgm` (just enabled)

### Available Embedding Model
- `nomic-embed-text:latest` on Ollama (localhost:11434), 768 dimensions, 261MB

---

## 4. Compliance Requirements

- **ACCME requires 7-year retention** of all CME materials used for a project
- Documents must be immutable (versioned, not overwritten)
- Source references must be cached (external URLs may go dead)
- `ON DELETE RESTRICT` prevents accidental data loss
- Audit trail: who created, when, what version

---

## 5. Pipeline Run Results (First Successful Run)

- **Thread:** `146808b7-0359-4971-ad5d-4b7b76361254`
- **Project:** `861ce1b2-a88c-4cfa-9d05-4d4591c39724` ("Advances in Immunotherapy for NSCLC")
- **Completed agents:** research, clinical, gap_analysis, learning_objectives, needs_assessment
- **Failed at:** prose_quality_pass_1 (score 85, needs_assessment word count 1696 < 3100 threshold)
- **Status:** `failed_human_intervention_required` after 3 retry cycles
- All 5 completed agent outputs synced to registry via `/sync` endpoint
