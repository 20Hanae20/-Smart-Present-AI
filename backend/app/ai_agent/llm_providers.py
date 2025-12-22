"""
LLM Provider abstractions for multi-provider support
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Iterator, Optional
import requests

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, messages: List[Dict[str, str]], stream: bool = False) -> Any:
        """Generate response from messages."""
        pass


class GroqProvider(LLMProvider):
    """Groq API provider (ultra-fast inference)."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.1-8b-instant"

    def generate(self, messages: List[Dict[str, str]], stream: bool = False) -> Any:
        """Generate response using Groq API."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "stream": stream,
            "max_tokens": 1024
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            self.api_url, 
            headers=headers, 
            json=payload, 
            stream=stream, 
            timeout=30
        )
        
        response.raise_for_status()
        
        if stream:
            return self._stream_generator(response)
        else:
            return response.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _stream_generator(response) -> Iterator[str]:
        """Generate streaming tokens from Groq response."""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: ") and "[DONE]" not in line_str:
                    try:
                        chunk = json.loads(line_str[6:])
                        content = chunk["choices"][0]["delta"].get("content")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-3.5-turbo"

    def generate(self, messages: List[Dict[str, str]], stream: bool = False) -> Any:
        """Generate response using OpenAI API."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "stream": stream,
            "max_tokens": 1024
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            self.api_url, 
            headers=headers, 
            json=payload, 
            stream=stream, 
            timeout=30
        )
        
        response.raise_for_status()
        
        if stream:
            return self._stream_generator(response)
        else:
            return response.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _stream_generator(response) -> Iterator[str]:
        """Generate streaming tokens from OpenAI response."""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: ") and "[DONE]" not in line_str:
                    try:
                        chunk = json.loads(line_str[6:])
                        content = chunk["choices"][0]["delta"].get("content")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue


class GeminiProvider(LLMProvider):
    """Google Gemini API provider (SmartPresence default)."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "gemini-1.5-flash"
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def generate(self, messages: List[Dict[str, str]], stream: bool = False) -> Any:
        """Generate response using Gemini API."""
        # Convert OpenAI-style messages to Gemini format
        gemini_contents = self._convert_messages_to_gemini(messages)
        
        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1024,
            }
        }
        
        url = f"{self.api_url}?key={self.api_key}"
        
        if stream:
            url = url.replace(":generateContent", ":streamGenerateContent")
            response = requests.post(url, json=payload, stream=True, timeout=30)
            response.raise_for_status()
            return self._stream_generator(response)
        else:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if "candidates" in data and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    return "".join(part.get("text", "") for part in parts)
            
            return ""

    @staticmethod
    def _convert_messages_to_gemini(messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Convert OpenAI-style messages to Gemini format."""
        gemini_contents = []
        system_instruction = None
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                system_instruction = content
                continue
            
            # Map roles: user -> user, assistant -> model
            gemini_role = "user" if role == "user" else "model"
            
            # Prepend system instruction to first user message
            if gemini_role == "user" and system_instruction and not gemini_contents:
                content = f"{system_instruction}\n\n{content}"
                system_instruction = None
            
            gemini_contents.append({
                "role": gemini_role,
                "parts": [{"text": content}]
            })
        
        return gemini_contents

    @staticmethod
    def _stream_generator(response) -> Iterator[str]:
        """Generate streaming tokens from Gemini response."""
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line.decode('utf-8'))
                    if "candidates" in chunk and len(chunk["candidates"]) > 0:
                        candidate = chunk["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            for part in candidate["content"]["parts"]:
                                if "text" in part:
                                    yield part["text"]
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
