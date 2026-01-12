"""
HTTP client with robust timeout and retry handling.
Essential for demo reliability.
"""

import time
import requests
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from common.logging_config import get_logger

logger = get_logger("http-client")


class RequestResult(Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    HTTP_ERROR = "http_error"
    PARSE_ERROR = "parse_error"


@dataclass
class Response:
    """Standardized response wrapper."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    result_type: RequestResult = RequestResult.SUCCESS
    status_code: Optional[int] = None
    elapsed_ms: float = 0


def make_request(
    method: str,
    url: str,
    json_data: Optional[Dict] = None,
    timeout: int = 30,
    retries: int = 3,
    retry_delay: int = 2
) -> Response:
    """
    Make an HTTP request with timeout and retry handling.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Target URL
        json_data: JSON payload for POST requests
        timeout: Request timeout in seconds
        retries: Number of retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        Response object with success status and data/error
    """
    last_error = None
    start_time = time.time()
    
    for attempt in range(retries):
        try:
            if attempt > 0:
                logger.info(f"Retry {attempt}/{retries-1} for {url}")
                time.sleep(retry_delay)
            
            # Make request
            response = requests.request(
                method=method,
                url=url,
                json=json_data,
                timeout=timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            elapsed = (time.time() - start_time) * 1000
            
            # Check HTTP status
            if response.status_code >= 400:
                logger.warning(f"HTTP {response.status_code} from {url}")
                last_error = f"HTTP {response.status_code}"
                continue
            
            # Parse JSON response
            try:
                data = response.json()
                return Response(
                    success=True,
                    data=data,
                    result_type=RequestResult.SUCCESS,
                    status_code=response.status_code,
                    elapsed_ms=elapsed
                )
            except ValueError as e:
                logger.warning(f"JSON parse error from {url}: {e}")
                last_error = f"JSON parse error: {e}"
                continue
                
        except requests.Timeout:
            elapsed = (time.time() - start_time) * 1000
            logger.warning(f"Timeout ({timeout}s) for {url}")
            last_error = f"Timeout after {timeout}s"
            continue
            
        except requests.ConnectionError as e:
            elapsed = (time.time() - start_time) * 1000
            logger.warning(f"Connection error for {url}: {e}")
            last_error = f"Connection failed: {e}"
            continue
            
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"Unexpected error for {url}: {e}")
            last_error = f"Unexpected error: {e}"
            continue
    
    # All retries exhausted
    elapsed = (time.time() - start_time) * 1000
    return Response(
        success=False,
        error=last_error,
        result_type=RequestResult.CONNECTION_ERROR,
        elapsed_ms=elapsed
    )


def check_health(url: str, timeout: int = 5) -> Tuple[bool, Optional[Dict]]:
    """
    Quick health check for a service.
    
    Args:
        url: Base URL of the service
        timeout: Health check timeout
    
    Returns:
        Tuple of (is_healthy, health_data)
    """
    health_url = f"{url.rstrip('/')}/health"
    response = make_request(
        method="GET",
        url=health_url,
        timeout=timeout,
        retries=1,  # Don't retry health checks
        retry_delay=0
    )
    
    return response.success, response.data


def post_with_timeout(
    url: str,
    data: Dict,
    timeout: int = 30,
    retries: int = 3
) -> Response:
    """Convenience function for POST requests."""
    return make_request(
        method="POST",
        url=url,
        json_data=data,
        timeout=timeout,
        retries=retries
    )


def get_with_timeout(
    url: str,
    timeout: int = 10,
    retries: int = 2
) -> Response:
    """Convenience function for GET requests."""
    return make_request(
        method="GET",
        url=url,
        timeout=timeout,
        retries=retries
    )
