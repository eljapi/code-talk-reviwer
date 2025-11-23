"""Repository manager for Claude Code SDK operations.

This module handles repository path validation and configuration for the Claude Code SDK.
It supports multi-project access through additionalDirectories.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from claude_agent_sdk import ClaudeAgentOptions

logger = logging.getLogger(__name__)

# Directories to exclude when discovering projects
DEFAULT_EXCLUDE_PATTERNS = {
    '.git', '.venv', 'venv', 'node_modules', '.env', '.env.example',
    '__pycache__', '.pytest_cache', 'dist', 'build', '.egg-info',
    '.idea', '.vscode', '.DS_Store', 'Thumbs.db'
}


@dataclass
class RepositoryConfig:
    """Configuration for a code repository."""
    path: str
    allowed_tools: List[str]
    permission_mode: str = "acceptEdits"  # 'plan', 'ask', 'acceptEdits', 'auto'
    discover_projects: bool = True  # Auto-discover subdirectories as additional projects
    exclude_patterns: List[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDE_PATTERNS))

    def validate(self) -> None:
        """Validate the configuration."""
        if not os.path.exists(self.path):
            raise ValueError(f"Repository path does not exist: {self.path}")
        if not os.path.isdir(self.path):
            raise ValueError(f"Repository path is not a directory: {self.path}")


class RepositoryManager:
    """Manages access to code repositories with multi-directory support."""

    def __init__(self, default_path: Optional[str] = None):
        """Initialize repository manager.

        Args:
            default_path: Default repository path. If None, uses current working directory.
        """
        self.default_path = default_path or os.getcwd()

        # Normalize and validate the path
        self.default_path = str(Path(self.default_path).resolve())

        logger.info(f"RepositoryManager initialized with path: {self.default_path}")

    def discover_projects(self, base_path: str, exclude_patterns: Optional[List[str]] = None) -> List[str]:
        """Discover subdirectories as projects.

        Args:
            base_path: Base directory to search in
            exclude_patterns: Patterns to exclude (directory names)

        Returns:
            List of absolute paths to project directories
        """
        if exclude_patterns is None:
            exclude_patterns = DEFAULT_EXCLUDE_PATTERNS

        projects = []

        try:
            base_path_obj = Path(base_path)

            # Iterate through first-level subdirectories
            for item in base_path_obj.iterdir():
                if item.is_dir():
                    # Skip excluded patterns
                    if item.name in exclude_patterns or item.name.startswith('.'):
                        continue

                    projects.append(str(item.resolve()))
                    logger.debug(f"Discovered project: {item.name}")

            logger.info(f"Discovered {len(projects)} project(s) in {base_path}")

        except Exception as e:
            logger.warning(f"Error discovering projects in {base_path}: {e}")

        return projects

    def get_options(self, config: Optional[RepositoryConfig] = None) -> ClaudeAgentOptions:
        """Get Claude Agent options for a repository with multi-directory support.

        Args:
            config: Repository configuration. If None, uses defaults.

        Returns:
            Configured ClaudeAgentOptions with cwd and additionalDirectories
        """
        # Read from environment variables for overrides
        permission_mode = os.getenv("CLAUDE_CODE_PERMISSION_MODE", None)

        # Use config values if provided, otherwise defaults
        path = config.path if config else self.default_path
        allowed_tools = config.allowed_tools if config else ["Read", "Grep", "Glob", "Bash"]
        permission_mode = permission_mode or (config.permission_mode if config else "plan")
        discover_projects = config.discover_projects if config else True
        exclude_patterns = config.exclude_patterns if config else DEFAULT_EXCLUDE_PATTERNS

        # Ensure path is absolute
        abs_path = str(Path(path).resolve())

        # Validate path exists
        if not os.path.exists(abs_path):
            logger.error(f"Repository path does not exist: {abs_path}")
            raise ValueError(f"Repository path does not exist: {abs_path}")

        if not os.path.isdir(abs_path):
            logger.error(f"Repository path is not a directory: {abs_path}")
            raise ValueError(f"Repository path is not a directory: {abs_path}")

        # Discover additional directories if enabled
        additional_dirs = []
        if discover_projects:
            additional_dirs = self.discover_projects(abs_path, exclude_patterns)

        logger.info(f"ClaudeAgentOptions: cwd={abs_path}")
        logger.info(f"Permission mode: {permission_mode}")
        logger.info(f"Allowed tools: {allowed_tools}")
        if additional_dirs:
            logger.info(f"Additional directories: {len(additional_dirs)} project(s)")
            for dir_path in additional_dirs:
                logger.debug(f"  - {dir_path}")

        return ClaudeAgentOptions(
            cwd=abs_path,
            model="claude-haiku-4-5-20251001",
            allowed_tools=allowed_tools,
            permission_mode=permission_mode,
            max_turns=10  # Limit turns for safety
        )
