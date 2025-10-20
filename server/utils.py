import base64, re, time, asyncio, hmac, os
from hashlib import sha256

def verify_secret(got: str, expected: str) -> bool:
    if got is None or expected is None: return False
    return hmac.compare_digest(got, expected)

_data_uri_re = re.compile(r"^data:(.*?);base64,(.*)$")

def decode_data_uri(uri: str) -> tuple[bytes, str]:
    m = _data_uri_re.match(uri or "")
    if not m: raise ValueError("Unsupported attachment URL")
    mime, b64 = m.groups()
    return base64.b64decode(b64), mime

async def backoff(retry_fn, *, max_tries=8):
    delay = 1
    for i in range(max_tries):
        ok = await retry_fn()
        if ok: return True
        await asyncio.sleep(delay)
        delay = min(delay * 2, 32)
    return False

def pages_url(owner: str, repo: str) -> str:
    return f"https://{owner}.github.io/{repo}/"
