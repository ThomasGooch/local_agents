"""Ollama client for interacting with local models."""

import json
import httpx
from typing import Dict, Any, Optional, Iterator
from rich.console import Console

console = Console()


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host.rstrip("/")
        self.client = httpx.Client(timeout=300.0)  # 5 minute timeout
    
    def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
        stream: bool = False,
    ) -> str:
        """Generate text using Ollama model."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
            
        if system:
            payload["system"] = system
        
        try:
            if stream:
                return self._generate_stream(payload)
            else:
                response = self.client.post(f"{self.host}/api/generate", json=payload)
                response.raise_for_status()
                return response.json()["response"]
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.host}. "
                "Make sure Ollama is running and accessible."
            )
        except httpx.TimeoutException:
            raise TimeoutError("Ollama request timed out. The model might be too large or busy.")
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}")
    
    def _generate_stream(self, payload: Dict[str, Any]) -> str:
        """Handle streaming response from Ollama."""
        full_response = ""
        
        try:
            with self.client.stream("POST", f"{self.host}/api/generate", json=payload) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                content = chunk["response"]
                                console.print(content, end="")
                                full_response += content
                                
                            if chunk.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            raise RuntimeError(f"Streaming request failed: {e}")
        
        console.print()  # New line after streaming
        return full_response
    
    def chat(
        self,
        model: str,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> str:
        """Chat with Ollama model using messages format."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        try:
            if stream:
                return self._chat_stream(payload)
            else:
                response = self.client.post(f"{self.host}/api/chat", json=payload)
                response.raise_for_status()
                return response.json()["message"]["content"]
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.host}. "
                "Make sure Ollama is running and accessible."
            )
        except httpx.TimeoutException:
            raise TimeoutError("Ollama request timed out. The model might be too large or busy.")
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}")
    
    def _chat_stream(self, payload: Dict[str, Any]) -> str:
        """Handle streaming chat response from Ollama."""
        full_response = ""
        
        try:
            with self.client.stream("POST", f"{self.host}/api/chat", json=payload) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "message" in chunk and "content" in chunk["message"]:
                                content = chunk["message"]["content"]
                                console.print(content, end="")
                                full_response += content
                                
                            if chunk.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            raise RuntimeError(f"Streaming chat request failed: {e}")
        
        console.print()  # New line after streaming
        return full_response
    
    def list_models(self) -> list[str]:
        """List available models."""
        try:
            response = self.client.get(f"{self.host}/api/tags")
            response.raise_for_status()
            models_data = response.json()
            return [model["name"] for model in models_data.get("models", [])]
        except Exception as e:
            console.print(f"[red]Warning: Could not list models: {e}[/red]")
            return []
    
    def is_model_available(self, model: str) -> bool:
        """Check if a model is available."""
        available_models = self.list_models()
        return model in available_models
    
    def pull_model(self, model: str) -> bool:
        """Pull a model if not available."""
        if self.is_model_available(model):
            return True
        
        console.print(f"[yellow]Pulling model {model}...[/yellow]")
        try:
            response = self.client.post(f"{self.host}/api/pull", json={"name": model})
            response.raise_for_status()
            console.print(f"[green]Successfully pulled model {model}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Failed to pull model {model}: {e}[/red]")
            return False
    
    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()