"""Put the template's `src/` on sys.path, matching how agents are imported in
`langgraph_workflows/dhg-agents-cloud/src/` (flat module namespace, with
`prompts` as a package inside it)."""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
