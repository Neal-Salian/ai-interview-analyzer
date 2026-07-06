"""
Candidate Attribution Service.

Separates raw transcript text into Candidate and Recruiter segments using LLM reasoning.
Implements windowing, retries, and strict ID-based attribution to preserve original text.
"""

import json
import logging
import asyncio
import time
from typing import Dict, Any, List

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

async def perform_attribution(
    transcripts: List[Dict[str, Any]], 
    candidate_name: str, 
    job_title: str,
    recent_questions: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calls the LLM to attribute each transcript chunk to Candidate or Recruiter.
    Uses sliding windows to provide context and limit prompt size.
    
    Returns:
    {
      "segments": [
        {
          "speaker": "Candidate" | "Recruiter" | "Unknown",
          "text": "...",
          "confidence": 0.95,
          "reason": "...",
          "attribution_method": "llm",
          "timestamp": "..."
        }
      ],
      "metadata": {
         "model": "...",
         "prompt_version": "1.0",
         "processing_timestamp": "...",
         "average_confidence": 0.9,
         "processing_duration_sec": 5.0,
         "total_windows": 5,
         "successful_windows": 5,
         "retries_performed": 0,
         "fallback_windows": 0
      }
    }
    """
    if not transcripts:
        return {"segments": [], "metadata": {}}

    start_time = time.time()
    
    window_size = settings.ATTRIBUTION_WINDOW_SIZE
    prev_ctx = settings.ATTRIBUTION_PREVIOUS_CONTEXT
    next_ctx = settings.ATTRIBUTION_NEXT_CONTEXT
    min_conf = settings.ATTRIBUTION_MIN_CONFIDENCE
    max_concurrent = settings.MAX_CONCURRENT_ATTRIBUTION
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    questions_context = ""
    if recent_questions:
        q_texts = [q.get("question_text") for q in recent_questions if q.get("question_text")]
        if q_texts:
            questions_context = "Recent questions suggested to the recruiter:\n" + "\n".join(f"- {q}" for q in q_texts)

    windows = []
    for i in range(0, len(transcripts), window_size):
        window_chunks = transcripts[i:i+window_size]
        prev_chunks = transcripts[max(0, i-prev_ctx):i]
        next_chunks = transcripts[i+window_size:i+window_size+next_ctx]
        windows.append((i, prev_chunks, window_chunks, next_chunks))

    stats = {
        "total_windows": len(windows),
        "successful_windows": 0,
        "retries_performed": 0,
        "fallback_windows": 0,
        "total_confidence": 0.0,
        "attributed_chunks": 0
    }

    async def process_window(start_idx: int, prev: List[Dict], current: List[Dict], nxt: List[Dict]) -> List[Dict]:
        async with semaphore:
            return await _attribute_window(
                start_idx=start_idx,
                prev_chunks=prev,
                current_chunks=current,
                next_chunks=nxt,
                candidate_name=candidate_name,
                job_title=job_title,
                questions_context=questions_context,
                min_conf=min_conf,
                stats=stats
            )

    tasks = [process_window(*w) for w in windows]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Flatten results and handle any top-level exceptions safely
    final_segments = []
    for r, w in zip(results, windows):
        current_chunks = w[2]
        if isinstance(r, Exception):
            logger.error(f"[candidate_attribution] Top level window gather failed: {r}")
            stats["fallback_windows"] += 1
            for idx, chunk in enumerate(current_chunks):
                final_segments.append({
                    "speaker": "Unknown",
                    "text": chunk.get("text", ""),
                    "confidence": 0.0,
                    "reason": "System failure during attribution.",
                    "attribution_method": "fallback",
                    "timestamp": chunk.get("timestamp")
                })
        else:
            final_segments.extend(r)
            
    # Sort by original start_idx mapping if needed, but gather returns in order
    duration = time.time() - start_time
    avg_conf = stats["total_confidence"] / stats["attributed_chunks"] if stats["attributed_chunks"] > 0 else 0.0
    
    metadata = {
        "model": settings.OLLAMA_MODEL,
        "prompt_version": "1.1",
        "processing_timestamp": time.time(),
        "average_confidence": round(avg_conf, 3),
        "processing_duration_sec": round(duration, 2),
        "total_windows": stats["total_windows"],
        "successful_windows": stats["successful_windows"],
        "retries_performed": stats["retries_performed"],
        "fallback_windows": stats["fallback_windows"]
    }
    
    logger.info(f"[candidate_attribution] Attribution complete. Stats: {json.dumps(metadata)}")
    
    return {
        "segments": final_segments,
        "metadata": metadata
    }

async def _attribute_window(
    start_idx: int,
    prev_chunks: List[Dict],
    current_chunks: List[Dict],
    next_chunks: List[Dict],
    candidate_name: str,
    job_title: str,
    questions_context: str,
    min_conf: float,
    stats: Dict[str, Any]
) -> List[Dict]:
    
    def format_chunks(chunks, offset):
        return "\n".join([f"[{offset+i}] {c.get('text', '')}" for i, c in enumerate(chunks)])

    prev_text = format_chunks(prev_chunks, start_idx - len(prev_chunks))
    curr_text = format_chunks(current_chunks, start_idx)
    next_text = format_chunks(next_chunks, start_idx + len(current_chunks))
    
    def build_prompt(simplified=False):
        sys_instructions = (
            "You are an AI interview analyzer. Your task is to perform Candidate Attribution. "
            "You will be given a set of transcript chunks. Attribute ONLY the 'TARGET CHUNKS' to 'Candidate', 'Recruiter', or 'Unknown'."
        )
        if simplified:
            sys_instructions += " Keep your reasons extremely brief."
            
        return f"""{sys_instructions}

CONTEXT:
Candidate Name: {candidate_name if candidate_name else 'Unknown'}
Job Title: {job_title if job_title else 'Unknown'}
{questions_context}

PREVIOUS CONTEXT (Do not attribute):
{prev_text}

TARGET CHUNKS (Attribute these!):
{curr_text}

NEXT CONTEXT (Do not attribute):
{next_text}

INSTRUCTIONS:
1. For each target chunk ID, output the speaker ("Candidate", "Recruiter", or "Unknown").
2. Do NOT guess if you are unsure. Use "Unknown" for low confidence.
3. Provide a confidence score (0.0 to 1.0) and a brief reason.
4. Output MUST be exactly in the JSON format below.

OUTPUT FORMAT:
{{
  "attributions": [
    {{
      "id": {start_idx},
      "speaker": "Candidate",
      "confidence": 0.95,
      "reason": "Answering question"
    }}
  ]
}}
"""

    async def call_llm(prompt: str) -> Dict:
        async with httpx.AsyncClient(timeout=settings.ATTRIBUTION_RETRY_TIMEOUT) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "keep_alive": settings.OLLAMA_KEEP_ALIVE,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 2048,
                    }
                }
            )
            response.raise_for_status()
            raw = response.json().get("response", "")
            
            clean = raw.strip()
            if "```" in clean:
                parts = clean.split("```")
                clean = parts[1] if len(parts) >= 2 else clean
                if clean.startswith("json"):
                    clean = clean[4:]
            
            start = clean.find("{")
            end = clean.rfind("}") + 1
            if start != -1 and end != 0:
                clean = clean[start:end]
                
            return json.loads(clean)

    # Retry logic
    try:
        result = await call_llm(build_prompt(simplified=False))
        stats["successful_windows"] += 1
    except Exception as e:
        logger.warning(f"[candidate_attribution] Window {start_idx} failed: {e}. Retrying with backoff...")
        stats["retries_performed"] += 1
        await asyncio.sleep(settings.ATTRIBUTION_RETRY_BACKOFF)
        try:
            result = await call_llm(build_prompt(simplified=True))
            stats["successful_windows"] += 1
        except Exception as e2:
            logger.error(f"[candidate_attribution] Window {start_idx} retry failed: {e2}. Falling back to Unknown.")
            stats["fallback_windows"] += 1
            result = {"attributions": []}

    # Map results back to original text chunks
    attributions_map = {}
    if "attributions" in result and isinstance(result["attributions"], list):
        for attr in result["attributions"]:
            if "id" in attr:
                attributions_map[attr["id"]] = attr
                
    segments = []
    for i, chunk in enumerate(current_chunks):
        c_id = start_idx + i
        attr = attributions_map.get(c_id, {})
        
        speaker = attr.get("speaker", "Unknown")
        conf = float(attr.get("confidence", 0.0))
        reason = attr.get("reason", "No attribution returned")
        method = "llm"
        
        if speaker not in ("Candidate", "Recruiter"):
            speaker = "Unknown"
            
        if conf < min_conf:
            speaker = "Unknown"
            reason = f"Confidence {conf} below threshold {min_conf}"
            
        if not attributions_map:
            method = "fallback"
            reason = "Attribution service failed. Defaulting to Unknown."
            
        segments.append({
            "speaker": speaker,
            "text": chunk.get("text", ""),
            "confidence": conf,
            "reason": reason,
            "attribution_method": method,
            "timestamp": chunk.get("timestamp")
        })
        
        stats["total_confidence"] += conf
        stats["attributed_chunks"] += 1
        
    return segments
