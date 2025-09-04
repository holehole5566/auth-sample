<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import data from "./data.js";
	import * as Sidebar from "$lib/components/ui/sidebar/index.js";
	import AppSidebar from "$lib/components/app-sidebar.svelte";
	import SiteHeader from "$lib/components/site-header.svelte";
	import SectionCards from "$lib/components/section-cards.svelte";
	import ChartAreaInteractive from "$lib/components/chart-area-interactive.svelte";
	import DataTable from "$lib/components/data-table.svelte";
	import { auth, initAuth } from '$lib/auth';

	onMount(() => {
		initAuth();
	});

	$: if (!$auth.isLoading && !$auth.user) {
		console.log('No user, redirecting to login');
		goto('/');
	}
</script>

{#if $auth.isLoading}
	<div class="flex h-screen w-full items-center justify-center px-4">
		<div class="text-center">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
			<p class="mt-2">Loading...</p>
		</div>
	</div>
{:else if $auth.user}
<Sidebar.Provider
	style="--sidebar-width: calc(var(--spacing) * 72); --header-height: calc(var(--spacing) * 12);"
>
	<AppSidebar variant="inset" />
	<Sidebar.Inset>
		<SiteHeader />
		<div class="flex flex-1 flex-col">
			<div class="@container/main flex flex-1 flex-col gap-2">
				<div class="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
					<SectionCards />
					<div class="px-4 lg:px-6">
						<ChartAreaInteractive />
					</div>
					<DataTable {data} />
				</div>
			</div>
		</div>
	</Sidebar.Inset>
</Sidebar.Provider>
{/if}
