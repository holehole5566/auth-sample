# OAuth 2.0 + OIDC + PKCE Flow Documentation

## Complete Authentication Flow

### 1. Frontend Initiates Login
```javascript
// User clicks "Login with Google"
async function loginWithGoogle() {
    const url = await generateOAuthURL('google');
    window.location.href = url;
}
```

### 2. Generate OAuth URL with PKCE
```javascript
// Generate PKCE parameters
const codeVerifier = generateRandomString(128);
const codeChallenge = await sha256(codeVerifier);
const state = generateRandomString(32);

// Store in session for later verification
sessionStorage.setItem('code_verifier', codeVerifier);
sessionStorage.setItem('oauth_state', state);

// Build OAuth URL
const oauthUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
    `client_id=${clientId}&` +
    `redirect_uri=${encodeURIComponent('http://localhost:5173/auth/google/callback')}&` +
    `response_type=code&` +
    `scope=openid email profile&` +
    `code_challenge=${codeChallenge}&` +
    `code_challenge_method=S256&` +
    `state=${state}`;
```

### 3. User Authorizes on Google
```
Browser redirects to Google OAuth server
User logs in and grants permissions
Google redirects back to: http://localhost:5173/auth/google/callback?code=xxx&state=yyy
```

### 4. Frontend Callback Handler
```javascript
// Extract code and state from URL
const urlParams = new URLSearchParams(window.location.search);
const code = urlParams.get('code');
const state = urlParams.get('state');

// Verify state matches (CSRF protection)
const storedState = sessionStorage.getItem('oauth_state');
if (state !== storedState) {
    throw new Error('Invalid state parameter - possible CSRF attack');
}

// Exchange code for tokens
await exchangeCodeForTokens(code, 'google');
```

### 5. Token Exchange with Backend
```javascript
// Get stored PKCE verifier
const codeVerifier = sessionStorage.getItem('code_verifier');

// Send to backend
const response = await fetch('http://localhost:8000/auth/google', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
        code, 
        code_verifier: codeVerifier, 
        state 
    })
});
```

### 6. Backend Token Exchange
```python
# Exchange authorization code for tokens
token_response = await client.post(
    "https://oauth2.googleapis.com/token",
    data={
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": request.code,
        "grant_type": "authorization_code",
        "redirect_uri": "http://localhost:5173/auth/google/callback",
        "code_verifier": request.code_verifier  # PKCE verification
    }
)

# Response contains:
# - access_token: For API calls
# - id_token: JWT with user identity (OIDC)
# - refresh_token: For token renewal
```

### 7. ID Token Verification
```python
# Get Google's public keys
jwks_response = await client.get("https://www.googleapis.com/oauth2/v3/certs")
jwks = jwks_response.json()

# Extract access token for at_hash validation
google_access_token = token_data.get("access_token")

# Verify ID token with full security validation
user_data = jwt.decode(
    id_token,
    jwks,
    algorithms=["RS256"],
    audience=GOOGLE_CLIENT_ID,
    issuer="https://accounts.google.com",
    access_token=google_access_token  # Enables at_hash validation
)

# Verified user data contains:
# - sub: Unique user ID
# - email: User's email
# - name: Display name
# - picture: Avatar URL
```

### 8. Create Application Tokens
```python
# Create your own JWT tokens
access_token = jwt.encode({
    "sub": user_data["sub"],
    "username": user_data["email"].split("@")[0],
    "name": user_data["name"],
    "email": user_data["email"],
    "avatar": user_data["picture"],
    "exp": datetime.utcnow() + timedelta(hours=1)
}, JWT_SECRET, algorithm="HS256")

refresh_token = jwt.encode({
    "sub": user_data["sub"],
    "type": "refresh",
    "exp": datetime.utcnow() + timedelta(days=7)
}, JWT_SECRET, algorithm="HS256")
```

### 9. Frontend Stores Tokens
```javascript
// Store tokens securely
localStorage.setItem('accessToken', data.access_token);
localStorage.setItem('refreshToken', data.refresh_token);

// Update auth state
auth.update(state => ({
    ...state,
    user: data.user,
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    isLoading: false
}));

// Redirect to dashboard
goto('/dashboard');
```

## Security Components

### PKCE (Proof Key for Code Exchange)
- **Purpose**: Prevents authorization code interception
- **Flow**: Generate random verifier → Create challenge → Verify on token exchange
- **Protection**: Even if code is intercepted, attacker can't exchange without verifier

### State Parameter
- **Purpose**: CSRF protection
- **Flow**: Generate random state → Include in OAuth URL → Verify on callback
- **Protection**: Prevents malicious sites from initiating OAuth flow

### ID Token Verification
- **Signature**: Verify token signed by Google using their public keys
- **Audience**: Ensure token is for your application (client_id)
- **Issuer**: Confirm token came from Google
- **Expiration**: Check token hasn't expired
- **at_hash**: Verify ID token and access token were issued together (prevents token substitution attacks)

## Key Differences from Basic OAuth

### OAuth 2.0 Only
```
1. Redirect to provider
2. Get authorization code
3. Exchange code for access_token
4. Use access_token to call /userinfo API
```

### OAuth 2.0 + OIDC + PKCE (Current)
```
1. Generate PKCE challenge + state
2. Redirect to provider with challenge
3. Get authorization code
4. Exchange code + verifier for access_token + id_token
5. Verify id_token signature and claims
6. Extract user info from verified id_token (no API call needed)
```

## Benefits of Current Approach

1. **Security**: PKCE + state parameter + JWT verification
2. **Performance**: No extra /userinfo API call
3. **Reliability**: User data comes from cryptographically verified token
4. **Standards**: Follows OIDC best practices
5. **Future-proof**: Ready for production security requirements

## Production Considerations

- **HTTPS**: All URLs must use HTTPS in production
- **Secure Storage**: Use httpOnly cookies instead of localStorage
- **Key Caching**: Cache Google's public keys with TTL
- **Error Handling**: Proper error messages without exposing internals
- **Rate Limiting**: Prevent abuse of auth endpoints
- **Logging**: Audit trail for security events