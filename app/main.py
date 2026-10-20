# app/main.py (relevant webhook portion)
import json
from fastapi import FastAPI, Request, HTTPException, Header, BackgroundTasks
from app.agent.graph import pr_review_graph
from app.github_client import verify_signature, get_pr_diff, post_pr_comment

app = FastAPI(title="PR Review Agent")


async def run_review_workflow(repo_name: str, pr_number: int, pr_title: str, diff_url: str, comments_url: str):
    """Background task: fetches diff, executes graph, and posts comment."""
    try:
        # 1. Fetch raw diff
        diff_text = await get_pr_diff(diff_url)
        if not diff_text.strip():
            return

        # 2. Initialize state
        initial_state = {
            "repo_full_name": repo_name,
            "pr_number": pr_number,
            "pr_title": pr_title,
            "raw_diff": diff_text,
            "findings": [],
            "final_markdown_review": "",
            "remaining_agents": []
        }

        # 3. Run multi-agent pipeline
        result = await pr_review_graph.ainvoke(initial_state)

        # 4. Post comment back to GitHub PR
        review_markdown = result.get("final_markdown_review")
        if review_markdown:
            await post_pr_comment(comments_url, review_markdown)

    except Exception as e:
        print(f"Error processing PR #{pr_number}: {e}")


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None)
):
    body = await request.body()

    # 1. Validate GitHub HMAC signature
    if not verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid HMAC signature")

    # 2. Handle GitHub ping event (sent when webhook is first saved)
    if x_github_event == "ping":
        return {"status": "ok", "message": "Pong! Webhook active."}

    # 3. Filter for pull request events only
    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"Event '{x_github_event}' not tracked"}

    payload = json.loads(body.decode("utf-8"))
    action = payload.get("action")

    # 4. Trigger only when a PR is opened, reopened, or new commits pushed
    if action not in ["opened", "synchronize", "reopened"]:
        return {"status": "ignored", "reason": f"Action '{action}' does not trigger a review"}

    pr = payload["pull_request"]
    repo = payload["repository"]

    # 5. Offload to background so GitHub receives an instant 202 Accepted
    background_tasks.add_task(
        run_review_workflow,
        repo_name=repo["full_name"],
        pr_number=pr["number"],
        pr_title=pr["title"],
        diff_url=pr["diff_url"],
        comments_url=pr["comments_url"]
    )

    return {"status": "accepted", "message": f"Review initiated for PR #{pr['number']}"}