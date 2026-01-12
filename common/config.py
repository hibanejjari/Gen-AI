"""
Shared configuration management for LLM Council.
Supports YAML config files and environment variable overrides.
"""

import os
import yaml
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class NodeConfig:
    """Configuration for a single council node or chairman."""
    id: str
    name: str
    url: str
    model: str
    priority: int = 1
    enabled: bool = True
    
    @property
    def health_url(self) -> str:
        return f"{self.url}/health"


@dataclass
class TimeoutConfig:
    """Timeout settings in seconds."""
    health_check: int = 5
    opinion: int = 120
    review: int = 90
    synthesis: int = 180
    retry_delay: int = 2
    max_retries: int = 3


@dataclass
class FallbackConfig:
    """Fallback behavior settings."""
    min_council_members: int = 2
    enable_local_fallback: bool = True
    local_model: str = "llama3.2:1b"


@dataclass
class CouncilConfig:
    """Complete council configuration."""
    council_nodes: List[NodeConfig] = field(default_factory=list)
    chairman: Optional[NodeConfig] = None
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
    fallback: FallbackConfig = field(default_factory=FallbackConfig)
    orchestrator_host: str = "0.0.0.0"
    orchestrator_port: int = 8080
    ollama_url: str = "http://localhost:11434"


def load_config(config_path: Optional[str] = None) -> CouncilConfig:
    """
    Load configuration from YAML file with environment variable overrides.
    
    Priority (highest to lowest):
    1. Environment variables
    2. Config file
    3. Default values
    """
    config = CouncilConfig()
    
    # Determine config file path
    if config_path is None:
        config_path = os.getenv("COUNCIL_CONFIG", "config.yaml")
    
    # Load from YAML if exists
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, 'r') as f:
            yaml_config = yaml.safe_load(f)
            config = _parse_yaml_config(yaml_config)
    
    # Override with environment variables
    config = _apply_env_overrides(config)
    
    return config


def _parse_yaml_config(yaml_config: dict) -> CouncilConfig:
    """Parse YAML configuration into CouncilConfig."""
    config = CouncilConfig()
    
    # Parse council nodes
    if 'council_nodes' in yaml_config:
        config.council_nodes = [
            NodeConfig(
                id=node.get('id', f"council-{i}"),
                name=node.get('name', f"Council Member {i}"),
                url=node['url'],
                model=node.get('model', 'llama3.2:1b'),
                priority=node.get('priority', i),
                enabled=node.get('enabled', True)
            )
            for i, node in enumerate(yaml_config['council_nodes'], 1)
        ]
    
    # Parse chairman
    if 'chairman' in yaml_config:
        ch = yaml_config['chairman']
        config.chairman = NodeConfig(
            id=ch.get('id', 'chairman'),
            name=ch.get('name', 'Chairman'),
            url=ch['url'],
            model=ch.get('model', 'llama3.2:1b'),
            priority=0
        )
    
    # Parse timeouts
    if 'timeouts' in yaml_config:
        t = yaml_config['timeouts']
        config.timeouts = TimeoutConfig(
            health_check=t.get('health_check', 5),
            opinion=t.get('opinion', 120),
            review=t.get('review', 90),
            synthesis=t.get('synthesis', 180),
            retry_delay=t.get('retry_delay', 2),
            max_retries=t.get('max_retries', 3)
        )
    
    # Parse fallback
    if 'fallback' in yaml_config:
        f = yaml_config['fallback']
        config.fallback = FallbackConfig(
            min_council_members=f.get('min_council_members', 2),
            enable_local_fallback=f.get('enable_local_fallback', True),
            local_model=f.get('local_model', 'llama3.2:1b')
        )
    
    # Parse orchestrator settings
    if 'orchestrator' in yaml_config:
        o = yaml_config['orchestrator']
        config.orchestrator_host = o.get('host', '0.0.0.0')
        config.orchestrator_port = o.get('port', 8080)
    
    config.ollama_url = yaml_config.get('ollama_url', 'http://localhost:11434')
    
    return config


def _apply_env_overrides(config: CouncilConfig) -> CouncilConfig:
    """Apply environment variable overrides to configuration."""
    
    # Orchestrator settings
    config.orchestrator_host = os.getenv('ORCHESTRATOR_HOST', config.orchestrator_host)
    config.orchestrator_port = int(os.getenv('ORCHESTRATOR_PORT', config.orchestrator_port))
    
    # Ollama URL
    config.ollama_url = os.getenv('OLLAMA_URL', config.ollama_url)
    
    # Timeouts
    config.timeouts.opinion = int(os.getenv('TIMEOUT_OPINION', config.timeouts.opinion))
    config.timeouts.review = int(os.getenv('TIMEOUT_REVIEW', config.timeouts.review))
    config.timeouts.synthesis = int(os.getenv('TIMEOUT_SYNTHESIS', config.timeouts.synthesis))
    
    # Fallback settings
    config.fallback.min_council_members = int(os.getenv(
        'MIN_COUNCIL_MEMBERS', 
        config.fallback.min_council_members
    ))
    
    # Dynamic node configuration from env (for quick overrides)
    # Format: COUNCIL_NODE_1_URL=http://192.168.1.100:5001
    for i in range(1, 10):
        url_env = f'COUNCIL_NODE_{i}_URL'
        if os.getenv(url_env):
            if i <= len(config.council_nodes):
                config.council_nodes[i-1].url = os.getenv(url_env)
            else:
                config.council_nodes.append(NodeConfig(
                    id=f"council-{i}",
                    name=f"Council Member {i}",
                    url=os.getenv(url_env),
                    model=os.getenv(f'COUNCIL_NODE_{i}_MODEL', 'llama3.2:1b'),
                    priority=i
                ))
    
    # Chairman URL override
    if os.getenv('CHAIRMAN_URL'):
        if config.chairman:
            config.chairman.url = os.getenv('CHAIRMAN_URL')
        else:
            config.chairman = NodeConfig(
                id='chairman',
                name='Chairman',
                url=os.getenv('CHAIRMAN_URL'),
                model=os.getenv('CHAIRMAN_MODEL', 'llama3.2:1b')
            )
    
    return config


def generate_default_config() -> str:
    """Generate a default configuration YAML string."""
    return """# LLM Council Configuration
# =========================

orchestrator:
  host: "0.0.0.0"      # Bind to all interfaces for LAN access
  port: 8080

# Council member nodes (minimum 3 required)
council_nodes:
  - id: "council-1"
    name: "Analyst Alpha"
    url: "http://localhost:5001"      # Change to LAN IP for distributed
    model: "llama3.2:1b"
    priority: 1
    enabled: true
    
  - id: "council-2"
    name: "Analyst Beta"  
    url: "http://localhost:5002"
    model: "llama3.2:1b"
    priority: 2
    enabled: true
    
  - id: "council-3"
    name: "Analyst Gamma"
    url: "http://localhost:5003"
    model: "llama3.2:1b"
    priority: 3
    enabled: true

# Chairman (must be separate service)
chairman:
  id: "chairman"
  name: "Council Chairman"
  url: "http://localhost:9000"        # Change to LAN IP for distributed
  model: "llama3.2:1b"

# Timeout configuration (seconds)
timeouts:
  health_check: 5
  opinion: 120      # LLM generation can be slow
  review: 90
  synthesis: 180
  retry_delay: 2
  max_retries: 3

# Fallback settings
fallback:
  min_council_members: 2    # Proceed with 2 if 1 fails
  enable_local_fallback: true
  local_model: "llama3.2:1b"

# Ollama API
ollama_url: "http://localhost:11434"
"""


if __name__ == "__main__":
    # Generate default config file
    print(generate_default_config())
