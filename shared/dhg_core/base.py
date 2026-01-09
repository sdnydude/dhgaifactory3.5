from fastapi import FastAPI
import structlog
import os
from contextlib import asynccontextmanager
from datetime import datetime

logger = structlog.get_logger()

class BaseAgent:
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.logger = logger.bind(agent=name)
        
        # Standard Lifecycle
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            self.logger.info("agent_startup", version=version)
            await self.startup()
            yield
            self.logger.info("agent_shutdown")
            await self.shutdown()

        self.app = FastAPI(
            title=f"DHG Agent: {name}",
            version=version,
            lifespan=lifespan
        )
        
        # Standard Endpoints
        self.app.get("/health")(self.health_check)
        self.app.get("/")(self.root_info)

    async def startup(self):
        """Override for custom startup logic"""
        pass

    async def shutdown(self):
        """Override for custom shutdown logic"""
        pass

    async def health_check(self):
        return {
            "status": "healthy",
            "agent": self.name,
            "version": self.version,
            "timestamp": datetime.utcnow()
        }

    async def root_info(self):
        return {
            "agent": self.name,
            "type": "dhg-specialized-agent",
            "version": self.version
        }

# Usage: 
# agent = BaseAgent("medical-llm")
# app = agent.app
