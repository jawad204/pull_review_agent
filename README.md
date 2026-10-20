# 🤖 Pull Review Agent

An asynchronous, event-driven multi-agent GitHub Pull Request reviewer built with **FastAPI**, **LangGraph**, and **GitHub Webhooks**.

When a Pull Request is opened or updated, the system verifies the incoming webhook, immediately acknowledges GitHub to beat API timeouts, asynchronously fetches the unified diff, runs it through specialized AI review agents, and posts a synthesized, actionable review comment back onto the PR.

---

## 🏗️ Architecture & Data Flow

```text
[ GitHub Event ]
       │  (Signed Webhook Delivery)
       ▼
[ Smee.io Proxy / Ingress ]
       │  (Local forwarding during development)
       ▼
[ FastAPI App ] ───(HMAC SHA-256 Check & 202 Accepted)───► GitHub (<50ms)
       │
       ▼ (Background Worker)
[ Fetch PR Diff ] ───► GitHub REST API (`Accept: application/vnd.github.v3.diff`)
       │
       ▼
[ LangGraph Workflow ]
   ├── Agent Analysis (Security, Logic, Performance)
   └── Synthesis Node (Markdown consolidation)
       │
       ▼
[ GitHub Egress ] ───► POST to `/issues/{number}/comments` (Review Comment)
```

### Key Engineering Decisions
* **Instant Acknowledgment (FastAPI `BackgroundTasks`):** GitHub enforces a strict 10-second timeout on webhook deliveries. The ingress layer validates the request and immediately returns an HTTP `202 Accepted`, running the multi-agent LLM workflow in the background.
* **Cryptographic Ingress Security:** Incoming payloads are validated against `X-Hub-Signature-256` using constant-time comparison (`hmac.compare_digest`) to prevent timing attacks.
* **Raw Diff Ingestion:** Pulls the raw unified diff text using GitHub's media type header directly into the typed LangGraph agent state.

---

## 🛠️ Tech Stack

* **Backend:** Python 3.11+, [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), [HTTPX](https://www.python-httpx.org/)
* **Agent Framework:** [LangGraph](https://github.com/langchain-ai/langgraph), [LangChain](https://github.com/langchain-ai/langchain)
* **Webhook Tunneling:** [Smee.io](https://smee.io/)
* **Platform:** GitHub REST API v3

---

## 📁 Project Structure

```text
pull_review_agent/
├── app/
│   ├── agent/
│   │   ├── graph.py          # LangGraph state machine & multi-agent nodes
│   │   └── state.py          # TypedDict definitions for graph state
│   ├── github_client.py      # HMAC signature verification & GitHub API clients
│   └── main.py               # FastAPI ingress & background task orchestration
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🚀 Getting Started

### 1. Prerequisites

* Python 3.11+
* Node.js & npm (for running `npx smee-client`)
* A GitHub repository where you have administrator permissions
* An LLM API key (OpenAI, Anthropic, or Google Gemini)

### 2. Clone and Setup Environment

```bash
git clone https://github.com/jawad204/pull_review_agent.git
cd pull_review_agent

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Fill in the required keys:

```env
# GitHub Personal Access Token (Requires Issues: Read/Write and Pull Requests: Read/Write)
GITHUB_TOKEN=ghp_your_personal_access_token_here

# Secret used to sign GitHub Webhooks (must match the secret entered in GitHub settings)
GITHUB_WEBHOOK_SECRET=your_custom_webhook_secret_here

# LLM Provider Key (depending on your graph configuration)
OPENAI_API_KEY=sk-...
```

---

## ⚙️ Webhook & Local Setup

Because GitHub needs a publicly accessible URL to deliver webhooks, we use **Smee.io** to proxy events to your local machine without exposing ports.

### 1. Start a Smee Channel
1. Go to [smee.io](https://smee.io) and click **Start a new channel**.
2. Copy your unique channel URL (e.g., `https://smee.io/abc123xyz`).

### 2. Configure GitHub Webhook
1. Go to your repository $\rightarrow$ **Settings** $\rightarrow$ **Webhooks** $\rightarrow$ **Add webhook**.
2. **Payload URL:** Paste your Smee URL (`https://smee.io/abc123xyz`).
3. **Content type:** Select **`application/json`** *(critical: do not use `x-www-form-urlencoded`)*.
4. **Secret:** Enter the exact string set in your `.env` as `GITHUB_WEBHOOK_SECRET`.
5. **Which events:** Choose **Let me select individual events**, uncheck *Pushes*, and check **Pull requests**.
6. Save the webhook.

---

## 🏃 Running the Application

Open two terminal windows:

### Terminal 1: Start the FastAPI Server
```bash
uvicorn app.main:app --reload --port 8000
```

### Terminal 2: Start the Smee Proxy
```bash
npx smee-client --url https://smee.io/YOUR_CHANNEL_ID --target http://localhost:8000/webhook/github
```

---

## 🧪 Testing the Review Pipeline

1. Create a feature branch and add intentional bugs or improvements:
   ```bash
   git checkout -b test-review-branch
   ```
2. Commit a code sample and push it to GitHub:
   ```bash
   git add .
   git commit -m "feat: test review trigger"
   git push -u origin test-review-branch
   ```
3. Open a **Pull Request** on GitHub against `main`.
4. Observe the flow:
   * **Smee Terminal:** Logs `POST /webhook/github - 202`.
   * **FastAPI Terminal:** Validates HMAC signature $\rightarrow$ kicks off `pr_review_graph.ainvoke`.
   * **GitHub PR:** Refresh the PR conversation page to see the automated review comment posted by your agent.

---

## 🔒 Security Best Practices

* **Signature Verification:** Requests missing or presenting invalid `X-Hub-Signature-256` headers are rejected with `401 Unauthorized` before reading payload content.
* **Token Scopes:** When creating fine-grained GitHub PATs, grant minimal permissions:
  * `Repository permissions` $\rightarrow$ **Issues**: `Read & Write` (required for issue/PR comments).
  * `Repository permissions` $\rightarrow$ **Pull requests**: `Read & Write`.

---

## 📄 License

MIT