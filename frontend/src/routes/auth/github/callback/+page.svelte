<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { exchangeCodeForTokens } from '$lib/auth';

	onMount(async () => {
		const code = $page.url.searchParams.get('code');
		if (code) {
			try {
				await exchangeCodeForTokens(code);
				goto('/dashboard');
			} catch (error) {
				console.error('Login failed:', error);
				goto('/');
			}
		} else {
			goto('/');
		}
	});
</script>

<div class="flex h-screen w-full items-center justify-center px-4">
	<div class="text-center">
		<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
		<p class="mt-2">Completing login...</p>
	</div>
</div>