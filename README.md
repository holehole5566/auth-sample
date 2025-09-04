# OAuth Authentication App

A minimal authentication app with Svelte frontend and FastAPI backend supporting GitHub and Google OAuth.

## Setup

### 1. OAuth Apps Setup

#### GitHub OAuth App
1. Go to GitHub Settings > Developer settings > OAuth Apps
2. Create a new OAuth App with:
   - Homepage URL: `http://localhost:5173`
   - Authorization callback URL: `http://localhost:5173/auth/github/callback`
3. Copy Client ID and Client Secret

#### Google OAuth App
1. Go to Google Cloud Console > APIs & Services > Credentials
2. Create OAuth 2.0 Client ID with:
   - Application type: Web application
   - Authorized redirect URI: `http://localhost:5173/auth/google/callback`
3. Copy Client ID and Client Secret

### 2. Backend Setup
```bash
cd auth-backend
uv sync

# Update .env file with your OAuth credentials
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
JWT_SECRET=your_jwt_secret_key
FRONTEND_URL=http://localhost:5173

# Run backend
uv run main.py
```

### 3. Frontend Setup
```bash
cd frontend
npm install

# Update .env file with your OAuth Client IDs
VITE_GITHUB_CLIENT_ID=your_github_client_id
VITE_GOOGLE_CLIENT_ID=your_google_client_id
VITE_API_BASE_URL=http://localhost:8000

# Run frontend
npm run dev
```

## Features

- GitHub and Google OAuth login with callback handling
- JWT access tokens (1 hour expiry)
- Refresh tokens (7 days expiry)
- Protected dashboard with user info
- Automatic token refresh
- User profile data from OAuth providers
- Logout functionality
- Minimal shadcn-ui styling

## API Endpoints

- `POST /auth/github` - Exchange GitHub code for tokens
- `POST /auth/google` - Exchange Google code for tokens
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user info