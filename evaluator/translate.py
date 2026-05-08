"""
translate.py
------------
Translates prompts into Hindi, Urdu, and Tamil using Sarvam AI's
Mayura v1 translation model before sending to the endpoint.

Why these 3 languages?
- Hindi:  Most spoken language in India (~600M speakers)
- Urdu:   Critical for Muslim maternal health populations, 
          especially in UP, Bihar, Hyderabad
- Tamil:  South India coverage, very different script family

Character budget:
- ₹100 free credits on signup
- Translate costs ₹20 per 10,000 characters
- Our usage: ~150 chars × 15 prompts × 3 languages = ~6,750 chars
- Cost: ₹13.5 — fully covered by free credits
"""

import os
import time
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

# Language codes per Sarvam API docs
# All 22 Indian languages supported — we use 3 for coverage breadth
LANGUAGE_MAP = {
    "hindi": {"code": "hi-IN", "name": "Hindi"},
    "gujarati":  {"code": "gu-IN", "name": "Gujarati"},
    "tamil": {"code": "ta-IN", "name": "Tamil"},
}


def translate_prompt(text: str, target_language: str, retries: int = 3) -> dict:
    """
    Translate a single English prompt into the target language.

    Args:
        text: English prompt to translate
        target_language: "hindi", "urdu", or "tamil"
        retries: Retry attempts on failure

    Returns:
        dict with: translated_text, language, language_code, char_count, error
    """
    if not SARVAM_API_KEY:
        return {
            "translated_text": text,
            "language": target_language,
            "language_code": None,
            "char_count": 0,
            "error": "SARVAM_API_KEY not set — falling back to English",
        }

    lang_info = LANGUAGE_MAP.get(target_language.lower())
    if not lang_info:
        return {
            "translated_text": text,
            "language": target_language,
            "language_code": None,
            "char_count": 0,
            "error": f"Unsupported language: {target_language}. Choose from: {list(LANGUAGE_MAP.keys())}",
        }

    for attempt in range(retries):
        try:
            time.sleep(0.5)  # rate limit buffer

            client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
            response = client.text.translate(
                input=text,
                source_language_code="en-IN",
                target_language_code=lang_info["code"],
                speaker_gender="Female",
                mode="formal",
                model="mayura:v1",
            )

            translated = response.translated_text if response.translated_text else text
            return {
                "translated_text": translated,
                "language": lang_info["name"],
                "language_code": lang_info["code"],
                "char_count": len(text),
                "error": None,
            }

        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            return {
                "translated_text": text,  # graceful fallback to English
                "language": lang_info["name"],
                "language_code": lang_info["code"],
                "char_count": 0,
                "error": f"API error: {str(e)}",
            }


def translate_batch(prompts: list, languages: list) -> dict:
    """
    Translate a list of prompts into multiple languages.

    Returns:
        {
          "hindi": [{"original": ..., "translated": ..., "error": ...}, ...],
          "urdu":  [...],
          "tamil": [...]
        }

    IMPORTANT: The translated prompts are what actually get sent to the
    endpoint model. This is the core of the multilingual evaluation —
    we test whether the health AI responds correctly when asked in
    the user's native language.
    """
    results = {lang: [] for lang in languages}
    total_chars = 0

    for lang in languages:
        lang_display = LANGUAGE_MAP.get(lang, {}).get("name", lang)
        print(f"\n  Translating {len(prompts)} prompts → {lang_display}...")
        success = 0

        for prompt in prompts:
            result = translate_prompt(prompt, lang)
            results[lang].append({
                "original": prompt,
                "translated": result["translated_text"],
                "language": result["language"],
                "language_code": result["language_code"],
                "error": result["error"],
            })
            if not result["error"]:
                success += 1
            total_chars += result["char_count"]

        print(f"  {lang_display}: {success}/{len(prompts)} translated successfully")

    cost = round(total_chars / 10000 * 20, 1)
    print(f"\n  Total characters used: {total_chars:,} / free tier")
    print(f"  Estimated cost: ₹{cost} (covered by free credits)")
    return results