import httpx, base64, os
from typing import Optional
from .files import README_TMPL, PAGES_WORKFLOW_YML

GITHUB_API = "https://api.github.com"

class GitHub:
    def __init__(self, token: str, owner: str):
        self.token = token
        self.owner = owner
        self.h = {"Authorization": f"Bearer {token}",
                  "Accept": "application/vnd.github+json",
                  'User-Agent': 'ashwin3082002'}

    async def create_repo_if_missing(self, repo: str, description: str) -> None:
        async with httpx.AsyncClient(timeout=20, headers=self.h) as client:
            r = await client.get(f"{GITHUB_API}/repos/{self.owner}/{repo}")
            if r.status_code == 200: return
            payload = {"name": repo, "description": description, "private": False, "auto_init": False, "license_template": "mit"}
            cr = await client.post(f"{GITHUB_API}/user/repos", json=payload)
            cr.raise_for_status()

    async def put_file(self, repo: str, path: str, content_utf8: str, message: str) -> str:
        # GitHub Contents API wants base64 bytes
        b64 = base64.b64encode(content_utf8.encode("utf-8")).decode("ascii")
        async with httpx.AsyncClient(timeout=20, headers=self.h) as client:
            # Check if exists to include SHA
            getr = await client.get(f"{GITHUB_API}/repos/{self.owner}/{repo}/contents/{path}")
            sha = getr.json().get("sha") if getr.status_code == 200 else None
            pr = await client.put(
                f"{GITHUB_API}/repos/{self.owner}/{repo}/contents/{path}",
                json={"message": message, "content": b64, **({"sha": sha} if sha else {})}
            )
            pr.raise_for_status()
            return pr.json()["commit"]["sha"]

    async def latest_commit(self, repo: str, branch="main") -> Optional[str]:
        async with httpx.AsyncClient(timeout=20, headers=self.h) as client:
            r = await client.get(f"{GITHUB_API}/repos/{self.owner}/{repo}/commits", params={"sha": branch, "per_page": 1})
            if r.status_code != 200: return None
            data = r.json()
            return data[0]["sha"] if data else None

    async def ensure_pages_workflow(self, repo: str) -> str:
        path = ".github/workflows/pages.yml"
        return await self.put_file(repo, path, PAGES_WORKFLOW_YML, "ci: add pages workflow")

    async def seed_repo(self, repo: str, title: str, brief: str, files: dict) -> str:
        # minimal site
        for rel, content in files.items():
            await self.put_file(repo, rel, content, f"init: add {rel}")
        # readme (pages URL guessed; first deploy fills it)
        purl = f"https://{self.owner}.github.io/{repo}/"
        await self.put_file(repo, "README.md", README_TMPL.format(title=title, summary=brief, pages_url=purl), "docs: add README")
        # workflow
        await self.ensure_pages_workflow(repo)
        # latest commit sha
        sha = await self.latest_commit(repo)
        return sha or "unknown"
