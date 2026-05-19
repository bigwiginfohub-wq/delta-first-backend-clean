from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from typing import Dict, Any
import time

app = FastAPI()

# CORS (frontend allowed origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vintas.org",
        "https://www.vintas.org",
        "http://localhost:*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# HEALTH CHECK
# -------------------------
@app.get("/")
@app.get("/health")
def health():
    return {"status": "ok"}

# -------------------------
# VALIDATION MODEL
# -------------------------
class AuditPayload(BaseModel):
    auditor_id: str
    audit_id: str
    integrity_score: float
    protocol_mode: str
    primary_driver: str
    reasoning_trace: str
    peak_moment: str
    interpretive_anchor: str
    h3_warrant: str
    null_test: str
    label_impact: str
    friction_score_components: Dict[str, Any]
    friction_score: float
    mcl_coefficient: float
    boundary: str


# -------------------------
# CORE LOGIC
# -------------------------
def compute_valid(data: dict) -> bool:
    # -----------------------------
    # 1. Evidence strength weighting
    # -----------------------------
    base_score = data["integrity_score"] / 100.0

    friction = data["friction_score"]

    mcl = data["mcl_coefficient"]

    driver_weight = {
        "H1": 1.0,
        "H2": 0.9,
        "H3": 0.8
    }.get(data["primary_driver"], 0.5)

    boundary_strength = 1.0 if data["boundary"].strip() else 0.0

    # -----------------------------
    # 2. Enhanced truth score model
    # -----------------------------
    truth_score = (
        base_score * 0.35 +
        mcl * 0.35 +
        (1 - friction) * 0.20 +
        driver_weight * 0.10
    )

    # -----------------------------
    # 3. Decision threshold
    # -----------------------------
    return truth_score >= 0.62 and boundary_strength > 0


# -------------------------
# VALIDATE ENDPOINT
# -------------------------
@app.post("/validate")
def validate(payload: AuditPayload):
    try:
        data = payload.model_dump()

        valid = compute_valid(data)

        return {
            "valid": valid,
            "audit_id": data["audit_id"],
            "primary_driver": data["primary_driver"],
            "mcl_coefficient": data["mcl_coefficient"],
            "friction_score": data["friction_score"],
            "validated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "SERVER_ERROR",
                "message": str(e)
            }
        )
        # Validate structure
        data = AuditPayload(**payload).model_dump()

        valid = compute_valid(data)

        return {
            "valid": valid,
            "audit_id": data["audit_id"],
            "primary_driver": data["primary_driver"],
            "mcl_coefficient": data["mcl_coefficient"],
            "friction_score": data["friction_score"],
            "validated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_PAYLOAD",
                "missing_or_invalid": e.errors()
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "SERVER_ERROR",
                "message": str(e)
            }
        )
