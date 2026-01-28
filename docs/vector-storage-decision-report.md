# Vector Storage Decision Report

## RECOMMENDATION
Use PostgreSQL (CR) + pgvector + LightRAG as unified solution.

## WHY
- Eliminates data duplication between CR and Onyx
- Costs $700/year vs $15k+ for separate databases
- Handles 50M vectors efficiently

## RESEARCH (2025)
- pgvectorscale: 28x better latency, 11.4x better QPS than Qdrant
- LightRAG: 40% cheaper than MS GraphRAG
- Qdrant: 20k GitHub stars, sub-10ms latency

## ARCHITECTURE
Single PostgreSQL contains CR + Onyx + vectors. No duplication.

## TIMELINE
Week 1: Add pgvector to CR
Week 2: Configure Onyx to use CR
Week 3: Test LightRAG  
Week 4: Production

Next: Implement Phase 1?
