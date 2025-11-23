"""Tool declarations for Gemini Live API.

This module defines tools in the format required by Gemini's function calling API.
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def get_claude_code_tool_declaration() -> Dict[str, Any]:
    """Get the Claude Code tool declaration for Gemini Live API.

    Returns:
        Tool declaration in Gemini format with function_declarations.
    """
    return {
        "function_declarations": [
            {
                "name": "run_coding_task",
                "description": (
                    "Perform a coding task or query on the repository. "
                    "Use this tool to read files, search code, analyze the codebase, "
                    "find implementations, check for bugs, or answer any questions about the code. "
                    "This tool uses an intelligent coding agent (Claude Code) to execute the task. "
                    "ALWAYS use this tool when the user asks about code, files, or repository structure. "
                    "The tool can access multiple projects in subdirectories - you can specify paths like "
                    "'project-name/src/file.py' to access specific projects."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_description": {
                            "type": "string",
                            "description": (
                                "A clear description of what coding task to perform. "
                                "Examples: "
                                "'List all projects in the base directory', "
                                "'Find all usages of the AudioManager class in project-name', "
                                "'Read the project-name/main.py file and explain what it does', "
                                "'Search for TODO comments in project-name', "
                                "'Check if there are any security vulnerabilities in the authentication code', "
                                "'Compare the architecture between project-a and project-b'"
                            )
                        }
                    },
                    "required": ["task_description"]
                }
            }
        ]
    }


def get_all_tool_declarations() -> List[Dict[str, Any]]:
    """Get all tool declarations for Gemini Live API.

    Returns:
        List of tool declarations in Gemini format.
    """
    return [
        get_claude_code_tool_declaration()
    ]
