<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import LoginForm from "$lib/components/login-form.svelte";
	import { auth, initAuth } from '$lib/auth';



	onMount(() => {
		initAuth();
	});

	$: if ($auth.user) {
		goto('/dashboard');
	}
</script>

{#if $auth.isLoading}
	<div class="flex h-screen w-full items-center justify-center px-4">
		<div class="text-center">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
			<p class="mt-2">Authenticating...</p>
		</div>
	</div>
{:else if !$auth.user}
	<div class="flex h-screen w-full items-center justify-center px-4">
		<LoginForm />
	</div>
{/if}
