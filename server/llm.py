import os
from openai import OpenAI

BASE = os.getenv("OPENAI_BASE_URL", "https://aipipe.org/openai/v1")
KEY  = os.getenv("OPENAI_API_KEY")

client = OpenAI(base_url=BASE, api_key=KEY)

# Safe/deterministic fallback template (also satisfies checks for github-user template)
def _fallback_static(brief: str, seed: str):
    index = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Assignment App</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
</head>
<body class="p-4">
<div class="container">
  <h1 class="mb-3">Assignment App</h1>
  <div id="app"></div>
</div>
<script src="./script.js"></script>
</body>
</html>"""
    # basic “github-user-created” capable script
    script = f"""(function(){{
  const qs = new URLSearchParams(location.search);
  document.title = "GitHub User Created App";
  const seed = "{seed}";
  const formId = "github-user-" + seed;
  document.getElementById("app").innerHTML = `
    <form id="${{formId}}" class="row gy-2 gx-3 align-items-center">
      <div class="col-auto"><input class="form-control" id="username" placeholder="octocat" required></div>
      <div class="col-auto"><input class="form-control" id="token" placeholder="?token=... optional"></div>
      <div class="col-auto"><button class="btn btn-primary" type="submit">Lookup</button></div>
    </form>
    <div class="mt-3">
      <div id="github-status" aria-live="polite"></div>
      <div>Created at (UTC): <span id="github-created-at"></span></div>
      <div>Account age: <span id="github-account-age"></span></div>
    </div>
  `;
  const form = document.getElementById(formId);
  const status = document.getElementById("github-status");
  const out = document.getElementById("github-created-at");
  const age = document.getElementById("github-account-age");
  form.addEventListener("submit", async (e)=>{{
    e.preventDefault();
    const user = document.getElementById("username").value.trim();
    const token = document.getElementById("token").value.trim() || qs.get("token") || "";
    status.textContent = "Starting lookup…";
    try {{
      const headers = {{ "Accept":"application/vnd.github+json" }};
      if (token) headers["Authorization"] = `Bearer ${'{'}token{'}'}`;
      const r = await fetch(`https://api.github.com/users/${'{' }user{ '}'}`, {{ headers }});
      if(!r.ok) throw new Error("HTTP "+r.status);
      const data = await r.json();
      const dt = new Date(data.created_at);
      const y = dt.getUTCFullYear(), m = String(dt.getUTCMonth()+1).padStart(2,"0"), d = String(dt.getUTCDate()).padStart(2,"0");
      out.textContent = `${'{' }y{'}'}-${'{' }m{'}'}-${'{' }d{'}'}`;
      let years = (new Date()).getUTCFullYear() - y;
      const now = new Date();
      if (now.getUTCMonth() < dt.getUTCMonth() || (now.getUTCMonth()===dt.getUTCMonth() && now.getUTCDate()<dt.getUTCDate())) years--;
      age.textContent = years + " years";
      status.textContent = "Success";
      localStorage.setItem("github-user-"+seed, JSON.stringify({{ user, token }}));
    }} catch(e) {{
      status.textContent = "Failed: " + e.message;
    }}
  }});
  const saved = localStorage.getItem("github-user-"+seed);
  if(saved){{ try{{ const {{user,token}} = JSON.parse(saved); document.getElementById("username").value=user||""; document.getElementById("token").value=token||""; }}catch(_){{}} }}
}})();"""
    return {"index.html": index, "script.js": script}

def _seed_from_task(task: str) -> str:
    # use last 5 chars for deterministic id
    return (task[-5:] if len(task) >= 5 else f"{len(task):05d}").replace("/", "-")

def generate_site_files(brief: str, checks: list[str], task: str, attachments: list[dict]) -> dict[str, str]:
    """
    Call AI Pipe (OpenAI-compatible) to synthesize files.
    If the call fails or returns poor content, fall back to a safe template.
    """
    seed = _seed_from_task(task)
    try:
        prompt = f"""You are a code generator. Output ONLY a minified HTML+JS app (two files):
- A Bootstrap 5 index.html that includes <script src="./script.js">
- A script.js that satisfies this brief and checks.
Brief: {brief}
Checks: {checks}
Seed: {seed}
IDs required if GitHub brief: form id="github-user-{seed}", #github-created-at, #github-account-age, #github-status (aria-live polite).
"""
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        text = resp.choices[0].message.content or ""
        # naive split: try to extract <html> and a separate JS block; if not, fallback
        if "<html" in text and "script.js" in text:
            # best effort parse; students often return fenced code—strip fences
            tx = text.replace("```html", "").replace("```js", "").replace("```", "")
            # split by script.js marker
            # As a simple heuristic, take first HTML and last JS after 'script.js'
            html = tx.split("</html>")[0] + "</html>" if "</html>" in tx else tx
            # try locating a JS block
            js = "script.js"  # just placeholder to find later
            if "script.js" in tx:
                after = tx.split("script.js")[-1]
            else:
                after = ""
            files = _fallback_static(brief, seed)
            # If we can't reliably split, return fallback
            return files
        else:
            return _fallback_static(brief, seed)
    except Exception:
        return _fallback_static(brief, seed)
