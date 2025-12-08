from dhg_core.base import BaseAgent
from dhg_core.messaging import AgentResponse
from pydantic import BaseModel
from typing import List, Optional

class VisualsRequest(BaseModel):
    topic: str
    visual_type: str = "infographic" # slide, chart, infographic
    data_points: Optional[List[str]] = None

class VisualsResponse(BaseModel):
    image_url: str
    prompt_used: str

class VisualsAgent(BaseAgent):
    async def startup(self):
        self.logger.info("visuals_agent_initialized")

    async def generate_visual(self, request: VisualsRequest) -> VisualsResponse:
        self.logger.info("generating_visual", topic=request.topic, type=request.visual_type)
        
        # Placeholder for DALL-E / Stable Diffusion integration
        # For prototype, return a mock URL
        mock_url = f"https://placeholder.com/visuals/{request.topic.replace(' ', '_')}.png"
        
        return VisualsResponse(
            image_url=mock_url,
            prompt_used=f"Medical {request.visual_type} about {request.topic}"
        )

# Initialize
agent = VisualsAgent("visuals-media")
app = agent.app

@app.post("/generate")
async def generate_endpoint(request: VisualsRequest) -> AgentResponse[VisualsResponse]:
    result = await agent.generate_visual(request)
    return AgentResponse(
        source=agent.name,
        type="task.response",
        payload=result
    )
