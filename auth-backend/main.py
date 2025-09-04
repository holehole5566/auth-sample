from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta
import httpx
import os
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

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class GoogleAuthRequest(BaseModel):
    code: str

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
    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": request.code,
                "grant_type": "authorization_code",
                "redirect_uri": "http://localhost:5173/auth/google/callback"
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        token_data = token_response.json()
        google_token = token_data.get("access_token")
        
        # Get user info
        user_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {google_token}"}
        )
        
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        user_data = user_response.json()
        
        # Transform Google user data to match our format
        transformed_user = {
            "id": user_data["id"],
            "login": user_data.get("email", "").split("@")[0],
            "name": user_data.get("name"),
            "email": user_data.get("email"),
            "avatar_url": user_data.get("picture")
        }
        
        tokens = create_tokens(transformed_user)
        
        return {
            "user": {
                "id": transformed_user["id"], 
                "username": transformed_user["login"],
                "name": transformed_user.get("name"),
                "email": transformed_user.get("email"),
                "avatar": transformed_user.get("avatar_url")
            },
            **tokens
        }

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