from supabase import create_client, Client
from typing import Optional, List
import os
from datetime import datetime
from models import CompetitorRecord, InsightRecord, ProductWeakness, AnalysisResponse


class DatabaseManager:
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("❌ SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment variables")

        try:
            self.supabase: Client = create_client(
                supabase_url=supabase_url,
                supabase_key=supabase_key
            )
            print("✅ Supabase connection established")
            # Test the connection
            self.supabase.table("competitors").select("id").limit(1).execute()
            print("✅ Database tables accessible")
        except Exception as e:
            raise ValueError(f"❌ Failed to connect to Supabase: {e}")

    async def create_competitor(self, name: str, target_url: str) -> CompetitorRecord:
        """Create or get existing competitor record"""
        # First check if competitor already exists
        existing = await self.get_competitor_by_name(name)
        if existing:
            return existing

        # Create new competitor record
        data = {
            "name": name,
            "target_url": target_url,
        }

        try:
            result = self.supabase.table("competitors").insert(data).execute()

            if result.data and len(result.data) > 0:
                record = result.data[0]
                return CompetitorRecord(
                    id=record["id"],
                    name=record["name"],
                    target_url=record["target_url"],
                    created_at=datetime.fromisoformat(record["created_at"]),
                    updated_at=datetime.fromisoformat(record["updated_at"])
                )
            else:
                raise Exception("No data returned from competitor creation")
        except Exception as e:
            raise Exception(f"Failed to create competitor record: {e}")

    async def get_competitor_by_name(self, name: str) -> Optional[CompetitorRecord]:
        """Get competitor by name"""
        try:
            result = self.supabase.table("competitors").select("*").eq("name", name).execute()

            if result.data and len(result.data) > 0:
                record = result.data[0]
                return CompetitorRecord(
                    id=record["id"],
                    name=record["name"],
                    target_url=record["target_url"],
                    created_at=datetime.fromisoformat(record["created_at"]),
                    updated_at=datetime.fromisoformat(record["updated_at"])
                )
            return None
        except Exception as e:
            raise Exception(f"Failed to query competitor: {e}")

    async def save_insights(self, competitor_id: str, weaknesses: List[ProductWeakness]) -> List[InsightRecord]:
        """Save analysis insights to database"""
        if not weaknesses:
            return []

        insights_data = []
        for weakness in weaknesses:
            insights_data.append({
                "competitor_id": competitor_id,
                "weakness_title": weakness.title,
                "weakness_description": weakness.description,
                "severity": weakness.severity,
                "category": weakness.category,
            })

        try:
            result = self.supabase.table("insights").insert(insights_data).execute()

            if result.data and len(result.data) > 0:
                return [
                    InsightRecord(
                        id=record["id"],
                        competitor_id=record["competitor_id"],
                        weakness_title=record["weakness_title"],
                        weakness_description=record["weakness_description"],
                        severity=record["severity"],
                        category=record["category"],
                        created_at=datetime.fromisoformat(record["created_at"])
                    )
                    for record in result.data
                ]
            else:
                raise Exception("No data returned from insights insertion")
        except Exception as e:
            raise Exception(f"Failed to save insights: {e}")


# Global database manager instance
db_manager = DatabaseManager()
