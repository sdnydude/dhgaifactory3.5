"""
DHG CME Research Agent - Feedback & Continuous Improvement Loop
================================================================

Implements the full feedback cycle:
BUILD → DEPLOY → OBSERVE → EVALUATE → ITERATE

Components:
1. FeedbackCollector - Collect feedback from multiple sources
2. EvaluationDataset - Test cases with expected outputs
3. QualityEvaluator - Automated quality checks
4. ImprovementTracker - Track improvements over time

Author: Digital Harmony Group
Version: 1.0.0
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass, field
from enum import Enum

from langsmith import Client as LangSmithClient
from langsmith.schemas import Run, Feedback
from langsmith.evaluation import evaluate
import httpx


# =============================================================================
# FEEDBACK TYPES
# =============================================================================

class FeedbackSource(Enum):
    """Where feedback originated"""
    USER_MANUAL = "user_manual"           # User clicked thumbs up/down
    USER_COMMENT = "user_comment"         # User provided written feedback
    AUTOMATED_EVAL = "automated_eval"     # Automated quality check
    EXPERT_REVIEW = "expert_review"       # Medical expert review
    SYSTEM_METRIC = "system_metric"       # System-level metrics (latency, cost)


class QualityDimension(Enum):
    """What aspect of quality is being rated"""
    OVERALL = "overall"
    EVIDENCE_QUALITY = "evidence_quality"       # Are citations high-quality?
    SYNTHESIS_ACCURACY = "synthesis_accuracy"   # Is synthesis accurate to sources?
    GAP_IDENTIFICATION = "gap_identification"   # Are gaps correctly identified?
    CLINICAL_RELEVANCE = "clinical_relevance"   # Is content clinically relevant?
    CITATION_VALIDITY = "citation_validity"     # Are citations valid/accessible?
    COMPLETENESS = "completeness"               # Is response complete?
    CME_COMPLIANCE = "cme_compliance"           # Meets CME standards?


@dataclass
class FeedbackEntry:
    """Structured feedback entry"""
    run_id: str
    score: float  # 0.0 to 1.0
    dimension: QualityDimension = QualityDimension.OVERALL
    source: FeedbackSource = FeedbackSource.USER_MANUAL
    comment: Optional[str] = None
    issues: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_langsmith_feedback(self) -> dict:
        """Convert to LangSmith feedback format"""
        return {
            "run_id": self.run_id,
            "key": self.dimension.value,
            "score": self.score,
            "comment": json.dumps({
                "text": self.comment,
                "issues": self.issues,
                "source": self.source.value,
                "metadata": self.metadata
            })
        }


# =============================================================================
# FEEDBACK COLLECTOR
# =============================================================================

class FeedbackCollector:
    """
    Collects feedback from multiple sources and submits to LangSmith.
    
    Sources:
    - Direct API calls
    - MCP Server
    - LibreChat UI
    - Automated evaluations
    """
    
    def __init__(self, project_name: str = "dhg-cme-research-agent"):
        self.client = LangSmithClient()
        self.project_name = project_name
        self._feedback_buffer: List[FeedbackEntry] = []
    
    def submit_feedback(
        self,
        run_id: str,
        score: float,
        dimension: QualityDimension = QualityDimension.OVERALL,
        source: FeedbackSource = FeedbackSource.USER_MANUAL,
        comment: Optional[str] = None,
        issues: Optional[List[str]] = None
    ) -> str:
        """
        Submit feedback to LangSmith.
        
        Args:
            run_id: LangSmith run ID
            score: Quality score 0.0 (bad) to 1.0 (excellent)
            dimension: What aspect is being rated
            source: Where feedback came from
            comment: Optional text comment
            issues: Optional list of specific issues
        
        Returns:
            Feedback ID
        """
        entry = FeedbackEntry(
            run_id=run_id,
            score=score,
            dimension=dimension,
            source=source,
            comment=comment,
            issues=issues or []
        )
        
        feedback = self.client.create_feedback(**entry.to_langsmith_feedback())
        return feedback.id
    
    def submit_thumbs(self, run_id: str, thumbs_up: bool, comment: Optional[str] = None) -> str:
        """Simple thumbs up/down feedback"""
        return self.submit_feedback(
            run_id=run_id,
            score=1.0 if thumbs_up else 0.0,
            source=FeedbackSource.USER_MANUAL,
            comment=comment
        )
    
    def submit_multi_dimension(
        self,
        run_id: str,
        scores: Dict[QualityDimension, float],
        source: FeedbackSource = FeedbackSource.EXPERT_REVIEW,
        comment: Optional[str] = None
    ) -> List[str]:
        """Submit feedback across multiple quality dimensions"""
        feedback_ids = []
        for dimension, score in scores.items():
            fid = self.submit_feedback(
                run_id=run_id,
                score=score,
                dimension=dimension,
                source=source,
                comment=comment
            )
            feedback_ids.append(fid)
        return feedback_ids
    
    def get_run_feedback(self, run_id: str) -> List[dict]:
        """Get all feedback for a run"""
        feedbacks = self.client.list_feedback(run_ids=[run_id])
        return [
            {
                "id": f.id,
                "key": f.key,
                "score": f.score,
                "comment": f.comment,
                "created_at": f.created_at
            }
            for f in feedbacks
        ]
    
    def get_feedback_summary(self, days: int = 7) -> dict:
        """Get feedback summary for recent runs"""
        runs = self.client.list_runs(
            project_name=self.project_name,
            start_time=datetime.utcnow() - timedelta(days=days)
        )
        
        total_runs = 0
        feedback_counts = {"positive": 0, "negative": 0, "neutral": 0}
        dimension_scores = {d.value: [] for d in QualityDimension}
        
        for run in runs:
            total_runs += 1
            feedbacks = list(self.client.list_feedback(run_ids=[run.id]))
            
            for f in feedbacks:
                if f.score is not None:
                    if f.score >= 0.7:
                        feedback_counts["positive"] += 1
                    elif f.score <= 0.3:
                        feedback_counts["negative"] += 1
                    else:
                        feedback_counts["neutral"] += 1
                    
                    if f.key in dimension_scores:
                        dimension_scores[f.key].append(f.score)
        
        return {
            "period_days": days,
            "total_runs": total_runs,
            "feedback_counts": feedback_counts,
            "dimension_averages": {
                k: sum(v) / len(v) if v else None
                for k, v in dimension_scores.items()
            }
        }


# =============================================================================
# EVALUATION DATASET
# =============================================================================

@dataclass
class EvaluationCase:
    """Single evaluation test case"""
    id: str
    name: str
    description: str
    
    # Input to the agent
    input: Dict[str, Any]
    
    # Expected output characteristics (not exact match)
    expected: Dict[str, Any]
    
    # Tags for filtering
    tags: List[str] = field(default_factory=list)
    
    # Difficulty level
    difficulty: Literal["easy", "medium", "hard"] = "medium"


class EvaluationDataset:
    """
    Manages evaluation test cases for the CME Research Agent.
    
    Test cases define:
    - Input parameters
    - Expected output characteristics
    - Quality criteria
    """
    
    # Built-in test cases for CME Research Agent
    BUILTIN_CASES = [
        EvaluationCase(
            id="cc-001",
            name="Chronic Cough Gap Analysis",
            description="Standard gap analysis for chronic cough - should find refractory treatment gaps",
            input={
                "topic": "chronic cough refractory treatment",
                "therapeutic_area": "pulmonology",
                "query_type": "gap_analysis",
                "target_audience": "primary_care",
                "date_range_years": 5
            },
            expected={
                "min_citations": 5,
                "max_citations": 50,
                "has_clinical_gaps": True,
                "min_gaps": 2,
                "evidence_levels_include": ["systematic_review_meta_analysis", "high_quality_rct"],
                "synthesis_min_words": 200,
                "must_mention": ["cough", "treatment", "refractory"]
            },
            tags=["pulmonology", "gap_analysis", "gsk-grant"],
            difficulty="medium"
        ),
        EvaluationCase(
            id="dm-001",
            name="Type 2 Diabetes Needs Assessment",
            description="Needs assessment for T2DM management updates",
            input={
                "topic": "type 2 diabetes GLP-1 receptor agonists",
                "therapeutic_area": "endocrinology",
                "query_type": "needs_assessment",
                "target_audience": "primary_care",
                "date_range_years": 3
            },
            expected={
                "min_citations": 8,
                "has_clinical_gaps": True,
                "evidence_levels_include": ["systematic_review_meta_analysis"],
                "synthesis_min_words": 300,
                "must_mention": ["GLP-1", "diabetes", "glycemic"]
            },
            tags=["endocrinology", "needs_assessment"],
            difficulty="medium"
        ),
        EvaluationCase(
            id="onc-001",
            name="Immunotherapy Literature Review",
            description="Complex oncology literature review - high difficulty",
            input={
                "topic": "checkpoint inhibitor immunotherapy resistance mechanisms",
                "therapeutic_area": "oncology",
                "query_type": "literature_review",
                "target_audience": "specialist",
                "date_range_years": 3
            },
            expected={
                "min_citations": 10,
                "has_key_findings": True,
                "min_findings": 3,
                "evidence_levels_include": ["systematic_review_meta_analysis", "high_quality_rct"],
                "synthesis_min_words": 400,
                "must_mention": ["checkpoint", "resistance", "PD-1", "immunotherapy"]
            },
            tags=["oncology", "literature_review", "complex"],
            difficulty="hard"
        ),
        EvaluationCase(
            id="edge-001",
            name="Rare Disease - Limited Evidence",
            description="Edge case - rare disease with limited peer-reviewed evidence",
            input={
                "topic": "Erdheim-Chester disease treatment",
                "therapeutic_area": "hematology",
                "query_type": "literature_review",
                "target_audience": "specialist",
                "date_range_years": 10
            },
            expected={
                "min_citations": 1,  # May be limited
                "max_citations": 20,
                "handles_limited_evidence": True,
                "synthesis_min_words": 100
            },
            tags=["rare_disease", "edge_case", "limited_evidence"],
            difficulty="hard"
        ),
        EvaluationCase(
            id="fast-001",
            name="Quick Podcast Content",
            description="Fast turnaround podcast content generation",
            input={
                "topic": "hypertension management updates 2024",
                "therapeutic_area": "cardiology",
                "query_type": "podcast_content",
                "target_audience": "primary_care",
                "date_range_years": 2
            },
            expected={
                "min_citations": 3,
                "has_key_findings": True,
                "synthesis_min_words": 150,
                "must_mention": ["blood pressure", "hypertension"]
            },
            tags=["cardiology", "podcast", "quick"],
            difficulty="easy"
        )
    ]
    
    def __init__(self, langsmith_client: Optional[LangSmithClient] = None):
        self.client = langsmith_client or LangSmithClient()
        self.cases = {c.id: c for c in self.BUILTIN_CASES}
    
    def get_case(self, case_id: str) -> Optional[EvaluationCase]:
        """Get a specific test case"""
        return self.cases.get(case_id)
    
    def get_cases_by_tag(self, tag: str) -> List[EvaluationCase]:
        """Get all cases with a specific tag"""
        return [c for c in self.cases.values() if tag in c.tags]
    
    def get_cases_by_difficulty(self, difficulty: str) -> List[EvaluationCase]:
        """Get all cases of a specific difficulty"""
        return [c for c in self.cases.values() if c.difficulty == difficulty]
    
    def add_case(self, case: EvaluationCase) -> None:
        """Add a custom test case"""
        self.cases[case.id] = case
    
    def create_langsmith_dataset(self, name: str = "cme-research-eval") -> str:
        """Create/update LangSmith dataset from test cases"""
        # Check if dataset exists
        datasets = list(self.client.list_datasets(dataset_name=name))
        
        if datasets:
            dataset = datasets[0]
        else:
            dataset = self.client.create_dataset(
                dataset_name=name,
                description="Evaluation dataset for DHG CME Research Agent"
            )
        
        # Add examples
        for case in self.cases.values():
            self.client.create_example(
                inputs=case.input,
                outputs=case.expected,
                dataset_id=dataset.id,
                metadata={
                    "case_id": case.id,
                    "name": case.name,
                    "difficulty": case.difficulty,
                    "tags": case.tags
                }
            )
        
        return dataset.id
    
    def export_cases(self) -> List[dict]:
        """Export all cases as JSON-serializable dicts"""
        return [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "input": c.input,
                "expected": c.expected,
                "tags": c.tags,
                "difficulty": c.difficulty
            }
            for c in self.cases.values()
        ]


# =============================================================================
# QUALITY EVALUATOR
# =============================================================================

class QualityEvaluator:
    """
    Automated quality evaluation for research agent outputs.
    
    Evaluates:
    - Citation quality and count
    - Synthesis accuracy
    - Gap identification
    - CME compliance
    """
    
    def __init__(self):
        self.feedback_collector = FeedbackCollector()
    
    def evaluate_result(
        self,
        result: Dict[str, Any],
        expected: Dict[str, Any],
        run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate agent result against expected criteria.
        
        Returns:
            Evaluation scores and details
        """
        scores = {}
        issues = []
        
        # Citation count
        citations = result.get("validated_citations", [])
        citation_count = len(citations)
        
        if "min_citations" in expected:
            if citation_count >= expected["min_citations"]:
                scores["citation_count"] = 1.0
            else:
                scores["citation_count"] = citation_count / expected["min_citations"]
                issues.append(f"Only {citation_count} citations, expected {expected['min_citations']}+")
        
        if "max_citations" in expected and citation_count > expected["max_citations"]:
            issues.append(f"Too many citations: {citation_count} > {expected['max_citations']}")
        
        # Evidence levels
        if "evidence_levels_include" in expected:
            found_levels = set(c.get("evidence_level") for c in citations)
            expected_levels = set(expected["evidence_levels_include"])
            overlap = found_levels & expected_levels
            if expected_levels:
                scores["evidence_quality"] = len(overlap) / len(expected_levels)
                if not overlap:
                    issues.append(f"No high-quality evidence found (expected: {expected_levels})")
        
        # Clinical gaps
        clinical_gaps = result.get("clinical_gaps", [])
        if expected.get("has_clinical_gaps"):
            if clinical_gaps:
                scores["gap_identification"] = 1.0
                if "min_gaps" in expected and len(clinical_gaps) < expected["min_gaps"]:
                    scores["gap_identification"] = len(clinical_gaps) / expected["min_gaps"]
                    issues.append(f"Only {len(clinical_gaps)} gaps, expected {expected['min_gaps']}+")
            else:
                scores["gap_identification"] = 0.0
                issues.append("No clinical gaps identified")
        
        # Key findings
        key_findings = result.get("key_findings", [])
        if expected.get("has_key_findings"):
            if key_findings:
                scores["findings"] = 1.0
                if "min_findings" in expected and len(key_findings) < expected["min_findings"]:
                    scores["findings"] = len(key_findings) / expected["min_findings"]
            else:
                scores["findings"] = 0.0
                issues.append("No key findings extracted")
        
        # Synthesis quality
        synthesis = result.get("synthesis", "")
        word_count = len(synthesis.split())
        
        if "synthesis_min_words" in expected:
            if word_count >= expected["synthesis_min_words"]:
                scores["synthesis_completeness"] = 1.0
            else:
                scores["synthesis_completeness"] = word_count / expected["synthesis_min_words"]
                issues.append(f"Synthesis too short: {word_count} words, expected {expected['synthesis_min_words']}+")
        
        # Must mention terms
        if "must_mention" in expected:
            synthesis_lower = synthesis.lower()
            mentioned = sum(1 for term in expected["must_mention"] if term.lower() in synthesis_lower)
            scores["relevance"] = mentioned / len(expected["must_mention"])
            missing = [t for t in expected["must_mention"] if t.lower() not in synthesis_lower]
            if missing:
                issues.append(f"Missing required terms: {missing}")
        
        # Overall score
        if scores:
            overall = sum(scores.values()) / len(scores)
        else:
            overall = 0.5  # Neutral if no criteria
        
        scores["overall"] = overall
        
        # Submit feedback to LangSmith if run_id provided
        if run_id:
            for dimension_name, score in scores.items():
                try:
                    dimension = QualityDimension(dimension_name)
                except ValueError:
                    dimension = QualityDimension.OVERALL
                
                self.feedback_collector.submit_feedback(
                    run_id=run_id,
                    score=score,
                    dimension=dimension,
                    source=FeedbackSource.AUTOMATED_EVAL,
                    issues=issues if dimension_name == "overall" else None
                )
        
        return {
            "scores": scores,
            "overall": overall,
            "passed": overall >= 0.7,
            "issues": issues,
            "citation_count": citation_count,
            "gap_count": len(clinical_gaps),
            "finding_count": len(key_findings),
            "synthesis_words": word_count
        }
    
    async def run_evaluation_suite(
        self,
        agent_func,
        dataset: EvaluationDataset,
        case_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run evaluation suite against multiple test cases.
        
        Args:
            agent_func: Async function to run agent (e.g., run_research)
            dataset: Evaluation dataset
            case_ids: Specific case IDs to run (or None for all)
            tags: Filter by tags
        
        Returns:
            Suite results with per-case and aggregate scores
        """
        # Select cases
        if case_ids:
            cases = [dataset.get_case(cid) for cid in case_ids if dataset.get_case(cid)]
        elif tags:
            cases = []
            for tag in tags:
                cases.extend(dataset.get_cases_by_tag(tag))
            cases = list({c.id: c for c in cases}.values())  # Dedupe
        else:
            cases = list(dataset.cases.values())
        
        results = []
        for case in cases:
            try:
                # Run agent
                agent_result = await agent_func(**case.input)
                
                # Get run_id from result if available
                run_id = agent_result.get("_run_id")
                
                # Evaluate
                eval_result = self.evaluate_result(
                    result=agent_result,
                    expected=case.expected,
                    run_id=run_id
                )
                
                results.append({
                    "case_id": case.id,
                    "case_name": case.name,
                    "difficulty": case.difficulty,
                    "passed": eval_result["passed"],
                    "overall_score": eval_result["overall"],
                    "scores": eval_result["scores"],
                    "issues": eval_result["issues"]
                })
                
            except Exception as e:
                results.append({
                    "case_id": case.id,
                    "case_name": case.name,
                    "difficulty": case.difficulty,
                    "passed": False,
                    "overall_score": 0.0,
                    "error": str(e)
                })
        
        # Aggregate
        passed_count = sum(1 for r in results if r["passed"])
        total_count = len(results)
        avg_score = sum(r["overall_score"] for r in results) / total_count if total_count else 0
        
        return {
            "summary": {
                "total_cases": total_count,
                "passed": passed_count,
                "failed": total_count - passed_count,
                "pass_rate": passed_count / total_count if total_count else 0,
                "average_score": avg_score
            },
            "by_difficulty": {
                diff: {
                    "count": len([r for r in results if r.get("difficulty") == diff]),
                    "passed": len([r for r in results if r.get("difficulty") == diff and r["passed"]]),
                    "avg_score": sum(r["overall_score"] for r in results if r.get("difficulty") == diff) / 
                               max(1, len([r for r in results if r.get("difficulty") == diff]))
                }
                for diff in ["easy", "medium", "hard"]
            },
            "results": results
        }


# =============================================================================
# IMPROVEMENT TRACKER
# =============================================================================

class ImprovementTracker:
    """
    Tracks improvements over time and identifies patterns.
    
    Analyzes:
    - Score trends
    - Common failure patterns
    - Improvement opportunities
    """
    
    def __init__(self, project_name: str = "dhg-cme-research-agent"):
        self.client = LangSmithClient()
        self.project_name = project_name
        self.feedback_collector = FeedbackCollector(project_name)
    
    def get_score_trend(self, days: int = 30, dimension: str = "overall") -> List[dict]:
        """Get score trend over time"""
        runs = list(self.client.list_runs(
            project_name=self.project_name,
            start_time=datetime.utcnow() - timedelta(days=days)
        ))
        
        daily_scores = {}
        for run in runs:
            date_key = run.start_time.strftime("%Y-%m-%d")
            feedbacks = list(self.client.list_feedback(run_ids=[run.id]))
            
            for f in feedbacks:
                if f.key == dimension and f.score is not None:
                    if date_key not in daily_scores:
                        daily_scores[date_key] = []
                    daily_scores[date_key].append(f.score)
        
        return [
            {
                "date": date,
                "avg_score": sum(scores) / len(scores),
                "count": len(scores),
                "min": min(scores),
                "max": max(scores)
            }
            for date, scores in sorted(daily_scores.items())
        ]
    
    def identify_failure_patterns(self, days: int = 14) -> Dict[str, Any]:
        """Identify common failure patterns from feedback"""
        runs = list(self.client.list_runs(
            project_name=self.project_name,
            start_time=datetime.utcnow() - timedelta(days=days)
        ))
        
        issue_counts = {}
        low_score_dimensions = {}
        failure_inputs = []
        
        for run in runs:
            feedbacks = list(self.client.list_feedback(run_ids=[run.id]))
            
            for f in feedbacks:
                # Track low scores by dimension
                if f.score is not None and f.score < 0.5:
                    if f.key not in low_score_dimensions:
                        low_score_dimensions[f.key] = 0
                    low_score_dimensions[f.key] += 1
                
                # Parse issues from comments
                if f.comment:
                    try:
                        comment_data = json.loads(f.comment)
                        for issue in comment_data.get("issues", []):
                            if issue not in issue_counts:
                                issue_counts[issue] = 0
                            issue_counts[issue] += 1
                    except json.JSONDecodeError:
                        pass
                
                # Track failing inputs
                if f.score is not None and f.score < 0.3:
                    failure_inputs.append({
                        "run_id": str(run.id),
                        "inputs": run.inputs,
                        "score": f.score,
                        "dimension": f.key
                    })
        
        return {
            "common_issues": sorted(issue_counts.items(), key=lambda x: -x[1])[:10],
            "weak_dimensions": sorted(low_score_dimensions.items(), key=lambda x: -x[1]),
            "failure_examples": failure_inputs[:5],
            "recommendations": self._generate_recommendations(issue_counts, low_score_dimensions)
        }
    
    def _generate_recommendations(
        self,
        issue_counts: Dict[str, int],
        low_score_dimensions: Dict[str, int]
    ) -> List[str]:
        """Generate improvement recommendations based on patterns"""
        recommendations = []
        
        # Check for citation issues
        citation_issues = [k for k in issue_counts if "citation" in k.lower()]
        if citation_issues:
            recommendations.append(
                "CITATION QUALITY: Consider expanding PubMed search terms or adjusting evidence level filters"
            )
        
        # Check for gap identification issues
        if low_score_dimensions.get("gap_identification", 0) > 3:
            recommendations.append(
                "GAP IDENTIFICATION: Review synthesis prompt - may need more explicit gap extraction instructions"
            )
        
        # Check for synthesis issues
        if low_score_dimensions.get("synthesis_completeness", 0) > 3:
            recommendations.append(
                "SYNTHESIS DEPTH: Increase max_tokens for synthesis step or adjust prompt for more detail"
            )
        
        # Check for relevance issues
        missing_terms = [k for k in issue_counts if "Missing required terms" in k]
        if missing_terms:
            recommendations.append(
                "RELEVANCE: Agent may be going off-topic - consider adding relevance guardrails"
            )
        
        # Check for evidence quality
        if low_score_dimensions.get("evidence_quality", 0) > 3:
            recommendations.append(
                "EVIDENCE QUALITY: Tighten evidence level filters or expand date range for more high-quality sources"
            )
        
        if not recommendations:
            recommendations.append("No major issues detected - continue monitoring")
        
        return recommendations
    
    def generate_improvement_report(self, days: int = 14) -> Dict[str, Any]:
        """Generate comprehensive improvement report"""
        trend = self.get_score_trend(days=days)
        patterns = self.identify_failure_patterns(days=days)
        summary = self.feedback_collector.get_feedback_summary(days=days)
        
        # Calculate trend direction
        if len(trend) >= 2:
            recent_avg = sum(t["avg_score"] for t in trend[-3:]) / min(3, len(trend))
            earlier_avg = sum(t["avg_score"] for t in trend[:3]) / min(3, len(trend))
            trend_direction = "improving" if recent_avg > earlier_avg else "declining" if recent_avg < earlier_avg else "stable"
        else:
            trend_direction = "insufficient_data"
        
        return {
            "report_date": datetime.utcnow().isoformat(),
            "period_days": days,
            "overall_health": {
                "trend_direction": trend_direction,
                "average_score": sum(t["avg_score"] for t in trend) / len(trend) if trend else None,
                "total_runs": summary["total_runs"],
                "feedback_ratio": summary["feedback_counts"]
            },
            "score_trend": trend,
            "failure_patterns": patterns,
            "dimension_health": summary["dimension_averages"],
            "action_items": patterns["recommendations"]
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Initialize global instances
feedback_collector = FeedbackCollector()
evaluation_dataset = EvaluationDataset()
quality_evaluator = QualityEvaluator()
improvement_tracker = ImprovementTracker()


def submit_feedback(run_id: str, score: float, comment: Optional[str] = None) -> str:
    """Quick feedback submission"""
    return feedback_collector.submit_feedback(run_id, score, comment=comment)


def thumbs_up(run_id: str, comment: Optional[str] = None) -> str:
    """Submit positive feedback"""
    return feedback_collector.submit_thumbs(run_id, thumbs_up=True, comment=comment)


def thumbs_down(run_id: str, comment: Optional[str] = None) -> str:
    """Submit negative feedback"""
    return feedback_collector.submit_thumbs(run_id, thumbs_up=False, comment=comment)


def get_improvement_report(days: int = 14) -> Dict[str, Any]:
    """Get improvement report"""
    return improvement_tracker.generate_improvement_report(days=days)


async def run_eval_suite(agent_func, tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run evaluation suite"""
    return await quality_evaluator.run_evaluation_suite(
        agent_func=agent_func,
        dataset=evaluation_dataset,
        tags=tags
    )
