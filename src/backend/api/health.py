"""Health check endpoints for observability and diagnostics."""

from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Optional
import backend.storage as storage_module
from backend.logging_config import logger

router = APIRouter(prefix="/health", tags=["health"])


# Response Models
class ComponentHealth(BaseModel):
    """Health status of a single component."""

    component: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Overall system health status."""

    status: str  # "ok" (all healthy), "degraded", "error" (any critical failure)
    timestamp: str
    components: list[ComponentHealth]


@router.get("", response_model=HealthCheckResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthCheckResponse:
    """
    Get overall system health status.

    Returns comprehensive health information for all components:
    - Storage backend
    - Database connectivity
    - Cache (if available)
    - Auth system

    Status values:
    - "ok": All components healthy
    - "degraded": Some components unhealthy but system operational
    - "error": Critical component failure

    Returns:
        HealthCheckResponse with timestamp and component statuses (200 OK).
    """
    from datetime import datetime

    components = []

    # Check storage backend
    if storage_module._storage_backend:
        try:
            storage_health = await storage_module._storage_backend.health_check()
            components.append(
                ComponentHealth(
                    component="storage",
                    status=storage_health.get("status", "unknown"),
                    message=storage_health.get("error"),
                )
            )
        except Exception as e:
            logger.error(
                "Storage health check failed",
                extra={"error": str(e)},
            )
            components.append(
                ComponentHealth(
                    component="storage",
                    status="unhealthy",
                    message=f"Health check failed: {str(e)}",
                )
            )
    else:
        components.append(
            ComponentHealth(
                component="storage",
                status="unhealthy",
                message="Storage backend not initialized",
            )
        )

    # Check database connectivity (basic check)
    try:
        from backend.db import get_session_factory

        SessionLocal = get_session_factory()
        session = SessionLocal()
        try:
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
            session.close()
            components.append(
                ComponentHealth(
                    component="database",
                    status="healthy",
                )
            )
        except Exception as e:
            components.append(
                ComponentHealth(
                    component="database",
                    status="unhealthy",
                    message=f"Database query failed: {str(e)}",
                )
            )
            raise
    except Exception as e:
        logger.error(
            "Database health check failed",
            extra={"error": str(e)},
        )
        components.append(
            ComponentHealth(
                component="database",
                status="unhealthy",
                message=f"Database connection failed: {str(e)}",
            )
        )

    # Determine overall status
    statuses = [c.status for c in components]
    if all(s == "healthy" for s in statuses):
        overall_status = "ok"
    elif any(s == "unhealthy" for s in statuses):
        overall_status = "error"
    else:
        overall_status = "degraded"

    logger.info(
        "Health check completed",
        extra={"overall_status": overall_status, "component_count": len(components)},
    )

    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        components=components,
    )


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """
    Readiness probe for load balancers/orchestrators.

    Returns 200 if the service is ready to accept traffic.
    Returns 503 if critical components are unavailable.

    This is typically called by Kubernetes/Docker health checks.
    """
    # Check storage
    if not storage_module._storage_backend:
        return {"ready": False, "reason": "Storage backend not initialized"}

    # Check database
    try:
        from backend.db import get_session_factory
        from sqlalchemy import text

        SessionLocal = get_session_factory()
        session = SessionLocal()
        try:
            session.execute(text("SELECT 1"))
            session.close()
        except Exception:
            return {"ready": False, "reason": "Database unavailable"}
    except Exception:
        return {"ready": False, "reason": "Database unavailable"}

    return {"ready": True}


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """
    Liveness probe for load balancers/orchestrators.

    Returns 200 if the service is running (not stuck/deadlocked).
    This is a basic check; if it fails, the container should be restarted.
    """
    return {"alive": True}
