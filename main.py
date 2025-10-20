import os, asyncio, json
from flask import Flask, request, jsonify
import httpx
from pydantic import BaseModel, HttpUrl, Field
from typing import Literal, List
from server.utils import verify_secret, backoff, pages_url
from server.llm import generate_site_files
from server.github import GitHub
import threading
from dotenv import load_dotenv
load_dotenv()


# -------- Pydantic models --------
class Attachment(BaseModel):
    name: str
    url: str

class TaskRequest(BaseModel):
    email: str
    secret: str
    task: str
    round: Literal[1, 2]
    nonce: str
    brief: str
    checks: List[str] = []
    evaluation_url: HttpUrl
    attachments: List[Attachment] = []

app = Flask(__name__)

SERVER_SECRET = os.getenv("SERVER_SECRET")
GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN")
GITHUB_USER   = os.getenv("GITHUB_USER")

@app.get("/health")
def health():
    ok = bool(SERVER_SECRET and GITHUB_TOKEN and GITHUB_USER)
    return jsonify({"ok": ok, "vars": {"SERVER_SECRET": bool(SERVER_SECRET),
                                       "GITHUB_TOKEN": bool(GITHUB_TOKEN),
                                       "GITHUB_USER": bool(GITHUB_USER)}}), 200 if ok else 500

@app.get("/")
def index():
    return jsonify({"status": "ok"}), 200

@app.post("/completed")
def completed():
    payload = request.get_json(force=True) or {}
    print("Received completion notification:", json.dumps(payload))
    return jsonify({"status": "noted"}), 200

@app.post("/")
def task():
    try:
        data = TaskRequest(**request.get_json(force=True))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    # Respond immediately
    response = jsonify({"usercode": "21f3000426@ds.study.iitm.ac.in"})
    
    # Run background processing in a thread
    threading.Thread(target=asyncio.run, args=(handle_round(data),)).start()

    return response, 200


async def handle_round(req: TaskRequest):
    gh = GitHub(GITHUB_TOKEN, GITHUB_USER)
    repo = req.task
    title = repo
    await gh.create_repo_if_missing(repo, description=req.brief)

    files = generate_site_files(req.brief, req.checks, req.task, [a.model_dump() for a in req.attachments])
    for rel, content in files.items():
        await gh.put_file(repo, rel, content, f"{'feat' if req.round==1 else 'chore'}: update {rel} for round {req.round}")

    await gh.ensure_pages_workflow(repo)
    commit_sha = await gh.latest_commit(repo) or "unknown"
    purl = pages_url(GITHUB_USER, repo)

    async def ping():
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(str(req.evaluation_url),
                                      json={"email": req.email, "task": req.task, "round": req.round,
                                            "nonce": req.nonce, "repo_url": f"https://github.com/{GITHUB_USER}/{repo}",
                                            "commit_sha": commit_sha, "pages_url": purl},
                                      headers={"Content-Type": "application/json"})
                return r.status_code == 200
        except Exception:
            return False

    await backoff(ping, max_tries=8)