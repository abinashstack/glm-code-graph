"""Authentication module."""
import logging
from typing import Optional, Callable
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AuthMiddleware:
    """Middleware for authentication."""
    
    def __init__(self, auth_service: AuthController):
        self.auth_service = auth_service
    
    def require_auth(self, handler: Callable) -> Callable:
        """Decorator to require authentication."""
        @wraps(handler)
        def wrapper(*args, **kwargs):
            # Extract token from request
            token = kwargs.get("token")
            if not token:
                return {"error": "No token provided", "status": 401}
            
            # Validate token
            if not self.auth_service.validate_token(token):
                return {"error": "Invalid token", "status": 401}
            
            # Token is valid, proceed
            return handler(*args, **kwargs)
        return wrapper

class TokenManager:
    """Token management service."""
    
    def __init__(self, expiration_minutes: int = 30):
        self.expiration = timedelta(minutes=expiration_minutes)
        self._token_store = {}
    
    def create_token(self, user_id: int, username: str) -> str:
        """Create a new authentication token."""
        import jwt
        from config import SECRET_KEY
        
        payload = {
            "user_id": user_id,
            "username": username,
            "exp": datetime.utcnow() + self.expiration
        }
        
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        self._token_store[token] = payload
        return token
    
    def validate_token(self, token: str) -> bool:
        """Validate a token."""
        if token not in self._token_store:
            return False
        
        payload = self._token_store[token]
        if payload["exp"] < datetime.utcnow():
            return False
        
        return True
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        if token in self._token_store:
            del self._token_store[token]
            return True
        return False

def get_current_user(request: dict) -> Optional[dict]:
    """Extract current user from request context."""
    token = request.get("headers", {}).get("Authorization")
    if not token:
        return None
    
    return authenticate(token)
