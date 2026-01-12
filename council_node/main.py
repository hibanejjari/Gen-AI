"""
Council Node Service - Individual LLM council member.

Each council node can:
1. Generate opinions (Stage 1)
2. Review and rank opinions (Stage 2)

Run with: uvicorn council_node.main:app --host 0.0.0.0 --port 5001
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
import requests
import json
import re
import os
import time
from datetime import datetime

# ================== Configuration ==================
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:1b")
NODE_ID = os.getenv("NODE_ID", "council-1")
NODE_NAME = os.getenv("NODE_NAME", "Council Member")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

app = FastAPI(
    title=f"LLM Council Node - {NODE_ID}",
    description="Individual council member service",
    version="2.0.0"
)

# CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track service stats
stats = {
    "start_time": datetime.now().isoformat(),
    "opinions_generated": 0,
    "reviews_completed": 0,
    "errors": 0
}


# ================== Request/Response Models ==================

class HealthResponse(BaseModel):
    status: str
    node_id: str
    model: str
    ollama_status: str
    uptime_seconds: float
    stats: dict


class OpinionRequest(BaseModel):
    question: str
    context: Optional[str] = None


class OpinionResponse(BaseModel):
    node_id: str
    model: str
    answer: str
    generation_time_ms: float


class ReviewRequest(BaseModel):
    question: str
    responses: Dict[str, str]  # {"A": "answer text", "B": "answer text", ...}


class ReviewResponse(BaseModel):
    node_id: str
    model: str
    review: dict
    raw_output: Optional[str] = None
    generation_time_ms: float


class InfoResponse(BaseModel):
    node_id: str
    name: str
    role: str
    model: str
    ollama_url: str
    description: str


# ================== Helper Functions ==================

def check_ollama_status() -> str:
    """Check if Ollama is running and model is available."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if r.status_code != 200:
            return "ollama_unreachable"

        models = r.json().get("models", [])
        model_names = [m.get("name", "") for m in models]

        if MODEL_NAME in model_names:
            return "ready"

        base_model = MODEL_NAME.split(":")[0]
        for name in model_names:
            if name.startswith(base_model):
                return "ready"

        return f"model_not_found:{MODEL_NAME}"

    except requests.exceptions.ConnectionError:
        return "ollama_not_running"
    except Exception as e:
        return f"error:{str(e)}"


def generate_with_ollama(prompt: str, timeout: int = OLLAMA_TIMEOUT) -> tuple[str, float]:
    """
    Generate text using Ollama API.

    Returns: (response_text, generation_time_ms)
    """
    start_time = time.time()

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
        }
    }

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()

        elapsed = (time.time() - start_time) * 1000
        return response.json().get("response", ""), elapsed

    except requests.Timeout:
        raise HTTPException(status_code=504, detail=f"Ollama generation timed out after {timeout}s")
    except requests.ConnectionError:
        raise HTTPException(status_code=503, detail="Cannot connect to Ollama service")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")


def parse_review_json(raw_output: str) -> dict:
    """
    Extract JSON from LLM output with fallback parsing.
    Handles cases where LLM adds explanation text around JSON.
    """
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        pass

    json_patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
        r'(\{.*\})',
    ]

    for pattern in json_patterns:
        match = re.search(pattern, raw_output, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

    start = raw_output.find('{')
    end = raw_output.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw_output[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from output: {raw_output[:200]}...")


def _to_float_or_default(x, default: float) -> float:
    try:
        return float(x)
    except Exception:
        return default


def normalize_review(review_data: dict, labels: list[str]) -> dict:
    """
    Ensure:
    - scores exist for every label
    - each score has numeric accuracy and insight in [0,10]
    - ranking exists and uses only allowed labels
    """
    if not isinstance(review_data, dict):
        review_data = {}

    scores = review_data.get("scores", {})
    if not isinstance(scores, dict):
        scores = {}

    fixed_scores: dict = {}
    for lbl in labels:
        s = scores.get(lbl, {})
        if not isinstance(s, dict):
            s = {}

        acc = _to_float_or_default(s.get("accuracy", 5), 5.0)
        ins = _to_float_or_default(s.get("insight", 5), 5.0)

        acc = max(0.0, min(10.0, acc))
        ins = max(0.0, min(10.0, ins))

        fixed_scores[lbl] = {"accuracy": acc, "insight": ins}

    review_data["scores"] = fixed_scores

    ranking = review_data.get("ranking", [])
    if not isinstance(ranking, list) or not ranking:
        review_data["ranking"] = labels
    else:
        filtered = [x for x in ranking if x in labels]
        # If model outputs duplicates or misses labels, fall back to full label list
        review_data["ranking"] = filtered if len(filtered) == len(set(filtered)) and filtered else labels

    return review_data


# ================== API Endpoints ==================

@app.get("/health", response_model=HealthResponse)
def health_check():
    start = datetime.fromisoformat(stats["start_time"])
    uptime = (datetime.now() - start).total_seconds()
    ollama_status = check_ollama_status()

    return HealthResponse(
        status="healthy" if ollama_status == "ready" else "degraded",
        node_id=NODE_ID,
        model=MODEL_NAME,
        ollama_status=ollama_status,
        uptime_seconds=uptime,
        stats=stats
    )


@app.post("/opinion", response_model=OpinionResponse)
def generate_opinion(request: OpinionRequest):
    prompt = f"""You are an expert analyst providing a thoughtful answer.

Question: {request.question}

{f"Additional context: {request.context}" if request.context else ""}

Provide a clear, well-reasoned answer. Be concise but thorough.

Answer:"""

    try:
        answer, elapsed = generate_with_ollama(prompt)
        stats["opinions_generated"] += 1

        return OpinionResponse(
            node_id=NODE_ID,
            model=MODEL_NAME,
            answer=answer.strip(),
            generation_time_ms=elapsed
        )
    except Exception:
        stats["errors"] += 1
        raise


@app.post("/answer", response_model=OpinionResponse)
def generate_answer(data: dict):
    """Legacy endpoint for backward compatibility. Maps to /opinion."""
    request = OpinionRequest(question=data.get("question", ""))
    return generate_opinion(request)


@app.post("/review", response_model=ReviewResponse)
def review_responses(request: ReviewRequest):
    """
    Stage 2: Review and rank anonymized responses.

    NOTE:
    - We do NOT change the evaluation prompt logic.
    - We normalize outputs so accuracy/insight are never missing (prevents UI N/A).
    """
    # Keep deterministic ordering for prompt & labels
    labels = sorted(request.responses.keys())
    labels_str = ", ".join(labels)

    formatted = "\n\n".join([
        f"=== Response {label} ===\n{request.responses[label]}"
        for label in labels
    ])

    prompt = f"""You are a STRICT evaluator. Your task is to evaluate the responses below.

QUESTION (for context):
{request.question}

RESPONSES TO EVALUATE:
{formatted}

TASK:
1. Score EACH response on:
   - accuracy (0-10): How correct and factual is the response?
   - insight (0-10): How insightful and valuable is the response?

2. Rank all responses from BEST to WORST.

IMPORTANT RULES:
- Output ONLY valid JSON, nothing else
- Use ONLY these labels: {labels_str}
- No explanations, no markdown, just JSON

OUTPUT FORMAT:
{{
  "scores": {{
    "{labels[0]}": {{"accuracy": 0, "insight": 0}}{"," if len(labels) > 1 else ""}
    {f'"{labels[1]}": {{"accuracy": 0, "insight": 0}}' if len(labels) > 1 else ""}
  }},
  "ranking": ["{labels[0]}"{f', "{labels[1]}"' if len(labels) > 1 else ""}]
}}

YOUR EVALUATION (JSON only):"""

    try:
        raw_output, elapsed = generate_with_ollama(prompt, timeout=90)

        try:
            review_data = parse_review_json(raw_output)
            review_data = normalize_review(review_data, labels)

            stats["reviews_completed"] += 1

            return ReviewResponse(
                node_id=NODE_ID,
                model=MODEL_NAME,
                review=review_data,
                raw_output=raw_output[:500],
                generation_time_ms=elapsed
            )

        except ValueError:
            stats["errors"] += 1
            # Safe fallback (never produces N/A)
            fallback = {
                "error": "Failed to parse review",
                "scores": {label: {"accuracy": 5.0, "insight": 5.0} for label in labels},
                "ranking": labels
            }
            return ReviewResponse(
                node_id=NODE_ID,
                model=MODEL_NAME,
                review=fallback,
                raw_output=raw_output[:500],
                generation_time_ms=elapsed
            )

    except Exception:
        stats["errors"] += 1
        raise


@app.get("/info", response_model=InfoResponse)
def get_info():
    return InfoResponse(
        node_id=NODE_ID,
        name=NODE_NAME,
        role="council_member",
        model=MODEL_NAME,
        ollama_url=OLLAMA_URL,
        description="Independent LLM council member providing opinions and reviews"
    )


@app.get("/")
def root():
    return {
        "service": "LLM Council Node",
        "node_id": NODE_ID,
        "version": "2.0.0",
        "endpoints": ["/health", "/opinion", "/review", "/info"]
    }


# ================== Main ==================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "5001"))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"""
╔══════════════════════════════════════════════════════════╗
║           LLM Council Node - {NODE_ID:^16}           ║
╠══════════════════════════════════════════════════════════╣
║  Model:  {MODEL_NAME:<45} ║
║  Host:   {host:<45} ║
║  Port:   {port:<45} ║
║  Ollama: {OLLAMA_URL:<45} ║
╚══════════════════════════════════════════════════════════╝
""")

    uvicorn.run(app, host=host, port=port)
