"""Ollama client for interacting with local models."""

import json
import time
import threading
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

import httpx
from rich.console import Console

console = Console()


class OllamaClient:
    """Client for interacting with Ollama API with performance optimizations."""
    
    # Shared connection pool for all instances
    _client_pool: Dict[str, httpx.Client] = {}
    _pool_lock = threading.Lock()
    
    # Response cache with LRU eviction
    _cache_size = 100
    _cache_ttl = 300  # 5 minutes
    _response_cache: Dict[str, Tuple[str, float]] = {}
    _cache_lock = threading.Lock()

    def __init__(self, host: str = "http://localhost:11434", enable_cache: bool = True):
        self.host = host.rstrip("/")
        self.enable_cache = enable_cache
        
        # Use shared connection pool
        with OllamaClient._pool_lock:
            if self.host not in OllamaClient._client_pool:
                OllamaClient._client_pool[self.host] = httpx.Client(
                    timeout=300.0,
                    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
                    http2=True
                )
            self.client = OllamaClient._client_pool[self.host]

    def _get_cache_key(self, model: str, prompt: str, temperature: float, 
                      max_tokens: Optional[int] = None, system: Optional[str] = None) -> str:
        """Generate cache key for request parameters."""
        key_parts = [model, prompt, str(temperature)]
        if max_tokens:
            key_parts.append(str(max_tokens))
        if system:
            key_parts.append(system)
        return "|".join(key_parts)
    
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached response if available and not expired."""
        if not self.enable_cache:
            return None
            
        with OllamaClient._cache_lock:
            if cache_key in OllamaClient._response_cache:
                response, timestamp = OllamaClient._response_cache[cache_key]
                if time.time() - timestamp < OllamaClient._cache_ttl:
                    return response
                else:
                    # Remove expired cache entry
                    del OllamaClient._response_cache[cache_key]
        return None
    
    def _cache_response(self, cache_key: str, response: str) -> None:
        """Cache a response with timestamp."""
        if not self.enable_cache:
            return
            
        with OllamaClient._cache_lock:
            # Implement simple LRU by removing oldest entries when cache is full
            if len(OllamaClient._response_cache) >= OllamaClient._cache_size:
                # Remove the oldest entry
                oldest_key = min(OllamaClient._response_cache.keys(), 
                               key=lambda k: OllamaClient._response_cache[k][1])
                del OllamaClient._response_cache[oldest_key]
            
            OllamaClient._response_cache[cache_key] = (response, time.time())
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear the response cache."""
        with cls._cache_lock:
            cls._response_cache.clear()
    
    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        """Get cache statistics."""
        with cls._cache_lock:
            current_time = time.time()
            valid_entries = sum(1 for _, timestamp in cls._response_cache.values()
                              if current_time - timestamp < cls._cache_ttl)
            return {
                "total_entries": len(cls._response_cache),
                "valid_entries": valid_entries,
                "cache_hit_potential": valid_entries / max(1, len(cls._response_cache)),
                "cache_size_limit": cls._cache_size,
                "ttl_seconds": cls._cache_ttl
            }

    def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
        stream: bool = False,
    ) -> str:
        """Generate text using Ollama model with caching and optimization."""
        # Check cache first for non-streaming requests
        if not stream and self.enable_cache:
            cache_key = self._get_cache_key(model, prompt, temperature, max_tokens, system)
            cached_response = self._get_cached_response(cache_key)
            if cached_response is not None:
                return cached_response
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
            },
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
                result = response.json()["response"]
                
                # Cache the response
                if self.enable_cache:
                    cache_key = self._get_cache_key(model, prompt, temperature, max_tokens, system)
                    self._cache_response(cache_key, result)
                
                return result
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.host}. "
                "Make sure Ollama is running and accessible."
            )
        except httpx.TimeoutException:
            raise TimeoutError(
                "Ollama request timed out. The model might be too large or busy."
            )
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}")

    def _generate_stream(self, payload: Dict[str, Any]) -> str:
        """Handle streaming response from Ollama."""
        full_response = ""

        try:
            with self.client.stream(
                "POST", f"{self.host}/api/generate", json=payload
            ) as response:
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
            },
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
            raise TimeoutError(
                "Ollama request timed out. The model might be too large or busy."
            )
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}")

    def _chat_stream(self, payload: Dict[str, Any]) -> str:
        """Handle streaming chat response from Ollama."""
        full_response = ""

        try:
            with self.client.stream(
                "POST", f"{self.host}/api/chat", json=payload
            ) as response:
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
        """Close the HTTP client (connection pool remains shared)."""
        # Don't close shared connection pool - other instances may be using it
        pass
    
    @classmethod
    def close_all_connections(cls) -> None:
        """Close all shared HTTP clients (use when shutting down application)."""
        with cls._pool_lock:
            for client in cls._client_pool.values():
                client.close()
            cls._client_pool.clear()
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get approximate memory usage statistics."""
        import sys
        
        cache_size_bytes = 0
        with OllamaClient._cache_lock:
            for key, (response, _) in OllamaClient._response_cache.items():
                cache_size_bytes += sys.getsizeof(key) + sys.getsizeof(response)
        
        return {
            "cache_entries": len(OllamaClient._response_cache),
            "cache_size_mb": cache_size_bytes / (1024 * 1024),
            "connection_pools": len(OllamaClient._client_pool),
        }
