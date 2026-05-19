from fastapi import FastAPI, HTTPException
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
app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    time: new Date().toISOString()
  });
});
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
def compute_valid(data: dict):
    # -----------------------------
    # Base signals
    # -----------------------------
    base_score = data["integrity_score"] / 100.0
    friction = float(data.get("friction_score", 0))
    mcl = float(data.get("mcl_coefficient", 0))

    driver_weight = {
        "H1": 1.0,
        "H2": 0.9,
        "H3": 0.8
    }.get(data["primary_driver"], 0.5)

    boundary = data.get("boundary") or ""
    boundary_strength = 1.0 if boundary.strip() else 0.0

    # -----------------------------
    # Score components (NEW)
    # -----------------------------
    integrity_contrib = base_score * 0.35
    mcl_contrib = mcl * 0.35
    friction_contrib = (1 - friction) * 0.20
    driver_contrib = driver_weight * 0.10

    truth_score = (
        integrity_contrib +
        mcl_contrib +
        friction_contrib +
        driver_contrib
    )

    # -----------------------------
    # Decision
    # -----------------------------
    is_valid = truth_score >= 0.62 and boundary_strength > 0

    # -----------------------------
    # Confidence logic
    # -----------------------------
    if truth_score >= 0.75:
        confidence = "high"
    elif truth_score >= 0.55:
        confidence = "medium"
    else:
        confidence = "low"

    # -----------------------------
    # Explanation generator (simple, deterministic)
    # -----------------------------
    explanation_parts = []

    if base_score < 0.6:
        explanation_parts.append("Low integrity score reduces confidence")

    if friction > 0.6:
        explanation_parts.append("High friction indicates conflicting signals")

    if mcl < 0.6:
        explanation_parts.append("Weak evidence aggregation (MCL is low)")

    if driver_weight < 0.9:
        explanation_parts.append("Non-primary driver reduces causal strength")

    explanation = "; ".join(explanation_parts) if explanation_parts else "Signals are aligned and consistent"

    # -----------------------------
    # Return full internal object
    # -----------------------------
    return {
    "valid": is_valid,
    "truth_score": truth_score,
    "confidence": confidence,
    "explanation": explanation,
    "score_breakdown": {
        "integrity": round(integrity_contrib, 3),
        "mcl": round(mcl_contrib, 3),
        "friction": round(friction_contrib, 3),
        "driver": round(driver_contrib, 3)
    }
}
# -------------------------
# VALIDATE ENDPOINT
# -------------------------

@app.post("/validate")
def validate(payload: AuditPayload):
    try:
        data = payload.model_dump()
        result = compute_valid(data)

        return {
            "valid": result["valid"],
            "audit_id": data["audit_id"],
            "primary_driver": data["primary_driver"],
            "mcl_coefficient": data["mcl_coefficient"],
            "friction_score": data["friction_score"],
            "confidence": result["confidence"],
            "explanation": result["explanation"],
            "score_breakdown": result["score_breakdown"],
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
