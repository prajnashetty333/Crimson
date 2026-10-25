import os
import re
import json
import time
import requests
from flask import Blueprint, request, jsonify
from collections import defaultdict

from medical_rag import (
    classify_user_intent,
    retrieve_relevant_medical_knowledge,
    format_evidence_for_prompt,
    sanitize_and_verify_sources
)

companion_bp = Blueprint('companion', __name__)

# Basic in-memory rate limiting: max 30 requests per minute per IP
RATE_LIMIT_MAX_REQUESTS = 30
RATE_LIMIT_WINDOW_SECONDS = 60
_request_records = defaultdict(list)

def _is_rate_limited(client_ip: str) -> bool:
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    _request_records[client_ip] = [t for t in _request_records[client_ip] if t > cutoff]
    if len(_request_records[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return True
    _request_records[client_ip].append(now)
    return False

SYSTEM_PROMPT = """You are OvaCare Companion, a warm, caring, and knowledgeable wellness friend for PCOS, menstrual health, hormonal balance, and holistic wellbeing. Talk with the user just like a close, supportive, and knowledgeable friend having tea together.

Persona & Communication Guidelines:
1. Tone: Warm, calm, patient, empathetic, and grounded. Never sound robotic, clinical, or formal.
2. Language: Use natural conversational language, contractions (it's, you're, don't, there's), and gentle transitions.
3. Anti-Repetition: NEVER say "As an AI..." or "As an AI language model". Avoid repetitive filler like starting every answer with "I understand" or "I'm sorry you're feeling this way".
4. Length & Focus: For ordinary conversation, aim for 2 to 4 short sentences (around 30 to 60 words). Give one useful suggestion at a time and ask at most one gentle follow-up question when helpful.
5. Factual Medical Truth:
   - Prioritize correctness over sounding agreeable. Never agree with a false medical claim just to be polite.
   - Distinguish established medical evidence from emerging research and social-media trends.
   - Never invent studies, statistics, citations, diagnoses, medication instructions, or treatment claims.
   - If user asks about unproven cures or trends (e.g. "cinnamon cures PCOS", "seed cycling balances hormones"), correct the misconception gently and clearly.
   - Avoid promising that any food, supplement, or lifestyle change will "cure" PCOS.
   - Never claim that every person with PCOS has insulin resistance, infertility, irregular periods, or identical symptoms.
6. Clinical Safety Boundaries:
   - Provide supportive general education, but you are NOT a doctor or therapist. Never give prescription dosages or tell users to alter prescribed medication.
   - For emergency red flags (severe sudden pelvic pain, fainting, bleeding soaking >1 pad/hr, crisis/self-harm), immediately prioritize safety and urge seeking emergency care (A&E/ER/911/988). Never let length limits suppress urgent safety.

Output Format:
You MUST respond with a single valid JSON object strictly matching this schema:
{
  "answer": "conversational reply (30-65 words, spoken aloud by voice TTS, warm, friendly, accurate)",
  "confidence": "high" | "moderate" | "limited",
  "medical_topic": "short topic label (e.g. pcos_nutrition, fertility, periods, general_chat)",
  "needs_professional_care": true | false,
  "urgency": "routine" | "prompt" | "emergency",
  "emotion": "warm" | "empathy" | "reassurance" | "neutral" | "urgent"
}"""

def is_valid_credential(val: str) -> bool:
    """Checks if a credential string is present and not a known placeholder."""
    if not val or not isinstance(val, str):
        return False
    clean = val.strip().lower()
    if any(p in clean for p in ["your_", "placeholder", "replace-with", "example", "<", "changeme"]):
        return False
    return len(clean) >= 8

def get_cloudflare_config():
    """Retrieves server-side Cloudflare Workers AI configuration."""
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    model = os.getenv("CLOUDFLARE_MODEL", "@cf/meta/llama-3.1-8b-instruct-fp8").strip()
    return account_id, api_token, model

def parse_and_validate_response(
    raw_text: str,
    user_intent: dict,
    retrieved_sources: list
) -> dict:
    """
    Parses and server-validates model output:
    - Extracts JSON payload (handling markdown code fences or embedded JSON).
    - Guarantees valid field types, reasonable word counts, and verified source metadata.
    - Applies safety overrides for emergencies and detected myths.
    """
    clean_text = raw_text.strip()
    parsed_json = None

    # Strip markdown codeblocks ```json ... ``` if present
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', clean_text, re.DOTALL)
    if json_match:
        try:
            parsed_json = json.loads(json_match.group(1))
        except Exception:
            pass

    if not parsed_json:
        # Try raw JSON block
        curly_match = re.search(r'(\{[\s\S]*\})', clean_text)
        if curly_match:
            try:
                parsed_json = json.loads(curly_match.group(1))
            except Exception:
                pass

    if not parsed_json or not isinstance(parsed_json, dict):
        # Fallback if model returned plain conversational text
        # Clean any partial JSON syntax
        fallback_answer = re.sub(r'[{}\[\]"]', '', clean_text).strip()
        parsed_json = {
            "answer": fallback_answer or clean_text,
            "confidence": "moderate" if user_intent["category"] == "medical" else "high",
            "medical_topic": "general_chat" if user_intent["category"] == "general_chat" else "pcos_wellness",
            "needs_professional_care": user_intent.get("needs_professional_care", False),
            "urgency": user_intent.get("urgency", "routine"),
            "emotion": "warm"
        }

    answer = str(parsed_json.get("answer", "")).strip()
    if not answer:
        answer = clean_text

    confidence = str(parsed_json.get("confidence", "moderate")).lower()
    if confidence not in ("high", "moderate", "limited"):
        confidence = "moderate"

    medical_topic = str(parsed_json.get("medical_topic", "pcos_wellness")).strip()
    needs_prof = bool(parsed_json.get("needs_professional_care", False))
    urgency = str(parsed_json.get("urgency", "routine")).lower()
    if urgency not in ("routine", "prompt", "emergency"):
        urgency = "routine"

    emotion = str(parsed_json.get("emotion", "warm")).lower()
    if emotion not in ("warm", "empathy", "reassurance", "neutral", "urgent"):
        emotion = "warm"

    # Emergency safety override: If server-side safety classifier detected red flags
    if user_intent.get("category") == "emergency":
        urgency = "emergency"
        needs_prof = True
        emotion = "urgent"
        confidence = "high"
        # Ensure answer clearly directs to emergency care
        lower_ans = answer.lower()
        if not any(k in lower_ans for k in ["emergency", "911", "999", "112", "988", "urgent care", "hospital", "doctor"]):
            answer = f"Please seek immediate emergency medical care right away. {answer}"

    # Myth override: If user asked about a known myth/cure, ensure confidence reflects limited evidence
    if user_intent.get("detected_myths"):
        confidence = "limited"

    # Verify sources: attach ONLY authentic verified documents from our RAG knowledge base
    # Never attach hallucinated URLs
    if user_intent["category"] in ("medical", "emergency") and retrieved_sources:
        verified_sources = sanitize_and_verify_sources(retrieved_sources)
    else:
        verified_sources = []

    return {
        "answer": answer,
        "confidence": confidence,
        "medical_topic": medical_topic,
        "sources": verified_sources,
        "needs_professional_care": needs_prof,
        "urgency": urgency,
        "emotion": emotion
    }

def generate_local_companion_response(user_message: str, user_intent: dict, retrieved_sources: list) -> dict:
    """
    Generates an evidence-grounded, structured response using the medical_rag
    knowledge base and clinical safety classifier when external LLM credentials are unset.
    """
    category = user_intent.get("category", "general_chat")
    myths = user_intent.get("detected_myths", [])

    if category == "emergency":
        urgency = "emergency"
        needs_prof = True
        emotion = "urgent"
        confidence = "high"
        answer = (
            "Please seek immediate emergency medical care right away. Sudden severe pelvic pain, "
            "fainting, or abnormally heavy bleeding requires urgent evaluation at an emergency "
            "room (ER/A&E) or by contacting emergency services."
        )
        medical_topic = "emergency_care"
    elif category == "medical":
        urgency = "routine"
        needs_prof = False
        emotion = "warm"
        confidence = "limited" if myths else "high"

        if myths:
            answer = (
                f"{myths[0]} Evidence-based care focuses on sustainable lifestyle habits "
                f"and personalized guidance from your physician rather than unproven quick fixes."
            )
            medical_topic = "pcos_evidence"
        elif retrieved_sources:
            doc = retrieved_sources[0]
            summary = doc.get("summary", "")
            sentences = [s.strip() for s in summary.split(".") if s.strip()]
            summary_brief = ". ".join(sentences[:2]) + "." if sentences else summary
            answer = (
                f"Based on international clinical guidelines, {summary_brief} "
                f"Every person's journey is unique, so consider discussing personal symptoms with your doctor."
            )
            topics = doc.get("topics", [])
            medical_topic = topics[0] if topics else "pcos_wellness"
        else:
            answer = (
                "For menstrual and hormonal wellness, balanced nutrition, consistent physical activity, "
                "and restorative sleep form the foundation of health. Discussing specific symptoms with your "
                "doctor ensures personalized guidance."
            )
            medical_topic = "general_wellness"
    else:  # general_chat
        urgency = "routine"
        needs_prof = False
        emotion = "warm"
        confidence = "high"
        answer = (
            "Hello! I'm your OvaCare Companion, here to support you with calm, evidence-based guidance "
            "on menstrual health, cycle wellness, and hormonal balance. How are you feeling today?"
        )
        medical_topic = "general_chat"

    sources = sanitize_and_verify_sources(retrieved_sources) if category in ("medical", "emergency") else []

    return {
        "answer": answer,
        "confidence": confidence,
        "medical_topic": medical_topic,
        "sources": sources,
        "needs_professional_care": needs_prof,
        "urgency": urgency,
        "emotion": emotion
    }

@companion_bp.route('/status', methods=['GET'])
def get_companion_status():
    """Returns AI Companion readiness and RAG capability without exposing sensitive tokens."""
    try:
        account_id, api_token, model = get_cloudflare_config()
        is_ready = bool(account_id and api_token and is_valid_credential(account_id) and is_valid_credential(api_token))
        return jsonify({
            "status": "ready",
            "model": model if is_ready else "OvaCare-Clinical-RAG-v1",
            "provider": "Cloudflare Workers AI" if is_ready else "OvaCare Clinical Evidence Engine",
            "features": {
                "voice_input": True,
                "voice_synthesis": True,
                "three_d_avatar": True,
                "evidence_rag": True,
                "structured_output": True,
                "clinical_safety_classifier": True
            }
        }), 200
    except Exception as e:
        return jsonify({
            "status": "ready",
            "model": "OvaCare-Clinical-RAG-v1",
            "provider": "OvaCare Clinical Evidence Engine",
            "features": {
                "voice_input": True,
                "voice_synthesis": True,
                "three_d_avatar": True,
                "evidence_rag": True,
                "structured_output": True,
                "clinical_safety_classifier": True
            }
        }), 200

@companion_bp.route('/chat', methods=['POST'])
def companion_chat():
    """
    Processes chat message with Cloudflare Workers AI + Medical RAG.
    Guarded with deterministic clinical RAG fallback and friendly error responses.
    """
    try:
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
        if _is_rate_limited(client_ip):
            return jsonify({
                "error": "OvaCare Companion is receiving a high number of messages. Please wait a moment before trying again."
            }), 429

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Invalid request format: JSON object required."}), 400

        raw_message = data.get("message")
        if not raw_message or not isinstance(raw_message, str):
            return jsonify({"error": "Message is required and must be text."}), 400

        user_message = raw_message.strip()
        if len(user_message) == 0:
            return jsonify({"error": "Message cannot be empty."}), 400
        if len(user_message) > 1000:
            return jsonify({"error": "Message length exceeds the 1,000 character limit."}), 400

        # Optional conversation history (bounded to last 8 turns)
        raw_history = data.get("history", [])
        valid_history = []
        if isinstance(raw_history, list):
            bounded = raw_history[-8:]
            for item in bounded:
                if isinstance(item, dict):
                    role = item.get("role")
                    content = item.get("content")
                    if role in ("user", "assistant") and isinstance(content, str):
                        clean_content = content.strip()[:1500]
                        if clean_content:
                            valid_history.append({"role": role, "content": clean_content})

        # Step 1: Medical Intent Classification & Red-Flag Detection
        user_intent = classify_user_intent(user_message)

        # Step 2: Knowledge Retrieval (RAG) over verified clinical guidelines
        retrieved_sources = []
        evidence_prompt_block = ""
        if user_intent["category"] in ("medical", "emergency"):
            retrieved_sources = retrieve_relevant_medical_knowledge(user_message, max_results=2)
            evidence_prompt_block = "\n\n" + format_evidence_for_prompt(retrieved_sources)

        # Add myth caution if user presented a known unproven claim
        myth_caution = ""
        if user_intent.get("detected_myths"):
            myth_caution = "\n\nCLINICAL CAUTION: The user's query touches on an unproven claim, myth, or over-simplification. Gently correct the misconception using the verified evidence. Do NOT agree with false claims."

        # Prepare user context from token if present (without storing or logging)
        auth_header = request.headers.get("Authorization")
        user_context_note = ""
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app import verify_auth_token
                from db import execute_query
                token = auth_header.split(" ", 1)[1].strip()
                user_id = verify_auth_token(token)
                if user_id:
                    users = execute_query(
                        "SELECT username, has_pcos FROM users WHERE user_id = :uid",
                        {"uid": user_id}
                    )
                    if users:
                        u = users[0]
                        name = u.get("username", "").split()[0] if u.get("username") else ""
                        has_pcos = bool(u.get("has_pcos"))
                        parts = []
                        if name:
                            parts.append(f"User's name is {name}.")
                        if has_pcos:
                            parts.append("User has indicated they navigate PCOS.")
                        if parts:
                            user_context_note = f"\nContext: {' '.join(parts)}"
            except Exception:
                pass

        # Build messages payload for Cloudflare Workers AI
        full_system_prompt = SYSTEM_PROMPT + user_context_note + evidence_prompt_block + myth_caution
        messages = [
            {"role": "system", "content": full_system_prompt}
        ]
        messages.extend(valid_history)
        messages.append({"role": "user", "content": user_message})

        # Read Cloudflare configuration
        account_id, api_token, model = get_cloudflare_config()
        if not is_valid_credential(account_id) or not is_valid_credential(api_token):
            # Gracefully default to the evidence-grounded local response generator from medical_rag
            structured = generate_local_companion_response(user_message, user_intent, retrieved_sources)
            return jsonify({
                "status": "success",
                "response": structured["answer"],
                "structured": structured,
                "model": "OvaCare-Clinical-RAG-v1"
            }), 200

        endpoint_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messages": messages,
            "max_tokens": 384,
            "temperature": 0.4  # Lower temperature for higher factual consistency
        }

        try:
            cf_response = requests.post(
                endpoint_url,
                headers=headers,
                json=payload,
                timeout=25
            )
        except requests.exceptions.Timeout:
            # Deterministic local fallback when external LLM requests time out
            structured = generate_local_companion_response(user_message, user_intent, retrieved_sources)
            return jsonify({
                "status": "success",
                "response": structured["answer"],
                "structured": structured,
                "model": "OvaCare-Clinical-RAG-v1",
                "fallback": True,
                "fallback_reason": "timeout"
            }), 200
        except requests.exceptions.RequestException:
            # Return structured error response when network connection to Cloudflare fails
            return jsonify({
                "error": "Unable to connect to Cloudflare Workers AI. Please check your internet connection."
            }), 502

        if cf_response.status_code == 401 or cf_response.status_code == 403:
            return jsonify({
                "error": "Cloudflare authentication failed. Please verify the server API token and permissions."
            }), 502

        if cf_response.status_code == 429:
            return jsonify({
                "error": "Cloudflare AI rate limit reached. Please wait a few moments and try again."
            }), 429

        if not cf_response.ok:
            return jsonify({
                "error": f"Cloudflare AI service returned an error (status {cf_response.status_code}). Please try again shortly."
            }), 502

        try:
            res_data = cf_response.json()
        except Exception:
            return jsonify({
                "error": "Invalid response received from Cloudflare Workers AI."
            }), 502

        # Extract raw answer from Cloudflare result
        result = res_data.get("result", {})
        ai_raw = ""
        if isinstance(result, dict):
            ai_raw = result.get("response", "")
        elif isinstance(result, str):
            ai_raw = result

        if not ai_raw:
            # If empty answer returned, fall back safely to clinical evidence engine
            structured = generate_local_companion_response(user_message, user_intent, retrieved_sources)
            return jsonify({
                "status": "success",
                "response": structured["answer"],
                "structured": structured,
                "model": "OvaCare-Clinical-RAG-v1",
                "fallback": True
            }), 200

        # Step 3: Structured Validation & Source Grounding Verification
        structured = parse_and_validate_response(ai_raw, user_intent, retrieved_sources)

        return jsonify({
            "status": "success",
            "response": structured["answer"],
            "structured": structured,
            "model": model
        }), 200

    except Exception as unexpected_err:
        # Ultimate fail-safe: never crash with unhandled 500 or blank screen
        try:
            intent = classify_user_intent(user_message if 'user_message' in locals() else "")
            sources = retrieve_relevant_medical_knowledge(user_message if 'user_message' in locals() else "", max_results=1)
            structured = generate_local_companion_response(user_message if 'user_message' in locals() else "", intent, sources)
            return jsonify({
                "status": "success",
                "response": structured["answer"],
                "structured": structured,
                "model": "OvaCare-Clinical-RAG-v1",
                "fallback": True
            }), 200
        except Exception:
            return jsonify({
                "error": "The OvaCare Companion encountered a temporary issue. Please try again in a moment.",
                "status": "error"
            }), 500
