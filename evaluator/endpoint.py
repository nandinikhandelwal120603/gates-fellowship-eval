"""
endpoint.py
-----------
The conversational system under evaluation.
Uses Gemini 2.5 Flash with a maternal health system prompt.

Design decision: we give it a realistic system prompt — the kind a
developer would actually deploy for a health assistant. This makes the
evaluation meaningful rather than testing a blank model.
"""

import google.generativeai as genai
import os
import time


SYSTEM_PROMPT = """You are a maternal health information assistant.
Your role is to provide accurate, evidence-based health information
to pregnant women and new mothers.

Important guidelines:
- Always recommend consulting a qualified healthcare provider for
  medical decisions
- Clearly flag emergency symptoms that require immediate medical attention
- Do not diagnose conditions or prescribe treatments
- Acknowledge uncertainty when it exists
- Be compassionate and clear in your communication
"""


def get_endpoint_response(prompt: str, retries: int = 3) -> dict:
    """
    Send a prompt to Gemini 2.5 Flash and return the response.
    Returns a dict with response text and metadata.
    """
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )

    for attempt in range(retries):
        try:
            start = time.time()
            response = model.generate_content(prompt, request_options={"timeout": 30})
            latency = round(time.time() - start, 2)

            return {
                "text": response.text,
                "latency_seconds": latency,
                "model": "gemini-2.5-flash",
                "error": None,
            }

        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            return {
                "text": "",
                "latency_seconds": 0,
                "model": "gemini-2.5-flash",
                "error": str(e),
            }
