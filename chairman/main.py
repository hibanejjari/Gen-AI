"""
Chairman Service - Final synthesis of council opinions.

The Chairman:
1. Receives all opinions from Stage 1
2. Receives all reviews from Stage 2
3. Synthesizes the final answer (Stage 3)

MUST run on a separate machine as per project requirements.

Run with: uvicorn chairman.main:app --host 0.0.0.0 --port 9000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, List
import requests
import os
import time
from datetime import datetime

# Configuration from environment
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:1b")
CHAIRMAN_ID = os.getenv("CHAIRMAN_ID", "chairman")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))

app = FastAPI(
    title="LLM Council Chairman",
    description="Chairman service for final answer synthesis",
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
    "syntheses_completed": 0,
    "errors": 0
}


# ============== Request/Response Models ==============

class HealthResponse(BaseModel):
    status: str
    chairman_id: str
    model: str
    ollama_status: str
    uptime_seconds: float
    stats: dict


class SynthesisRequest(BaseModel):
    question: str
    answers: Dict[str, str]       # {"A": "answer...", "B": "answer...", ...}
    reviews: Dict[str, dict]      # {"model1": {"scores": {...}, "ranking": [...]}, ...}


class SynthesisResponse(BaseModel):
    chairman_id: str
    model: str
    final_answer: str
    synthesis_time_ms: float
    input_summary: dict


class InfoResponse(BaseModel):
    chairman_id: str
    role: str
    model: str
    ollama_url: str
    description: str


# ============== Helper Functions ==============

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
    """Generate text using Ollama API."""
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
        raise HTTPException(
            status_code=504,
            detail=f"Ollama generation timed out after {timeout}s"
        )
    except requests.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Ollama service"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ollama error: {str(e)}"
        )


def calculate_answer_scores(reviews: Dict[str, dict]) -> Dict[str, float]:
    """
    Calculate aggregate scores for each answer based on all reviews.
    
    Returns dict mapping answer labels to average scores.
    """
    scores = {}
    
    for reviewer, review_data in reviews.items():
        if isinstance(review_data, dict) and "scores" in review_data:
            for label, score_data in review_data["scores"].items():
                if label not in scores:
                    scores[label] = {"accuracy": [], "insight": []}
                
                if isinstance(score_data, dict):
                    if "accuracy" in score_data:
                        scores[label]["accuracy"].append(score_data["accuracy"])
                    if "insight" in score_data:
                        scores[label]["insight"].append(score_data["insight"])
    
    # Calculate averages
    avg_scores = {}
    for label, score_lists in scores.items():
        acc = score_lists["accuracy"]
        ins = score_lists["insight"]
        avg_scores[label] = {
            "avg_accuracy": sum(acc) / len(acc) if acc else 0,
            "avg_insight": sum(ins) / len(ins) if ins else 0,
            "total": (sum(acc) / len(acc) + sum(ins) / len(ins)) / 2 if acc and ins else 0
        }
    
    return avg_scores


# ============== API Endpoints ==============

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint - CRITICAL for orchestrator monitoring."""
    start = datetime.fromisoformat(stats["start_time"])
    uptime = (datetime.now() - start).total_seconds()
    
    ollama_status = check_ollama_status()
    
    return HealthResponse(
        status="healthy" if ollama_status == "ready" else "degraded",
        chairman_id=CHAIRMAN_ID,
        model=MODEL_NAME,
        ollama_status=ollama_status,
        uptime_seconds=uptime,
        stats=stats
    )


@app.post("/synthesize", response_model=SynthesisResponse)
def synthesize_final_answer(request: SynthesisRequest):
    """
    Stage 3: Synthesize final answer from all opinions and reviews.
    
    The Chairman analyzes all inputs and produces a single, high-quality answer.
    """
    # Calculate aggregate scores
    avg_scores = calculate_answer_scores(request.reviews)
    
   # Format answers with their scores
    formatted_answers = []
    for label, answer in sorted(request.answers.items()):
        score_info = avg_scores.get(label, {})
        avg_acc = score_info.get('avg_accuracy', 0)
        avg_ins = score_info.get('avg_insight', 0)
        
        # Handle case when no reviews exist
        if avg_acc == 0 and avg_ins == 0:
            score_text = "[No peer reviews]"
        else:
            score_text = f"[Avg Accuracy: {avg_acc:.1f}/10, Avg Insight: {avg_ins:.1f}/10]"
        
        formatted_answers.append(
            f"=== Answer {label} ===\n"
            f"{score_text}\n"
            f"{answer}"
        )
    answers_text = "\n\n".join(formatted_answers)
    
    # Format review summaries
    review_summaries = []
    for reviewer, review_data in request.reviews.items():
        if isinstance(review_data, dict):
            ranking = review_data.get("ranking", [])
            review_summaries.append(f"- {reviewer}: ranked {' > '.join(ranking)}")
    reviews_text = "\n".join(review_summaries) if review_summaries else "No rankings available"
    
    prompt = f"""You are the CHAIRMAN of an expert council of AI analysts.

Your task is to synthesize a FINAL, DEFINITIVE answer based on the council's work.

ORIGINAL QUESTION:
{request.question}

COUNCIL ANSWERS (with peer review scores):
{answers_text}

PEER REVIEW RANKINGS:
{reviews_text}

INSTRUCTIONS FOR SYNTHESIS:
1. Consider all answers, giving more weight to higher-scored responses
2. Combine the best insights from multiple answers
3. Correct any errors identified in lower-scored answers
4. Produce ONE clear, comprehensive final answer
5. Do NOT mention reviewers, scores, labels, or the review process
6. Do NOT explain your synthesis process
7. Write as if this is the direct answer to the user's question

FINAL ANSWER:"""

    try:
        final_answer, elapsed = generate_with_ollama(prompt)
        stats["syntheses_completed"] += 1
        
        return SynthesisResponse(
            chairman_id=CHAIRMAN_ID,
            model=MODEL_NAME,
            final_answer=final_answer.strip(),
            synthesis_time_ms=elapsed,
            input_summary={
                "num_answers": len(request.answers),
                "num_reviews": len(request.reviews),
                "score_summary": avg_scores
            }
        )
    except Exception as e:
        stats["errors"] += 1
        raise


@app.post("/finalize")
def finalize_legacy(data: dict):
    """
    Legacy endpoint for backward compatibility.
    Maps to /synthesize endpoint.
    """
    request = SynthesisRequest(
        question=data.get("question", ""),
        answers=data.get("answers", {}),
        reviews=data.get("reviews", {})
    )
    result = synthesize_final_answer(request)
    return {"final_answer": result.final_answer}


@app.get("/info", response_model=InfoResponse)
def get_info():
    """Get information about the chairman service."""
    return InfoResponse(
        chairman_id=CHAIRMAN_ID,
        role="chairman",
        model=MODEL_NAME,
        ollama_url=OLLAMA_URL,
        description="Council Chairman - synthesizes final answers from council opinions and reviews"
    )


@app.get("/")
def root():
    """Root endpoint with basic info."""
    return {
        "service": "LLM Council Chairman",
        "chairman_id": CHAIRMAN_ID,
        "version": "2.0.0",
        "endpoints": ["/health", "/synthesize", "/info"]
    }


# ============== Main ==============

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "9000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║              LLM Council Chairman                        ║
╠══════════════════════════════════════════════════════════╣
║  Model:  {MODEL_NAME:<45} ║
║  Host:   {host:<45} ║
║  Port:   {port:<45} ║
║  Ollama: {OLLAMA_URL:<45} ║
╚══════════════════════════════════════════════════════════╝
""")
    
    uvicorn.run(app, host=host, port=port)
