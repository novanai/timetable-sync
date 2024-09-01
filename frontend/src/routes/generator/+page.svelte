
<script>
	export let data;

    import Svelecte from 'svelecte';
    import { copy } from 'svelte-copy';
    import { Tabs, TabItem } from 'flowbite-svelte';
    import { FileCopySolid } from 'flowbite-svelte-icons';
    
    let course = null;
    let modules = null;
</script>


<Tabs tabStyle="underline" contentClass="p-4 bg-gray-50 rounded-lg">
    <TabItem open title="Course">
        <div class="mb-2">
            {#key course}
                {`${window.location.protocol}//${window.location.hostname}/api?course=${course != null ? encodeURI(course) : ""}`}
                <button
                    use:copy={`${window.location.protocol}//${window.location.hostname}/api?course=${encodeURI(course)}`}
                    on:svelte-copy={(e) => alert("Copied URL to clipboard")}
                    on:svelte-copy:error={(e) => alert(e.detail.message)}
                    title="Copy URL to clipboard"
                >
                    <FileCopySolid />
                </button>
            {/key}
        </div>
        <Svelecte options={data.courses} clearable closeAfterSelect bind:value={course} />
    </TabItem>

    <TabItem title="Modules">
        <div class="mb-2">
        {#key modules}
                {`${window.location.protocol}//${window.location.hostname}/api?modules=${modules != null ? encodeURI(modules) : ""}`}
                <button
                    use:copy={`${window.location.protocol}//${window.location.hostname}/api?modules=${encodeURI(modules)}`}
                    on:svelte-copy={(e) => alert("Copied URL to clipboard")}
                    on:svelte-copy:error={(e) => alert(e.detail.message)}
                    title="Copy URL to clipboard"
                >
                    <FileCopySolid />
                </button>
            {/key}
        </div>
        <Svelecte options={data.modules} multiple max=20 clearable closeAfterSelect bind:value={modules} />
    </TabItem>
</Tabs>
