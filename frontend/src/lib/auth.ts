import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import { goto } from '$app/navigation';

// PKCE helper functions
function generateRandomString(length = 128) {
	const charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
	return Array.from(crypto.getRandomValues(new Uint8Array(length)))
		.map(x => charset[x % charset.length])
		.join('');
}

async function sha256(plain: string) {
	const encoder = new TextEncoder();
	const data = encoder.encode(plain);
	const hash = await crypto.subtle.digest('SHA-256', data);
	return btoa(String.fromCharCode(...new Uint8Array(hash)))
		.replace(/\+/g, '-')
		.replace(/\//g, '_')
		.replace(/=/g, '');
}

interface User {
	id: string;
	username: string;
	name: string;
	email: string | null;
	avatar: string | null;
}

interface AuthState {
	user: User | null;
	accessToken: string | null;
	refreshToken: string | null;
	isLoading: boolean;
}

const initialState: AuthState = {
	user: null,
	accessToken: null,
	refreshToken: null,
	isLoading: true
};

export const auth = writable<AuthState>(initialState);

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function exchangeCodeForTokens(code: string, provider: 'github' | 'google' = 'github') {
	try {
		// Get stored code verifier for PKCE
		const codeVerifier = browser ? sessionStorage.getItem('code_verifier') : null;
		const state = browser ? sessionStorage.getItem('oauth_state') : null;
		
		const response = await fetch(`${API_BASE}/auth/${provider}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ code, code_verifier: codeVerifier, state })
		});

		if (!response.ok) throw new Error('Failed to authenticate');

		const data = await response.json();
		
		// Clean up PKCE data
		if (browser) {
			sessionStorage.removeItem('code_verifier');
			sessionStorage.removeItem('oauth_state');
		}
		
		if (browser) {
			localStorage.setItem('accessToken', data.access_token);
			localStorage.setItem('refreshToken', data.refresh_token);
		}

		auth.update(state => ({
			...state,
			user: data.user,
			accessToken: data.access_token,
			refreshToken: data.refresh_token,
			isLoading: false
		}));

		return data;
	} catch (error) {
		console.error('Auth error:', error);
		throw error;
	}
}

export async function refreshAccessToken() {
	const refreshToken = browser ? localStorage.getItem('refreshToken') : null;
	if (!refreshToken) return false;

	try {
		const response = await fetch(`${API_BASE}/auth/refresh`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ refresh_token: refreshToken })
		});

		if (!response.ok) throw new Error('Failed to refresh token');

		const data = await response.json();
		
		if (browser) {
			localStorage.setItem('accessToken', data.access_token);
			localStorage.setItem('refreshToken', data.refresh_token);
		}

		auth.update(state => ({
			...state,
			accessToken: data.access_token,
			refreshToken: data.refresh_token
		}));

		return true;
	} catch (error) {
		logout();
		return false;
	}
}

export async function getCurrentUser() {
	const accessToken = browser ? localStorage.getItem('accessToken') : null;
	if (!accessToken) {
		auth.update(state => ({ ...state, isLoading: false }));
		return;
	}

	try {
		const response = await fetch(`${API_BASE}/auth/me`, {
			headers: { Authorization: `Bearer ${accessToken}` }
		});

		if (!response.ok) {
			if (response.status === 401) {
				const refreshed = await refreshAccessToken();
				if (refreshed) return getCurrentUser();
			}
			throw new Error('Failed to get user');
		}

		const data = await response.json();
		auth.update(state => ({
			...state,
			user: data.user,
			accessToken,
			refreshToken: browser ? localStorage.getItem('refreshToken') : null,
			isLoading: false
		}));
	} catch (error) {
		logout();
	}
}

export function logout() {
	if (browser) {
		localStorage.removeItem('accessToken');
		localStorage.removeItem('refreshToken');
	}
	
	auth.set(initialState);
	goto('/');
}

// Generate OAuth URL with PKCE
export async function generateOAuthURL(provider: 'github' | 'google') {
	if (!browser) return '';
	
	const codeVerifier = generateRandomString();
	const codeChallenge = await sha256(codeVerifier);
	const state = generateRandomString(32);
	
	// Store for later verification
	sessionStorage.setItem('code_verifier', codeVerifier);
	sessionStorage.setItem('oauth_state', state);
	
	const clientId = provider === 'github' 
		? import.meta.env.VITE_GITHUB_CLIENT_ID
		: import.meta.env.VITE_GOOGLE_CLIENT_ID;
	
	if (provider === 'github') {
		return `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${encodeURIComponent('http://localhost:5173/auth/github/callback')}&state=${state}`;
	} else {
		return `https://accounts.google.com/o/oauth2/v2/auth?` +
			`client_id=${clientId}&` +
			`redirect_uri=${encodeURIComponent('http://localhost:5173/auth/google/callback')}&` +
			`response_type=code&` +
			`scope=openid email profile&` +
			`code_challenge=${codeChallenge}&` +
			`code_challenge_method=S256&` +
			`state=${state}`;
	}
}

export function initAuth() {
	if (browser) {
		getCurrentUser();
	}
}