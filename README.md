# GitHub OAuth Authentication App

A minimal authentication app with Svelte frontend and FastAPI backend.

## Setup

### 1. GitHub OAuth App
1. Go to GitHub Settings > Developer settings > OAuth Apps
2. Create a new OAuth App with:
   - Homepage URL: `http://localhost:5173`
   - Authorization callback URL: `http://localhost:5173/auth/github/callback`
3. Copy Client ID and Client Secret

### 2. Backend Setup
```bash
cd auth-backend
pip install -r requirements.txt

# Update .env file with your GitHub credentials
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
JWT_SECRET=your_jwt_secret_key
FRONTEND_URL=http://localhost:5173

# Run backend
python main.py
```

### 3. Frontend Setup
```bash
cd frontend
npm install

# Update .env file with your GitHub Client ID
VITE_GITHUB_CLIENT_ID=your_github_client_id
VITE_API_BASE_URL=http://localhost:8000

# Run frontend
npm run dev
```

## Features

- GitHub OAuth login with callback handling
- JWT access tokens (1 hour expiry)
- Refresh tokens (7 days expiry)
- Protected dashboard with user info
- Automatic token refresh
- User profile data from GitHub API
- Logout functionality
- Minimal shadcn-ui styling

## API Endpoints

- `POST /auth/github` - Exchange GitHub code for tokens
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user info