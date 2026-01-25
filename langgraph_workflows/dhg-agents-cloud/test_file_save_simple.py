"""
Simple test for file saving - standalone version
"""
import os
from datetime import datetime

def save_research_output(
    content: str,
    topic: str,
    output_format: str,
    file_format: str = "md",
    base_dir: str = "./outputs"
) -> str:
    """Save research output to file."""
    os.makedirs(base_dir, exist_ok=True)
    safe_topic = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in topic)
    safe_topic = safe_topic.replace(" ", "_").lower()[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_format}_{safe_topic}_{timestamp}.{file_format}"
    filepath = os.path.join(base_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath

# Test content
test_content = """# CME Activity Proposal: Test Topic

## Educational Need
Testing file saving functionality

## Content Outline
This is a test document
"""

# Test .md file (default)
print("Testing .md file saving...")
md_path = save_research_output(
    content=test_content,
    topic="Diabetes Management in Elderly Patients",
    output_format="cme_proposal",
    file_format="md"
)
print(f"✓ Saved .md file: {md_path}")

# Test .txt file
print("\nTesting .txt file saving...")
txt_path = save_research_output(
    content=test_content,
    topic="Chronic Cough Treatment",
    output_format="gap_report",
    file_format="txt"
)
print(f"✓ Saved .txt file: {txt_path}")

# Verify files
assert os.path.exists(md_path)
assert os.path.exists(txt_path)
assert md_path.endswith(".md")
assert txt_path.endswith(".txt")

print("\n✅ All file saving tests passed!")
print(f"\nCheck files in: ./outputs/")
