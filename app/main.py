from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from app.agent.graph import pr_review_graph

# Load environment variables (.env)
load_dotenv()

app = FastAPI(title="Agentic PR & Security Reviewer")

class SimulatePRRequest(BaseModel):
    pr_title: str = "Add user login endpoint and order lookup"
    raw_diff: str

@app.get("/health")
async def health_check():
    return {"status": "online", "message": "FastAPI and LangGraph are ready!"}

@app.post("/review/simulate")
async def simulate_review(req: SimulatePRRequest):
    """
    Triggers the parallel multi-agent LangGraph workflow and 
    automatically traces it in LangSmith.
    """
    initial_state = {
        "repo_full_name": "local/sandbox",
        "pr_number": 1,
        "pr_title": req.pr_title,
        "raw_diff": req.raw_diff,
        "findings": [],
        "final_markdown_review": "",
    }
    
    # Run the graph asynchronously and give the trace a custom run name in LangSmith
    result = await pr_review_graph.ainvoke(
        initial_state,
        config={"run_name": "Simulated-PR-Review"}
    )
    
    return {
        "structured_findings": result["findings"],
        "markdown_comment": result["final_markdown_review"],
    }