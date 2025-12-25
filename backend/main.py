# Load environment variables FIRST, before any imports that depend on them
import os
from dotenv import load_dotenv

# Load environment variables from .env file in project root
print("🔧 Loading environment variables...")

try:
    # Try loading from current directory first
    result1 = load_dotenv()
    print(f"📁 Tried loading .env from current directory: {result1}")

    # If that doesn't work, try loading from parent directory
    if not os.getenv("FIRECRAWL_API_KEY"):
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        print(f"📁 Trying to load .env from: {env_path}")
        result2 = load_dotenv(dotenv_path=env_path)
        print(f"📁 Loaded .env from parent directory: {result2}")

except Exception as e:
    print(f"⚠️ Could not load .env file: {e}")

# Additional fallback: Load from Untitled file if environment variables not set
if not os.getenv("FIRECRAWL_API_KEY"):
    try:
        untitled_path = os.path.join(os.path.dirname(__file__), "..", "Untitled")
        print(f"📄 Loading from Untitled file: {untitled_path}")
        with open(untitled_path, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value
                    print(f"✅ Set {key} from Untitled file")
        print("✅ Loaded environment variables from Untitled file")
    except FileNotFoundError:
        print("❌ No Untitled file found")
    except Exception as e:
        print(f"❌ Error loading from Untitled file: {e}")

# Check final status
firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
if firecrawl_key:
    print(f"✅ FIRECRAWL_API_KEY loaded: {firecrawl_key[:10]}...")
else:
    print("❌ FIRECRAWL_API_KEY not found!")

# Now import the modules that depend on environment variables
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from datetime import datetime
from typing import List
from models import AnalyzeRequest, AnalysisResponse, ProductWeakness

# Initialize database manager (will raise exception if connection fails)
try:
    from database import db_manager
    print("✅ Database manager initialized")
except Exception as e:
    print(f"❌ Database initialization failed: {e}")
    print("🔧 Please check your Supabase credentials and database schema")
    raise

# Initialize scraper AFTER environment variables are loaded
from scraper import ContentScraper
scraper = ContentScraper()

app = FastAPI(title="Competitor Analysis API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174", "https://aicompetitoranalysis.netlify.app"],  # Vite dev server (both 5173 and 5174)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Google AI
genai.configure(api_key=os.getenv("GOOGLE_AI_API_KEY"))
try:
    model = genai.GenerativeModel('gemini-flash-latest')
    print("✅ Using Google AI model: gemini-flash-latest")
except Exception as e:
    print(f"⚠️ gemini-flash-latest not available: {e}")
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        print("✅ Using Google AI model: gemini-2.5-flash")
    except Exception as e2:
        print(f"❌ No Gemini models available: {e2}")
        model = None

# Supported models metadata (frontend will fetch this list)
SUPPORTED_MODELS = [
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "daily": "20", "note": "Severely limited"},
    {"id": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash-Lite", "daily": "1,500", "note": "Recommended for Free Tier"},
    {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "daily": "0 - 5", "note": "Often removed or restricted"},
]


@app.get("/models")
async def list_models():
    """Return supported model ids and descriptive metadata for the frontend."""
    return {"models": SUPPORTED_MODELS}

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Competitor Analysis API is running"}

@app.get("/env-check")
async def env_check():
    """Check environment variable status"""
    return {
        "FIRECRAWL_API_KEY": bool(os.getenv("FIRECRAWL_API_KEY")),
        "SUPABASE_URL": bool(os.getenv("SUPABASE_URL")),
        "GOOGLE_AI_API_KEY": bool(os.getenv("GOOGLE_AI_API_KEY")),
        "firecrawl_key_prefix": os.getenv("FIRECRAWL_API_KEY")[:10] + "..." if os.getenv("FIRECRAWL_API_KEY") else None
    }

@app.get("/db-check")
async def db_check():
    """Check database connection and table structure"""
    try:
        # Test competitors table
        competitors_result = db_manager.supabase.table("competitors").select("id", count="exact").limit(1).execute()
        competitor_count = getattr(competitors_result, 'count', 0)

        # Test insights table
        insights_result = db_manager.supabase.table("insights").select("id", count="exact").limit(1).execute()
        insights_count = getattr(insights_result, 'count', 0)

        return {
            "status": "connected",
            "database_url": "Configured ✅",
            "competitors_table": f"✅ ({competitor_count} records)",
            "insights_table": f"✅ ({insights_count} records)",
            "ready_for_production": True
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "troubleshooting": [
                "1. Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env",
                "2. Run database_schema.sql in Supabase SQL Editor",
                "3. Verify your Supabase project is active"
            ]
        }

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_competitor(request: AnalyzeRequest):
    """
    Analyze a competitor's website for product weaknesses

    Args:
        request: Analysis request containing target URL and competitor name

    Returns:
        Analysis results with identified weaknesses
    """
    try:
        # Step 1: Scrape the target URL
        print(f"🔍 Scraping content from {request.target_url}")
        print(f"🔍 Scraper instance: {scraper}")
        print(f"🔍 Scraper firecrawl: {scraper.firecrawl}")
        scraped_content = scraper.scrape_url(request.target_url)

        if not scraped_content:
            raise HTTPException(
                status_code=400,
                detail="Failed to scrape content from the provided URL"
            )

        print(f"✅ Scraped {len(scraped_content)} characters of content")

        # Step 2: Create or get competitor record
        competitor = await db_manager.create_competitor(
            name=request.competitor_name,
            target_url=request.target_url
        )

        # Step 3: Analyze content with AI
        print("🤖 Analyzing content with AI...")

        # Determine which model instance to use for this request.
        # Validate request.model against our SUPPORTED_MODELS list to prevent arbitrary ids.
        selected_model = None
        requested_model_id = getattr(request, 'model', None)
        if requested_model_id:
            allowed_ids = [m['id'] for m in SUPPORTED_MODELS]
            if requested_model_id not in allowed_ids:
                raise HTTPException(status_code=400, detail=f"Requested model '{requested_model_id}' is not supported. Allowed: {allowed_ids}")
            try:
                print(f"🔁 Request requested model: {requested_model_id}")
                selected_model = genai.GenerativeModel(requested_model_id)
                print(f"✅ Using requested model instance: {requested_model_id}")
            except Exception as e:
                print(f"⚠️ Requested model '{requested_model_id}' not available: {e}")
                # we'll fall back to server default below

        if not selected_model:
            selected_model = model

        if not selected_model:
            # Fallback: create mock weaknesses if AI is not available
            weaknesses = [
                ProductWeakness(
                    title="AI Analysis Unavailable",
                    description="Google AI service is currently unavailable. This appears to be a temporary API issue.",
                    severity="medium",
                    category="technical"
                ),
                ProductWeakness(
                    title="Manual Review Required",
                    description=f"Content was successfully scraped from {request.target_url} but AI analysis failed. Manual review recommended.",
                    severity="low",
                    category="technical"
                )
            ]
        else:
            prompt = f"""
            You are an expert competitive analyst. Analyze the following content from {request.competitor_name}'s website
            and identify their main product weaknesses or areas for improvement.

            Focus on:
            - Product features and functionality gaps
            - Pricing issues or concerns
            - Customer support problems
            - User experience issues
            - Technical limitations
            - Market positioning weaknesses

            Content to analyze:
            {scraped_content[:10000]}  # Limit content length for API

            Please provide 8-12 specific weaknesses in the following JSON format:
            {{
                "weaknesses": [
                    {{
                        "title": "Brief title of weakness",
                        "description": "Detailed explanation of the weakness and why it's a problem",
                        "severity": "high|medium|low",
                        "category": "feature|pricing|support|usability|technical|other"
                    }}
                ]
            }}

            Be specific, actionable, and focus on genuine weaknesses that competitors could exploit.
            """

            try:
                response = selected_model.generate_content(prompt)
                ai_response = response.text
            except Exception as ai_error:
                print(f"❌ AI analysis failed using model {getattr(selected_model, 'name', 'unknown')}: {ai_error}")
                # Fallback to mock weaknesses
                weaknesses = [
                    ProductWeakness(
                        title="AI Service Error",
                        description=f"Google AI analysis failed: {str(ai_error)}. Content scraping was successful.",
                        severity="medium",
                        category="technical"
                    )
                ]

        # Parse AI response (only if AI was successful)
        if 'ai_response' in locals() and ai_response:
            try:
                # Extract JSON from the response
                import json
                import re

                # Find JSON in the response
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if json_match:
                    weaknesses_data = json.loads(json_match.group())
                    weaknesses = [
                        ProductWeakness(**w) for w in weaknesses_data.get("weaknesses", [])
                    ]
                else:
                    # Fallback: create mock weaknesses if parsing fails
                    weaknesses = [
                        ProductWeakness(
                            title="AI Response Parsing Issue",
                            description="AI provided a response but it couldn't be parsed as JSON",
                            severity="medium",
                            category="technical"
                        )
                    ]
            except Exception as e:
                print(f"Error parsing AI response: {e}")
                weaknesses = [
                    ProductWeakness(
                        title="Analysis parsing error",
                        description=f"Failed to parse AI analysis: {str(e)}",
                        severity="medium",
                        category="technical"
                    )
                ]

        # Step 4: Save insights to database
        await db_manager.save_insights(competitor.id, weaknesses)

        # Step 5: Return analysis results
        return AnalysisResponse(
            competitor_name=request.competitor_name,
            target_url=request.target_url,
            weaknesses=weaknesses,
            analyzed_at=datetime.utcnow(),
            raw_content_length=len(scraped_content)
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

@app.get("/competitors")
async def get_competitors():
    """Get all analyzed competitors"""
    try:
        # Get all competitors with their analysis count
        competitors = db_manager.supabase.table("competitors").select("id, name, target_url, created_at").execute()

        if competitors.data:
            # Get insights count for each competitor
            result = []
            for comp in competitors.data:
                insights_count = db_manager.supabase.table("insights").select("id", count="exact").eq("competitor_id", comp["id"]).execute()
                count = getattr(insights_count, 'count', 0)

                result.append({
                    "id": comp["id"],
                    "name": comp["name"],
                    "url": comp["target_url"],
                    "analyses_count": count,
                    "created_at": comp["created_at"]
                })

            return {
                "total_competitors": len(result),
                "competitors": result
            }
        else:
            return {"total_competitors": 0, "competitors": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch competitors: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
