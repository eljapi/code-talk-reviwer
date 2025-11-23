"""Google Cloud authentication for Vertex AI Live API."""

import logging
import os
from typing import Optional

from google.auth import default
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError
from google.oauth2 import service_account

logger = logging.getLogger(__name__)


class VertexAuthManager:
    """Manages authentication for Google Vertex AI services."""

    def __init__(self, project_id: Optional[str] = None, credentials_path: Optional[str] = None):
        """Initialize authentication manager.
        
        Args:
            project_id: Google Cloud project ID
            credentials_path: Path to service account JSON file
        """
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self._credentials: Optional[Credentials] = None
        
    def get_credentials(self) -> Credentials:
        """Get authenticated credentials for Google Cloud services.
        
        Returns:
            Google Cloud credentials
            
        Raises:
            DefaultCredentialsError: If authentication fails
        """
        if self._credentials is not None:
            return self._credentials
            
        try:
            if self.credentials_path and os.path.exists(self.credentials_path):
                logger.info(f"Using service account credentials from {self.credentials_path}")
                self._credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
            else:
                logger.info("Using default credentials (ADC)")
                self._credentials, _ = default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                
            return self._credentials
            
        except DefaultCredentialsError as e:
            logger.error(f"Failed to authenticate with Google Cloud: {e}")
            raise
            
    def get_project_id(self) -> str:
        """Get the Google Cloud project ID.
        
        Returns:
            Project ID
            
        Raises:
            ValueError: If project ID is not configured
        """
        if not self.project_id:
            # Try to get from credentials
            credentials = self.get_credentials()
            if hasattr(credentials, 'project_id') and credentials.project_id:
                self.project_id = credentials.project_id
            else:
                raise ValueError(
                    "Google Cloud project ID not found. Set GOOGLE_CLOUD_PROJECT "
                    "environment variable or provide project_id parameter."
                )
                
        return self.project_id
        
    def validate_authentication(self) -> bool:
        """Validate that authentication is working.
        
        Returns:
            True if authentication is valid, False otherwise
        """
        try:
            credentials = self.get_credentials()
            project_id = self.get_project_id()
            logger.info(f"Authentication validated for project: {project_id}")
            return True
        except Exception as e:
            logger.error(f"Authentication validation failed: {e}")
            return False