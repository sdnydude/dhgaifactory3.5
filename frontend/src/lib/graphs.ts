export interface GraphInfo {
  id: string;
  label: string;
  description: string;
  category: "agent" | "orchestrator";
}

export const GRAPHS: GraphInfo[] = [
  {
    id: "needs_assessment",
    label: "Needs Assessment",
    description: "Cold open framework analysis with 3100+ word validation",
    category: "agent",
  },
  {
    id: "research",
    label: "Research",
    description: "Literature and PubMed queries with 30+ sources",
    category: "agent",
  },
  {
    id: "clinical_practice",
    label: "Clinical Practice",
    description: "Barrier identification and standard-of-care analysis",
    category: "agent",
  },
  {
    id: "gap_analysis",
    label: "Gap Analysis",
    description: "Evidence-based gaps with quantification",
    category: "agent",
  },
  {
    id: "learning_objectives",
    label: "Learning Objectives",
    description: "Moore's Expanded Framework mapping",
    category: "agent",
  },
  {
    id: "curriculum_design",
    label: "Curriculum Design",
    description: "Educational design with innovation section",
    category: "agent",
  },
  {
    id: "research_protocol",
    label: "Research Protocol",
    description: "IRB-ready outcomes protocol",
    category: "agent",
  },
  {
    id: "marketing_plan",
    label: "Marketing Plan",
    description: "Audience strategy and channel budget",
    category: "agent",
  },
  {
    id: "grant_writer",
    label: "Grant Writer",
    description: "Full grant package assembly",
    category: "agent",
  },
  {
    id: "prose_quality",
    label: "Prose Quality",
    description: "De-AI-ification scoring and banned pattern detection",
    category: "agent",
  },
  {
    id: "compliance_review",
    label: "Compliance Review",
    description: "ACCME verification",
    category: "agent",
  },
  {
    id: "needs_package",
    label: "Needs Package",
    description:
      "Research + Clinical parallel, Gap, LO, Needs, Prose QA, Human Review",
    category: "orchestrator",
  },
  {
    id: "curriculum_package",
    label: "Curriculum Package",
    description:
      "Needs Package + Curriculum + Protocol + Marketing parallel, Human Review",
    category: "orchestrator",
  },
  {
    id: "grant_package",
    label: "Grant Package",
    description:
      "Full 11 agents, Prose QA 2 passes, Compliance gate, Human Review",
    category: "orchestrator",
  },
];
