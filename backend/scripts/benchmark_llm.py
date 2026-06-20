import asyncio
import sys
import time
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.append("/workspace")

from app.config import settings
from app.infrastructure.database.mongodb import MongoDB
from app.infrastructure.llm.gemini import GeminiImplementation
from app.infrastructure.llm.groq_llm import GroqImplementation
from app.infrastructure.database.repositories import RawDataRepository

async def run_benchmark():
    await MongoDB.connect()
    
    # Instantiate both LLM providers directly to bypass DB config for the benchmark
    gemini = GeminiImplementation()
    groq = GroqImplementation()
    
    raw_repo = RawDataRepository()
    
    # We will pick 10 newest raw articles
    print("Fetching 10 raw articles for benchmarking...")
    cursor = raw_repo.collection.find().sort("crawl_time", -1).limit(10)
    articles = [doc async for doc in cursor]
    
    if not articles:
        print("No raw articles found!")
        return
        
    print(f"Loaded {len(articles)} articles.")
    
    print("\n--- BATCH CLUSTERING BENCHMARK ---")
    print("Sending batch request to GEMINI...")
    t0 = time.time()
    try:
        gemini_result = await gemini.extract_insights_batch(articles)
        gemini_time = time.time() - t0
        print(f"Gemini Time: {gemini_time:.2f}s")
        print(f"Gemini output type: {type(gemini_result)}")
        print(f"Gemini clustered into {len(gemini_result)} events.")
    except Exception as e:
        print(f"Gemini Batch Failed: {e}")
        
    print("\nSending batch request to GROQ...")
    t0 = time.time()
    try:
        groq_result = await groq.extract_insights_batch(articles)
        groq_time = time.time() - t0
        print(f"Groq Time: {groq_time:.2f}s")
        print(f"Groq output type: {type(groq_result)}")
        print(f"Groq clustered into {len(groq_result)} events.")
    except Exception as e:
        print(f"Groq Batch Failed: {e}")
        
    print("\n--- DONE ---")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
