from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta
import httpx
import os
import hashlib
import base64
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JWT_SECRET = os.getenv("JWT_SECRET")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

def create_tokens(user_data: dict):
    access_payload = {
        "sub": str(user_data["id"]),
        "username": user_data["login"],
        "name": user_data.get("name") or user_data["login"],
        "email": user_data.get("email"),
        "avatar": user_data.get("avatar_url"),
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    refresh_payload = {
        "sub": str(user_data["id"]),
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    
    access_token = jwt.encode(access_payload, JWT_SECRET, algorithm="HS256")
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm="HS256")
    
    return {"access_token": access_token, "refresh_token": refresh_token}

class GitHubAuthRequest(BaseModel):
    code: str
    state: str = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class GoogleAuthRequest(BaseModel):
    code: str
    code_verifier: str = None
    state: str = None

def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """Verify PKCE code challenge"""
    if not code_verifier or not code_challenge:
        return True  # Skip verification if not provided
    
    # Generate challenge from verifier
    digest = hashlib.sha256(code_verifier.encode()).digest()
    generated_challenge = base64.urlsafe_b64encode(digest).decode().rstrip('=')
    
    return generated_challenge == code_challenge

async def verify_google_id_token(id_token: str, http_client, access_token: str = None):
    """Verify Google ID token with proper validation"""
    try:
        # Get Google's public keys
        jwks_response = await http_client.get("https://www.googleapis.com/oauth2/v3/certs")
        if jwks_response.status_code != 200:
            raise HTTPException(500, "Failed to get Google keys")
        
        jwks = jwks_response.json()
        
        # Verify token with proper at_hash validation
        user_data = jwt.decode(
            id_token,
            jwks,
            algorithms=["RS256"],
            audience=GOOGLE_CLIENT_ID,
            issuer="https://accounts.google.com",
            access_token=access_token  # Provide access token for at_hash validation
        )
        
        return user_data
        
    except JWTError as e:
        raise HTTPException(400, f"Invalid ID token: {str(e)}")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/auth/github")
async def github_auth(request: GitHubAuthRequest):
    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": request.code,
            },
            headers={"Accept": "application/json"}
        )
        
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        token_data = token_response.json()
        github_token = token_data.get("access_token")
        
        # Get user info
        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {github_token}"}
        )
        
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        user_data = user_response.json()
        
        # Get user email if not public
        if not user_data.get("email"):
            email_response = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {github_token}"}
            )
            if email_response.status_code == 200:
                emails = email_response.json()
                primary_email = next((e["email"] for e in emails if e["primary"]), None)
                if primary_email:
                    user_data["email"] = primary_email
        tokens = create_tokens(user_data)
        
        return {
            "user": {
                "id": user_data["id"], 
                "username": user_data["login"],
                "name": user_data.get("name") or user_data["login"],
                "email": user_data.get("email"),
                "avatar": user_data.get("avatar_url")
            },
            **tokens
        }

@app.post("/auth/refresh")
async def refresh_token(request: RefreshTokenRequest):
    try:
        payload = jwt.decode(request.refresh_token, JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        user_data = {
            "id": payload["sub"], 
            "login": payload.get("username", ""),
            "name": payload.get("name", ""),
            "email": payload.get("email"),
            "avatar_url": payload.get("avatar")
        }
        return create_tokens(user_data)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@app.post("/auth/google")
async def google_auth(request: GoogleAuthRequest):
    try:
        print(f"Google auth request: code={request.code[:10]}..., verifier={request.code_verifier[:10] if request.code_verifier else None}...")
        async with httpx.AsyncClient() as client:
            # Prepare token exchange data
            token_data = {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": request.code,
                "grant_type": "authorization_code",
                "redirect_uri": "http://localhost:5173/auth/google/callback"
            }
            
            # Add PKCE verifier if provided
            if request.code_verifier:
                token_data["code_verifier"] = request.code_verifier
            
            # Exchange code for tokens
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=token_data
            )
        
            if token_response.status_code != 200:
                print(f"Google token response error: {token_response.status_code} - {token_response.text}")
                raise HTTPException(status_code=400, detail="Failed to get access token")
            
            token_data = token_response.json()
            print(f"Token response: {token_data}")
            id_token = token_data.get("id_token")
            
            if not id_token:
                raise HTTPException(status_code=400, detail="No ID token received")
            
            # Verify ID token
            try:
                google_access_token = token_data.get("access_token")
                user_data = await verify_google_id_token(id_token, client, google_access_token)
                print(f"Verified user data: {user_data}")
                
            except Exception as e:
                print(f"JWT verification error: {e}")
                raise HTTPException(status_code=400, detail=f"Failed to verify ID token: {str(e)}")
            
            # Transform to expected format
            user_data = {
                "id": user_data["sub"],
                "login": user_data.get("email", "").split("@")[0],
                "name": user_data.get("name"),
                "email": user_data.get("email"),
                "avatar_url": user_data.get("picture")
            }
            
            tokens = create_tokens(user_data)
            
            return {
                "user": {
                    "id": user_data["id"], 
                    "username": user_data["login"],
                    "name": user_data.get("name"),
                    "email": user_data.get("email"),
                    "avatar": user_data.get("avatar_url")
                },
                **tokens
            }
    except Exception as e:
        print(f"Google auth error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/auth/me")
async def get_me(current_user = Depends(get_current_user)):
    return {
        "user": {
            "id": current_user["sub"],
            "username": current_user["username"],
            "name": current_user.get("name", current_user["username"]),
            "email": current_user.get("email"),
            "avatar": current_user.get("avatar")
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)