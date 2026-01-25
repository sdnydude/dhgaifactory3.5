"""
Test file saving functionality
"""
import sys
sys.path.insert(0, "./src")

from agent import save_research_output

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

# Verify files exist
import os
assert os.path.exists(md_path), f"MD file not found: {md_path}"
assert os.path.exists(txt_path), f"TXT file not found: {txt_path}"

# Verify content
with open(md_path, "r") as f:
    md_content = f.read()
    assert "Educational Need" in md_content
    print(f"✓ MD file content verified ({len(md_content)} chars)")

with open(txt_path, "r") as f:
    txt_content = f.read()
    assert "Educational Need" in txt_content
    print(f"✓ TXT file content verified ({len(txt_content)} chars)")

print("\n✅ All file saving tests passed!")
print(f"\nFiles saved in: ./outputs/")
