import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import { goto } from '$app/navigation';

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
		const response = await fetch(`${API_BASE}/auth/${provider}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ code })
		});

		if (!response.ok) throw new Error('Failed to authenticate');

		const data = await response.json();
		
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

export function initAuth() {
	if (browser) {
		getCurrentUser();
	}
}