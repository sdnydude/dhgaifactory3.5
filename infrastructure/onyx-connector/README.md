# DHG Registry Connector for Onyx

Custom connector to sync CME content from DHG Registry to Onyx for RAG.

## Content Types Synced

| Type | Source Table | Description |
|------|--------------|-------------|
| References | `references` | Citations with abstracts, DOIs, evidence levels |
| Segments | `segments` | Needs assessments, scripts, curricula |
| Learning Objectives | `learning_objectives` | Moore levels, ICD-10, QI measures |
| Competitor Activities | `competitor_activities` | CME market intelligence |

## Usage

```python
from dhg_registry_connector import DHGRegistryConnector, sync_registry_to_onyx

# Test connector
connector = DHGRegistryConnector()
for doc in connector.load_from_state():
    print(doc.semantic_identifier)

# Sync to Onyx
stats = sync_registry_to_onyx(onyx_api_url="http://10.0.0.251:8088")
print(f"Synced {stats['documents_synced']} documents")
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REGISTRY_DB_HOST` | 10.0.0.251 | DHG Registry PostgreSQL host |
| `REGISTRY_DB_PASSWORD` | changeme | Database password |

## Architecture

```
DHG Registry (pgvector)
        ↓
  DHG Registry Connector (scheduled sync)
        ↓
    Onyx Ingestion API
        ↓
    Vespa (embeddings + search)
```
