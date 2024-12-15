"""
Models for AI Agent data structures
"""
import json
from typing import Optional, List
from pydantic import BaseModel
from dataclasses import dataclass, asdict

class AgentInfo(BaseModel):
    """Detailed information about an AI agent"""
    name: str
    logo_url: str
    website_url: str
    description: Optional[str] = None
    review: Optional[str] = None
    key_features: Optional[List[str]] = []
    user_cases: Optional[List[str]] = []
    details: Optional[dict[str, str]] = {}
    preview_url: Optional[str] = None

@dataclass
class Agent:
    """Data class for storing basic AI agent information"""
    name: str
    url: str
    source_url: Optional[str]
    description: Optional[str]
    info: Optional[AgentInfo] = None

    def __post_init__(self):
        """Validate required fields after initialization"""
        if not self.name or not self.url:
            raise ValueError("Agent must have both name and URL")

class AgentEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, AgentInfo):
            return obj.model_dump()
        if isinstance(obj, Agent):
            return {
                "name": obj.name,
                "url": obj.url,
                "source_url": obj.source_url,
                "description": obj.description,
                "info": obj.info.model_dump() if obj.info else None
            }

        # Let the base class default method raise the TypeError
        return super().default(obj)