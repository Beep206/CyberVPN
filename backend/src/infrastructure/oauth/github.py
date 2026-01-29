import httpx
from typing import Dict, Optional
from src.config.settings import settings

class GitHubOAuthProvider:
    """GitHub OAuth authentication provider"""

    def __init__(self):
        self.client_id = settings.github_client_id
        self.client_secret = settings.github_client_secret
        self.authorize_base_url = "https://github.com/login/oauth/authorize"
        self.token_url = "https://github.com/login/oauth/access_token"
        self.user_api_url = "https://api.github.com/user"

    def authorize_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Generate GitHub OAuth authorization URL

        Args:
            redirect_uri: URL to redirect after authentication
            state: Optional CSRF protection state parameter

        Returns:
            GitHub auth URL
        """
        params = f"client_id={self.client_id}&redirect_uri={redirect_uri}&scope=read:user user:email"
        if state:
            params += f"&state={state}"
        return f"{self.authorize_base_url}?{params}"

    async def exchange_code(self, code: str, redirect_uri: str) -> Optional[Dict]:
        """
        Exchange authorization code for access token and retrieve user info

        Args:
            code: Authorization code from GitHub
            redirect_uri: Original redirect URI used in authorization

        Returns:
            User info dict if successful, None otherwise
        """
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            # Get access token
            token_response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri
                },
                headers={"Accept": "application/json"}
            )

            if token_response.status_code != 200:
                return None

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                return None

            # Get user information
            user_response = await client.get(
                self.user_api_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                }
            )

            if user_response.status_code != 200:
                return None

            user_data = user_response.json()

            return {
                "id": user_data.get("id"),
                "username": user_data.get("login"),
                "email": user_data.get("email"),
                "name": user_data.get("name"),
                "avatar_url": user_data.get("avatar_url"),
                "access_token": access_token
            }
