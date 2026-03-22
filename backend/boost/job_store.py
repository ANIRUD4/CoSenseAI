"""
backend/boost/job_store.py

In-memory job tracking for boost pipeline jobs.
The companion app polls GET /boost/status/{job_id} to show a progress bar.

Job lifecycle:
  pending → running → done | failed
"""

import time
import uuid
from typing import Dict, Optional


_JOBS: Dict[str, dict] = {}


def create_job(label: str) -> str:
    """Create a new job and return its ID."""
    job_id = str(uuid.uuid4())[:8]
    _JOBS[job_id] = {
        "job_id":    job_id,
        "label":     label,
        "status":    "pending",    # pending | running | done | failed
        "progress":  0,
        "total":     0,
        "added":     0,
        "message":   "Initialising boost pipeline...",
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    return job_id


def update_job(
    job_id: str,
    *,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    total: Optional[int] = None,
    added: Optional[int] = None,
    message: Optional[str] = None,
):
    """Update fields on an existing job."""
    job = _JOBS.get(job_id)
    if job is None:
        return
    if status   is not None: job["status"]   = status
    if progress is not None: job["progress"] = progress
    if total    is not None: job["total"]    = total
    if added    is not None: job["added"]    = added
    if message  is not None: job["message"]  = message
    job["updated_at"] = time.time()


def get_job(job_id: str) -> Optional[dict]:
    """Return the job dict or None."""
    return _JOBS.get(job_id)


def list_jobs() -> list:
    """Return all jobs sorted by creation time (newest first)."""
    return sorted(_JOBS.values(), key=lambda j: j["created_at"], reverse=True)
