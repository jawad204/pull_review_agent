# app/github_client.py
import os
import hmac
import hashlib
import httpx

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


def verify_signature(payload_body: bytes, signature_header: str | None) -> bool:
  secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")

  print("=== WEBHOOK HMAC DEBUG ===")
  print(f"Secret configured in backend: {repr(secret)}")
  print(f"Header received: {repr(signature_header)}")

  if not signature_header or not secret:
    print("FAILED: Missing header or secret is empty.")
    return False

  computed = (
      "sha256="
      + hmac.new(
          secret.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256
      ).hexdigest()
  )

  print(f"Computed hash: {computed}")
  print(f"Expected hash: {signature_header}")
  match = hmac.compare_digest(computed, signature_header)
  print(f"Signature Match: {match}")
  print("==========================")
  return match


async def get_pr_diff(diff_url: str) -> str:
    """Fetches the unified git diff from the pull request."""
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.diff",
        "User-Agent": "PR-Review-Agent"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(diff_url, headers=headers, follow_redirects=True)
        response.raise_for_status()
        return response.text


async def post_pr_comment(comments_url: str, markdown_body: str) -> None:
    """Posts the synthesized Markdown review comment to the PR thread."""
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "PR-Review-Agent"
    }
    payload = {"body": markdown_body}
    async with httpx.AsyncClient() as client:
        response = await client.post(comments_url, headers=headers, json=payload)
        response.raise_for_status()