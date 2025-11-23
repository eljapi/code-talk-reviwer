"""Repository manager for Claude Code SDK operations.

This module handles repository path validation and configuration for the Claude Code SDK.
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from claude_agent_sdk import ClaudeAgentOptions

@dataclass
class RepositoryConfig:
    """Configuration for a code repository."""
    path: str
    allowed_tools: List[str]
    permission_mode: str = "acceptEdits"  # 'plan', 'ask', 'acceptEdits', 'auto'
    
    def validate(self) -> None:
        """Validate the configuration."""
        if not os.path.exists(self.path):
            raise ValueError(f"Repository path does not exist: {self.path}")
        if not os.path.isdir(self.path):
            raise ValueError(f"Repository path is not a directory: {self.path}")


class RepositoryManager:
    """Manages access to code repositories."""
    
    def __init__(self, default_path: Optional[str] = None):
        """Initialize repository manager.
        
        Args:
            default_path: Default repository path. If None, uses current working directory.
        """
        self.default_path = default_path or os.getcwd()
        
    def get_options(self, config: Optional[RepositoryConfig] = None) -> ClaudeAgentOptions:
        """Get Claude Agent options for a repository.
        
        Args:
            config: Repository configuration. If None, uses defaults.
            
        Returns:
            Configured ClaudeAgentOptions
        """
        path = config.path if config else self.default_path
        allowed_tools = config.allowed_tools if config else ["Read", "Grep", "Glob", "Bash"]
        permission_mode = config.permission_mode if config else "acceptEdits"
        
        # Ensure path is absolute
        abs_path = str(Path(path).resolve())
        
        return ClaudeAgentOptions(
            cwd=abs_path,
            model="claude-sonnet-4-5-20250929",
            allowed_tools=allowed_tools,
            permission_mode=permission_mode,
            max_turns=10  # Limit turns for safety
        )
