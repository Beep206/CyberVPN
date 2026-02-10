"""System health use case."""

from collections.abc import Callable


class SystemHealthUseCase:
    """Use case for checking system health status."""

    def __init__(
        self,
        db_check: Callable,
        redis_check: Callable,
        remnawave_check: Callable,
    ):
        """Initialize the use case with health check functions.

        Args:
            db_check: Function to check database health
            redis_check: Function to check Redis health
            remnawave_check: Function to check Remnawave API health
        """
        self.db_check = db_check
        self.redis_check = redis_check
        self.remnawave_check = remnawave_check

    async def execute(self) -> dict:
        """Execute the system health check.

        Returns:
            A dictionary containing health status of all components
        """
        health_status = {
            "status": "healthy",
            "components": {},
        }

        # Check database
        try:
            await self.db_check()
            health_status["components"]["database"] = {
                "status": "healthy",
                "message": "Database connection successful",
            }
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "message": f"Database error: {str(e)}",
            }

        # Check Redis
        try:
            await self.redis_check()
            health_status["components"]["redis"] = {
                "status": "healthy",
                "message": "Redis connection successful",
            }
        except Exception as e:
            health_status["status"] = "degraded" if health_status["status"] == "healthy" else "unhealthy"
            health_status["components"]["redis"] = {
                "status": "unhealthy",
                "message": f"Redis error: {str(e)}",
            }

        # Check Remnawave API
        try:
            await self.remnawave_check()
            health_status["components"]["remnawave"] = {
                "status": "healthy",
                "message": "Remnawave API connection successful",
            }
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["components"]["remnawave"] = {
                "status": "unhealthy",
                "message": f"Remnawave API error: {str(e)}",
            }

        return health_status
