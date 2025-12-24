from pydantic import BaseModel, Field
from typing import List
from datetime import datetime


class AnalyzeRequest(BaseModel):
    """Request model for the /analyze endpoint"""
    target_url: str = Field(..., description="URL to scrape (e.g., Trustpilot or G2 page)")
    competitor_name: str = Field(..., description="Name of the competitor company")
    model: str | None = Field(None, description="Optional model id to use for analysis (e.g., gemini-2.5-flash-lite)")


class ProductWeakness(BaseModel):
    """Individual product weakness identified by AI"""
    title: str = Field(..., description="Brief title of the weakness")
    description: str = Field(..., description="Detailed explanation")
    severity: str = Field(..., description="Severity level: low, medium, high")
    category: str = Field(..., description="Category: feature, pricing, support, usability, etc.")


class AnalysisResponse(BaseModel):
    """Response model containing analysis results"""
    competitor_name: str
    target_url: str
    weaknesses: List[ProductWeakness]
    analyzed_at: datetime
    raw_content_length: int = Field(..., description="Length of scraped content in characters")


class CompetitorRecord(BaseModel):
    """Database record for competitors table"""
    id: str
    name: str
    target_url: str
    created_at: datetime
    updated_at: datetime


class InsightRecord(BaseModel):
    """Database record for insights table"""
    id: str
    competitor_id: str
    weakness_title: str
    weakness_description: str
    severity: str
    category: str
    created_at: datetime









