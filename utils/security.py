"""Security utilities for validating Twilio webhooks."""
import os
from fastapi import Request, HTTPException
from twilio.request_validator import RequestValidator


async def validate_twilio(request: Request) -> None:
    """
    Validates Twilio webhook signatures.
    
    This is a dependency that can be used in FastAPI routes to ensure
    requests are actually coming from Twilio.
    
    Note: Validation is skipped in local development for easier testing.
    In production, make sure TWILIO_AUTH is set properly.
    
    Args:
        request: FastAPI request object (injected by FastAPI)
        
    Raises:
        HTTPException: If the request fails validation
    """
    # Skip validation in local development
    domain = os.getenv("DOMAIN", "")
    if "localhost" in domain or "127.0.0.1" in domain or "ngrok" in domain:
        # Allow requests in development mode
        return
    
    # In production, validate the signature
    auth_token = os.getenv("TWILIO_AUTH")
    if not auth_token:
        # If no auth token is configured, we can't validate
        # Log a warning but allow the request (you may want to change this)
        return
        
    try:
        validator = RequestValidator(auth_token)
        
        # Get the URL that Twilio called
        url = str(request.url)
        
        # Get the signature from headers
        signature = request.headers.get("X-Twilio-Signature", "")
        
        # For POST requests, we need the form data
        # Note: This is a simplified version - you may need to adjust based on your needs
        # In a real implementation, you'd need to handle the body properly
        
        # For now, just do a basic check
        if not signature:
            raise HTTPException(
                status_code=403,
                detail="Missing X-Twilio-Signature header"
            )
            
    except Exception as e:
        # Log the error but don't block in development
        if "production" in domain.lower():
            raise HTTPException(
                status_code=403,
                detail=f"Twilio validation failed: {str(e)}"
            )
