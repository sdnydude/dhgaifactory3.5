import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

# Manual env loading since we might not have python-dotenv
def load_env_file(path):
    if not os.path.exists(path):
        return
    with open(path, "r") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val

load_env_file("../.env")

from agent import run_research

async def test():
    print("🚀 Starting Research Agent Cloud Verification...")
    print(f"LangSmith Project: {os.getenv('LANGSMITH_PROJECT')}")
    
    try:
        result = await run_research(
            topic="Type 2 Diabetes GLP-1 Cardiovascular Outcomes",
            therapeutic_area="Endocrinology",
            user_id="verification_bot_antigravity",
            output_format="gap_report"
        )
        print("\n✅ Run Completed!")
        print(f"Request ID: {result.get('request_id')}")
        print(f"Model Used: {result.get('model_used')}")
        print(f"Clinical Gaps Found: {len(result.get('clinical_gaps', []))}")
        print(f"Citations: {len(result.get('validated_citations', []))}")
        
        if "_rendered_output" in result:
            print(f"✓ Rendered Output Created ({len(result['_rendered_output'])} chars)")
            
    except Exception as e:
        print(f"\n❌ Run Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
