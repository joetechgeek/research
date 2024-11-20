from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv
from webscraper import WebScraper  # Import your WebScraper class

load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv('FRONTEND_URL', 'http://localhost:3000'),
        'http://localhost:3000',
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize WebScraper
scraper = None
qa_chain = None

class ScrapeRequest(BaseModel):
    urls: List[str]

class QuestionRequest(BaseModel):
    question: str

@app.post("/api/scrape")
async def scrape_urls(request: ScrapeRequest):
    global scraper, qa_chain
    try:
        scraper = WebScraper()
        documents = scraper.scrape_urls(request.urls)
        
        if not documents:
            raise HTTPException(status_code=400, detail="No content could be scraped")
            
        vector_store = scraper.create_vector_store(documents)
        if not vector_store:
            raise HTTPException(status_code=500, detail="Failed to create vector store")
            
        qa_chain = scraper.setup_qa_chain(vector_store)
        if not qa_chain:
            raise HTTPException(status_code=500, detail="Failed to setup QA chain")
            
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ask")
async def ask_question(request: QuestionRequest):
    global qa_chain
    try:
        if not qa_chain:
            raise HTTPException(status_code=400, detail="Please scrape URLs first")
            
        result = qa_chain({"question": request.question})
        return {
            "answer": result["answer"],
            "sources": result["sources"].split("\n") if result["sources"] else []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/question")
async def ask_question(request: QuestionRequest):
    global qa_chain
    if not qa_chain:
        raise HTTPException(status_code=400, detail="Please scrape URLs first")
    try:
        result = qa_chain({"question": request.question})
        return {"answer": result["answer"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "FastAPI server is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 