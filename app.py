import os, datetime, aiofiles
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets, base64

security = HTTPBasic()

# pull creds from env (need to set in Railway Variables)
BASIC_USER = os.getenv("UPLOAD_USER", "perfect")
BASIC_PASS = os.getenv("UPLOAD_PASS", "plants")

# ── where to save uploads ────────────────────────────────────
UPLOAD_ROOT = Path(
    os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "./uploads")  # local fallback
) / "uploads"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_user = secrets.compare_digest(credentials.username, BASIC_USER)
    correct_pass = secrets.compare_digest(credentials.password, BASIC_PASS)
    if not (correct_user and correct_pass):
        raise HTTPException(status_code=401, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Basic"})
    return True

# ── FastAPI setup ────────────────────────────────────────────
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# UI
@app.get("/", response_class=HTMLResponse, dependencies=[Depends(check_auth)])
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Upload
@app.post("/upload", dependencies=[Depends(check_auth)])
async def upload(file: UploadFile = File(...)):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(400, "Only .xlsx files allowed")
    ts   = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    dest = UPLOAD_ROOT / f"{ts}__{file.filename}"
    async with aiofiles.open(dest, "wb") as out:
        while chunk := await file.read(1 << 20):   # 1 MB chunks
            await out.write(chunk)
    return {"saved": dest.name}

# Health (for Relay)
@app.get("/healthz")
def health():
    return {"ok": True}
