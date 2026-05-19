from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from validator import DeltaFirstV501

from datetime import datetime, timezone
import hashlib
import json
import time

app = FastAPI()

# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vintas.org",
        "https://www.vintas.org",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# SIMPLE MEMORY CACHE
# =========================================================

CACHE = {}
CACHE_TTL = 300  # 5 minutes

# =========================================================
# SIMPLE RATE LIMIT
# =========================================================

RATE_LIMIT = {}
RATE_WINDOW = 3600
RATE_MAX = 100

# =========================================================
# HELPERS
# =========================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def cleanup_cache():
    current = time.time()

    expired = []

    for key, value in CACHE.items():
        if current - value["time"] > CACHE_TTL:
            expired.append(key)

    for key in expired:
        del CACHE[key]


def cleanup_rate_limit():
    current = time.time()

    expired_ips = []

    for ip, timestamps in RATE_LIMIT.items():
        RATE_LIMIT[ip] = [
            ts for ts in timestamps
            if current - ts < RATE_WINDOW
        ]

        if not RATE_LIMIT[ip]:
            expired_ips.append(ip)

    for ip in expired_ips:
        del RATE_LIMIT[ip]


def check_rate_limit(ip):
    cleanup_rate_limit()

    if ip not in RATE_LIMIT:
        RATE_LIMIT[ip] = []

    if len(RATE_LIMIT[ip]) >= RATE_MAX:
        return False

    RATE_LIMIT[ip].append(time.time())
    return True


def make_cache_key(payload):
    encoded = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(encoded.encode()).hexdigest()


def protocol_valid(audit):
    return (
        audit.integrity_score >= 70.0 and
        audit.friction_score <= 0.70 and
        audit.mcl_coefficient >= 0.50 and
        audit.primary_driver in {"H1", "H2", "H3"} and
        bool(audit.boundary.strip())
    )

# =========================================================
# ROUTES
# =========================================================

@app.get("/")
def health():
    return {
        "status": "ok",
        "version": "NEW_MAIN_ACTIVE_V1"
    }

@app.get("/health")
def health_alt():
    return {"status": "ok"}


@app.post("/validate")
async def validate(request: Request):

    # ---------------------------
    # RATE LIMIT
    # ---------------------------

    ip = request.client.host

    if not check_rate_limit(ip):
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded"
            }
        )

    # ---------------------------
    # PARSE JSON
    # ---------------------------

    try:
        payload = await request.json()

    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Malformed JSON payload"
            }
        )

    # ---------------------------
    # CACHE
    # ---------------------------

    cleanup_cache()

    cache_key = make_cache_key(payload)

    if cache_key in CACHE:
        cached = CACHE[cache_key]["result"]
        cached["cached"] = True
        return cached

    # ---------------------------
    # VALIDATION
    # ---------------------------

    try:
        audit = DeltaFirstV501(**payload)

    except ValidationError as e:

        missing = []

        for err in e.errors():

            location = err.get("loc", [])

            if location:
                missing.append(location[-1])

        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid payload",
                "missing_fields": list(set(missing)),
                "details": e.errors()
            }
        )

    # ---------------------------
    # PROTOCOL CHECK
    # ---------------------------

    warnings = []

    if audit.integrity_score < 70:
        warnings.append("Integrity score below threshold")

    if audit.friction_score > 0.70:
        warnings.append("Friction score exceeds threshold")

    if audit.mcl_coefficient < 0.50:
        warnings.append("MCL coefficient below threshold")

    response = {
        "valid": protocol_valid(audit),
        "audit_id": audit.audit_id,
        "primary_driver": audit.primary_driver,
        "mcl_coefficient": audit.mcl_coefficient,
        "friction_score": audit.friction_score,
        "validated_at": now_iso(),
        "warnings": warnings
    }

    # ---------------------------
    # STORE CACHE
    # ---------------------------

    CACHE[cache_key] = {
        "time": time.time(),
        "result": response
    }

    return response