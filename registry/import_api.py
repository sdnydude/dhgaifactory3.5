"""
Data Import API endpoints for LibreChat integration.

Provides file upload endpoints to import ChatGPT, Claude, and Gemini exports
directly from the LibreChat UI.
"""
import json
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/import", tags=["data-import"])

# Path to import scripts
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


class ImportStatus(BaseModel):
    """Import job status."""
    job_id: str
    status: str  # pending, running, completed, failed
    source: str
    message: str
    conversations_imported: Optional[int] = None
    messages_imported: Optional[int] = None


# In-memory job tracking (replace with Redis/DB for production)
import_jobs: dict[str, ImportStatus] = {}


def run_import_script(job_id: str, source: str, file_path: str, user_id: str, org_id: Optional[str]):
    """Background task to run import script."""
    try:
        import_jobs[job_id].status = "running"
        
        # Select script based on source
        script_map = {
            "chatgpt": SCRIPTS_DIR / "import_chatgpt.py",
            "claude": SCRIPTS_DIR / "import_claude.py",
            "gemini": SCRIPTS_DIR / "import_gemini.py",
        }
        
        script = script_map.get(source)
        if not script or not script.exists():
            raise ValueError(f"Unknown source or script not found: {source}")
        
        # Build command
        cmd = [
            "python3", str(script),
            "--input", file_path,
            "--user-id", user_id,
        ]
        if org_id:
            cmd.extend(["--org-id", org_id])
        
        # Run script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout
            env={
                **os.environ,
                "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "localhost"),
                "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            }
        )
        
        if result.returncode == 0:
            import_jobs[job_id].status = "completed"
            import_jobs[job_id].message = "Import completed successfully"
            
            # Try to parse counts from output
            output = result.stdout
            if "Imported" in output:
                try:
                    # Parse: "Imported X conversations, Y messages"
                    parts = output.split("Imported")[-1].split(",")
                    if len(parts) >= 2:
                        conv = int(''.join(filter(str.isdigit, parts[0])))
                        msg = int(''.join(filter(str.isdigit, parts[1])))
                        import_jobs[job_id].conversations_imported = conv
                        import_jobs[job_id].messages_imported = msg
                except:
                    pass
        else:
            import_jobs[job_id].status = "failed"
            import_jobs[job_id].message = f"Import failed: {result.stderr[:500]}"
            logger.error(f"Import failed for job {job_id}: {result.stderr}")
    
    except Exception as e:
        import_jobs[job_id].status = "failed"
        import_jobs[job_id].message = f"Error: {str(e)}"
        logger.exception(f"Import error for job {job_id}")
    
    finally:
        # Cleanup temp file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass


@router.post("/upload/{source}")
async def upload_and_import(
    source: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(...),
    organization_id: Optional[str] = Form(None),
):
    """
    Upload and import an AI conversation export file.
    
    Args:
        source: One of 'chatgpt', 'claude', 'gemini'
        file: The export file (ZIP for ChatGPT/Gemini, JSON for Claude)
        user_id: User UUID
        organization_id: Optional organization UUID
    
    Returns:
        ImportStatus with job_id for tracking
    """
    # Validate source
    if source not in ("chatgpt", "claude", "gemini"):
        raise HTTPException(400, f"Invalid source: {source}. Must be chatgpt, claude, or gemini")
    
    # Validate UUIDs
    try:
        uuid.UUID(user_id)
        if organization_id:
            uuid.UUID(organization_id)
    except ValueError:
        raise HTTPException(400, "Invalid UUID format")
    
    # Validate file extension
    filename = file.filename or "upload"
    if source in ("chatgpt", "gemini"):
        if not filename.endswith(".zip"):
            raise HTTPException(400, f"{source} exports must be ZIP files")
    elif source == "claude":
        if not filename.endswith(".json"):
            raise HTTPException(400, "Claude exports must be JSON files")
    
    # Save file to temp location
    job_id = str(uuid.uuid4())
    suffix = ".zip" if source in ("chatgpt", "gemini") else ".json"
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    
    try:
        shutil.copyfileobj(file.file, temp_file)
        temp_file.close()
        temp_path = temp_file.name
    except Exception as e:
        raise HTTPException(500, f"Failed to save uploaded file: {e}")
    
    # Create job status
    status = ImportStatus(
        job_id=job_id,
        status="pending",
        source=source,
        message=f"Import queued for {filename}"
    )
    import_jobs[job_id] = status
    
    # Queue background task
    background_tasks.add_task(
        run_import_script,
        job_id, source, temp_path, user_id, organization_id
    )
    
    return status


@router.get("/status/{job_id}")
async def get_import_status(job_id: str):
    """Get the status of an import job."""
    if job_id not in import_jobs:
        raise HTTPException(404, f"Job not found: {job_id}")
    return import_jobs[job_id]


@router.get("/jobs")
async def list_import_jobs(user_id: Optional[str] = None, limit: int = 20):
    """List recent import jobs."""
    jobs = list(import_jobs.values())[-limit:]
    return {"jobs": jobs}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a completed/failed job from history."""
    if job_id in import_jobs:
        del import_jobs[job_id]
        return {"deleted": True}
    raise HTTPException(404, f"Job not found: {job_id}")
