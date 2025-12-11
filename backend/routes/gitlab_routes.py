"""
GitLab Integration Routes
Fetches pipeline status, deployments, and project info from GitLab API.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import httpx
import logging

from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/gitlab", tags=["gitlab"])

# GitLab Configuration from settings
GITLAB_URL = settings.GITLAB_URL
GITLAB_PROJECT_ID = settings.GITLAB_PROJECT_ID
GITLAB_TOKEN = settings.GITLAB_TOKEN


class PipelineInfo(BaseModel):
    id: int
    status: str  # running, pending, success, failed, canceled, skipped
    ref: str  # branch name
    sha: str  # commit SHA (short)
    web_url: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration: Optional[int] = None  # seconds
    source: str  # push, web, trigger, schedule, api, etc.


class JobInfo(BaseModel):
    id: int
    name: str
    stage: str
    status: str
    web_url: str
    duration: Optional[float] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class DeploymentInfo(BaseModel):
    id: int
    status: str
    environment: str
    ref: str
    sha: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    deployed_by: Optional[str] = None


class CommitInfo(BaseModel):
    sha: str
    short_sha: str
    title: str
    author_name: str
    authored_date: datetime
    web_url: str


class GitLabStatusResponse(BaseModel):
    connected: bool
    project_name: Optional[str] = None
    project_url: Optional[str] = None
    default_branch: Optional[str] = None
    latest_pipeline: Optional[PipelineInfo] = None
    latest_commit: Optional[CommitInfo] = None
    recent_pipelines: List[PipelineInfo] = []
    pipeline_jobs: List[JobInfo] = []
    latest_deployment: Optional[DeploymentInfo] = None
    error: Optional[str] = None


async def fetch_gitlab_api(endpoint: str) -> dict:
    """Fetch data from GitLab API"""
    if not GITLAB_TOKEN or not GITLAB_PROJECT_ID:
        raise HTTPException(
            status_code=503,
            detail="GitLab integration not configured. Set GITLAB_TOKEN and GITLAB_PROJECT_ID."
        )

    # URL encode the project ID if it contains slashes
    project_id = GITLAB_PROJECT_ID.replace("/", "%2F")
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}{endpoint}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"PRIVATE-TOKEN": GITLAB_TOKEN},
            timeout=10.0
        )

        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="GitLab authentication failed")
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="GitLab project not found")
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"GitLab API error: {response.text}"
            )

        return response.json()


@router.get("/status", response_model=GitLabStatusResponse)
async def get_gitlab_status():
    """
    Get comprehensive GitLab project status including:
    - Project info
    - Latest pipeline status
    - Recent pipelines
    - Latest commit
    - Latest deployment
    """
    if not GITLAB_TOKEN or not GITLAB_PROJECT_ID:
        return GitLabStatusResponse(
            connected=False,
            error="GitLab integration not configured"
        )

    try:
        # Fetch project info
        project = await fetch_gitlab_api("")

        # Fetch latest pipelines
        pipelines_data = await fetch_gitlab_api("/pipelines?per_page=5")

        recent_pipelines = []
        latest_pipeline = None
        pipeline_jobs = []

        for p in pipelines_data:
            pipeline = PipelineInfo(
                id=p["id"],
                status=p["status"],
                ref=p["ref"],
                sha=p["sha"][:8],
                web_url=p["web_url"],
                created_at=p["created_at"],
                updated_at=p.get("updated_at"),
                source=p.get("source", "unknown")
            )
            recent_pipelines.append(pipeline)

        if recent_pipelines:
            latest_pipeline = recent_pipelines[0]

            # Fetch jobs for latest pipeline
            try:
                jobs_data = await fetch_gitlab_api(f"/pipelines/{latest_pipeline.id}/jobs")
                for j in jobs_data:
                    pipeline_jobs.append(JobInfo(
                        id=j["id"],
                        name=j["name"],
                        stage=j["stage"],
                        status=j["status"],
                        web_url=j["web_url"],
                        duration=j.get("duration"),
                        started_at=j.get("started_at"),
                        finished_at=j.get("finished_at")
                    ))
            except Exception as e:
                logger.warning(f"Failed to fetch pipeline jobs: {e}")

        # Fetch latest commit
        latest_commit = None
        try:
            commits_data = await fetch_gitlab_api("/repository/commits?per_page=1")
            if commits_data:
                c = commits_data[0]
                latest_commit = CommitInfo(
                    sha=c["id"],
                    short_sha=c["short_id"],
                    title=c["title"],
                    author_name=c["author_name"],
                    authored_date=c["authored_date"],
                    web_url=c["web_url"]
                )
        except Exception as e:
            logger.warning(f"Failed to fetch commits: {e}")

        # Fetch latest deployment
        latest_deployment = None
        try:
            deployments_data = await fetch_gitlab_api("/deployments?per_page=1&status=success")
            if deployments_data:
                d = deployments_data[0]
                latest_deployment = DeploymentInfo(
                    id=d["id"],
                    status=d["status"],
                    environment=d["environment"]["name"] if d.get("environment") else "unknown",
                    ref=d["ref"],
                    sha=d["sha"][:8],
                    created_at=d["created_at"],
                    updated_at=d.get("updated_at"),
                    deployed_by=d.get("user", {}).get("name")
                )
        except Exception as e:
            logger.warning(f"Failed to fetch deployments: {e}")

        return GitLabStatusResponse(
            connected=True,
            project_name=project.get("name"),
            project_url=project.get("web_url"),
            default_branch=project.get("default_branch"),
            latest_pipeline=latest_pipeline,
            latest_commit=latest_commit,
            recent_pipelines=recent_pipelines,
            pipeline_jobs=pipeline_jobs,
            latest_deployment=latest_deployment
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GitLab API error: {e}")
        return GitLabStatusResponse(
            connected=False,
            error=str(e)
        )


@router.get("/pipelines")
async def get_pipelines(limit: int = 10):
    """Get recent pipelines"""
    pipelines_data = await fetch_gitlab_api(f"/pipelines?per_page={limit}")

    return {
        "pipelines": [
            {
                "id": p["id"],
                "status": p["status"],
                "ref": p["ref"],
                "sha": p["sha"][:8],
                "web_url": p["web_url"],
                "created_at": p["created_at"],
                "source": p.get("source", "unknown")
            }
            for p in pipelines_data
        ]
    }


@router.get("/pipelines/{pipeline_id}/jobs")
async def get_pipeline_jobs(pipeline_id: int):
    """Get jobs for a specific pipeline"""
    jobs_data = await fetch_gitlab_api(f"/pipelines/{pipeline_id}/jobs")

    return {
        "jobs": [
            {
                "id": j["id"],
                "name": j["name"],
                "stage": j["stage"],
                "status": j["status"],
                "web_url": j["web_url"],
                "duration": j.get("duration"),
                "started_at": j.get("started_at"),
                "finished_at": j.get("finished_at")
            }
            for j in jobs_data
        ]
    }


@router.get("/health")
async def gitlab_health():
    """Check GitLab connection health"""
    if not GITLAB_TOKEN or not GITLAB_PROJECT_ID:
        return {
            "status": "not_configured",
            "gitlab_url": GITLAB_URL,
            "project_configured": bool(GITLAB_PROJECT_ID),
            "token_configured": bool(GITLAB_TOKEN)
        }

    try:
        project = await fetch_gitlab_api("")
        return {
            "status": "connected",
            "gitlab_url": GITLAB_URL,
            "project_name": project.get("name"),
            "project_id": GITLAB_PROJECT_ID
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
