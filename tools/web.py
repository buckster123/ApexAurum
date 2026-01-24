"""
Web Tools
=========

Simple web utilities for AI tool calling.
Requires: requests (pip install requests)

Tools:
- web_fetch: Fetch content from a URL
- web_search: Search the web (uses DuckDuckGo)
"""

import logging
import re
from typing import Dict, Any, Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# Try to import requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests not installed - web tools will be limited")


def web_fetch(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    max_length: int = 50000
) -> Dict[str, Any]:
    """
    Fetch content from a URL.

    Args:
        url: URL to fetch
        method: HTTP method (GET or POST)
        headers: Optional custom headers
        timeout: Request timeout in seconds
        max_length: Max response length to return

    Returns:
        Dict with status, content, headers, and metadata

    Example:
        >>> web_fetch("https://httpbin.org/get")
        {"success": True, "status_code": 200, "content": "...", ...}
    """
    if not REQUESTS_AVAILABLE:
        return {
            "success": False,
            "error": "requests library not installed. Run: pip install requests"
        }

    try:
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Default headers
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; AIBot/1.0)'
        }
        if headers:
            default_headers.update(headers)

        # Make request
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=default_headers,
            timeout=timeout,
            allow_redirects=True
        )

        # Get content
        content = response.text
        if len(content) > max_length:
            content = content[:max_length] + f"\n\n[Truncated - {len(response.text)} total chars]"

        # Extract title if HTML
        title = None
        if 'text/html' in response.headers.get('Content-Type', ''):
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()

        return {
            "success": True,
            "status_code": response.status_code,
            "url": response.url,
            "title": title,
            "content_type": response.headers.get('Content-Type', 'unknown'),
            "content_length": len(response.text),
            "content": content
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": f"Request timed out after {timeout}s"}
    except requests.exceptions.ConnectionError as e:
        return {"success": False, "error": f"Connection error: {str(e)}"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


def web_search(
    query: str,
    num_results: int = 5
) -> Dict[str, Any]:
    """
    Search the web using DuckDuckGo Instant Answers API.

    Note: This uses DuckDuckGo's free API which provides instant answers
    and related topics, not full search results. For full search, consider
    using a dedicated search API.

    Args:
        query: Search query
        num_results: Max number of results to return

    Returns:
        Dict with search results

    Example:
        >>> web_search("python programming")
        {"success": True, "results": [...], ...}
    """
    if not REQUESTS_AVAILABLE:
        return {
            "success": False,
            "error": "requests library not installed. Run: pip install requests"
        }

    try:
        # DuckDuckGo Instant Answer API
        url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"

        response = requests.get(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; AIBot/1.0)'},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        results = []

        # Abstract (main answer)
        if data.get('Abstract'):
            results.append({
                "type": "answer",
                "title": data.get('Heading', 'Answer'),
                "text": data['Abstract'],
                "url": data.get('AbstractURL', ''),
                "source": data.get('AbstractSource', '')
            })

        # Related topics
        for topic in data.get('RelatedTopics', [])[:num_results]:
            if isinstance(topic, dict):
                if 'Text' in topic:
                    results.append({
                        "type": "related",
                        "title": topic.get('Text', '')[:100],
                        "text": topic.get('Text', ''),
                        "url": topic.get('FirstURL', '')
                    })
                elif 'Topics' in topic:
                    # Nested topics
                    for subtopic in topic['Topics'][:2]:
                        if 'Text' in subtopic:
                            results.append({
                                "type": "related",
                                "title": subtopic.get('Text', '')[:100],
                                "text": subtopic.get('Text', ''),
                                "url": subtopic.get('FirstURL', '')
                            })

        # Definition
        if data.get('Definition'):
            results.append({
                "type": "definition",
                "title": "Definition",
                "text": data['Definition'],
                "url": data.get('DefinitionURL', ''),
                "source": data.get('DefinitionSource', '')
            })

        return {
            "success": True,
            "query": query,
            "results": results[:num_results],
            "result_count": len(results[:num_results]),
            "answer_type": data.get('Type', 'unknown')
        }

    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Search request failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Search error: {str(e)}"}


# =============================================================================
# Tool Schemas
# =============================================================================

WEB_TOOL_SCHEMAS = {
    "web_fetch": {
        "name": "web_fetch",
        "description": """Fetch content from a URL. Returns page content, status code, and metadata.

Use for:
- Reading web pages
- Fetching API responses
- Checking if URLs are accessible

Note: Content is truncated at 50KB by default.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch (http:// or https://)"
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST"],
                    "description": "HTTP method",
                    "default": "GET"
                },
                "headers": {
                    "type": "object",
                    "description": "Optional custom headers"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds",
                    "default": 30
                }
            },
            "required": ["url"]
        }
    },
    "web_search": {
        "name": "web_search",
        "description": """Search the web using DuckDuckGo.

Returns instant answers and related topics. Good for:
- Quick facts and definitions
- Finding relevant topics
- General knowledge queries

Note: Uses DuckDuckGo Instant Answer API (free, no API key needed).
For comprehensive results, use web_fetch on specific sites.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Max results to return",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
}
