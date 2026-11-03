"""
Ollama Client Service for LexiGuard AI
Interacts with the local Ollama instance (qwen3:4b).
Ensures only user-facing responses are returned, stripping the JSON 'thinking' field
and removing any <think>...</think> sections from the final text.
"""

import re
import logging
from typing import Optional, Dict, Any
import httpx

from app.core.config import settings

logger = logging.getLogger("lexiguard.ollama")

THINK_TAG_REGEX = re.compile(r"<think>[\s\S]*?</think>", flags=re.IGNORECASE)


def sanitize_ollama_response(raw_text: str) -> str:
    """
    Strips internal reasoning enclosed in <think>...</think>, any orphaned closing </think>
    tags with preceding reasoning text, and cleans excess whitespace.
    Ensures only user-facing responses are returned.
    """
    if not raw_text:
        return ""
    # 1. Strip complete <think>...</think> blocks
    cleaned = THINK_TAG_REGEX.sub("", raw_text)
    # 2. Strip orphaned closing </think> tag and any preceding reasoning content
    if "</think>" in cleaned.lower():
        cleaned = re.split(r"</think>", cleaned, flags=re.IGNORECASE)[-1]
    # 3. Clean unclosed opening <think> tag if output was truncated mid-thought
    cleaned = re.sub(r"<think>[\s\S]*$", "", cleaned, flags=re.IGNORECASE)
    # 4. Remove leading/trailing formatting tokens if raw chat template leaked
    cleaned = re.sub(r"^(```json\s*|```\s*)", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<\|im_end\|>", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


class OllamaClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        num_predict: Optional[int] = None,
        temperature: Optional[float] = None,
        disable_thinking: Optional[bool] = None
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout_seconds if timeout_seconds is not None else settings.OLLAMA_TIMEOUT_SECONDS
        self.num_predict = num_predict if num_predict is not None else settings.OLLAMA_NUM_PREDICT
        self.temperature = temperature if temperature is not None else settings.OLLAMA_TEMPERATURE
        self.disable_thinking = disable_thinking if disable_thinking is not None else settings.OLLAMA_DISABLE_THINKING

    def build_prompt(self, prompt: str, system_prompt: Optional[str] = None, disable_thinking: bool = True) -> tuple[str, bool, Optional[list]]:
        """
        Builds the request prompt and determines if raw template mode is used.
        For Qwen3 thinking models, when thinking is disabled, pre-filling a resolved <think>
        block via raw ChatML template prevents the model from spending generation tokens
        on internal thinking reasoning, guaranteeing fast, direct answers.
        """
        is_qwen = "qwen" in self.model.lower()
        if is_qwen and disable_thinking:
            # Build ChatML raw template with prefilled finished think block
            parts = []
            if system_prompt:
                parts.append(f"<|im_start|>system\n{system_prompt}<|im_end|>")
            parts.append(f"<|im_start|>user\n{prompt}<|im_end|>")
            parts.append("<|im_start|>assistant\n<think>\nDone.\n</think>\n")
            raw_prompt = "\n".join(parts)
            return raw_prompt, True, ["<|im_end|>", "<|im_start|>"]
        return prompt, False, None

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        think: Optional[bool] = None,
        format: Optional[str] = None
    ) -> str:
        """
        Asynchronously calls Ollama /api/generate and returns only the cleaned response string.
        Passes think=False to disable Ollama thinking when configured, applies concise generation options,
        and ensures neither the JSON 'thinking' field nor <think> blocks are exposed.
        """
        endpoint = f"{self.base_url}/api/generate"

        merged_options: Dict[str, Any] = {
            "num_predict": self.num_predict,
            "temperature": self.temperature,
        }
        if options:
            merged_options.update(options)

        should_think = think if think is not None else (not self.disable_thinking)
        final_prompt, is_raw, stop_tokens = self.build_prompt(
            prompt=prompt,
            system_prompt=system_prompt,
            disable_thinking=(not should_think)
        )

        if stop_tokens and "stop" not in merged_options:
            merged_options["stop"] = stop_tokens

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": final_prompt,
            "stream": False,
            "options": merged_options,
            "think": should_think,
        }
        if format:
            payload["format"] = format

        if is_raw:
            payload["raw"] = True
        elif system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(endpoint, json=payload)
                if res.status_code >= 400:
                    raw_err = getattr(res, "text", "") or ""
                    error_body = str(raw_err).strip()
                    # Truncate unusually large error responses to avoid flooding logs
                    truncated_body = error_body[:500] + ("..." if len(error_body) > 500 else "")
                    logger.error(
                        "Ollama API returned error status %s from %s: %s",
                        res.status_code,
                        endpoint,
                        truncated_body
                    )
                    raise RuntimeError(
                        f"Ollama generation failed with status {res.status_code}: {truncated_body}"
                    )
                data = res.json()
        except httpx.TimeoutException as te:
            logger.error("Ollama request timed out after %s seconds: %s", self.timeout, te)
            raise TimeoutError(f"Ollama inference timed out after {self.timeout}s.") from te
        except RuntimeError:
            raise
        except Exception as e:
            logger.exception("Failed to query Ollama at %s: %s", endpoint, e)
            raise RuntimeError(f"Ollama generation failed: {str(e)}") from e

        # Extract only the 'response' key; completely ignore the 'thinking' key
        raw_response = data.get("response", "")
        clean_text = sanitize_ollama_response(raw_response)
        return clean_text

    async def check_health(self) -> bool:
        """
        Quick probe to check if Ollama is reachable and the model exists.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models = [m.get("name") for m in res.json().get("models", [])]
                    # Check if model name or prefix matches
                    return any(self.model in m for m in models)
                return False
        except Exception:
            return False


# Singleton instance
ollama_client = OllamaClient()
