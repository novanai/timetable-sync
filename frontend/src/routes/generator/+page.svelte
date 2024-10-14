<script>
    export let data;

    import Svelecte from "svelecte";
    import { copy } from "svelte-copy";

    let api_data = {
        timetable: {
            title: "Timetable",
            url_builder: build_timetable_url,
            data: {
                courses: {
                    name: "Courses",
                    selected: [],
                    data: data.courses,
                    max: 8,
                },
                modules: {
                    name: "Modules",
                    selected: [],
                    data: data.modules,
                    max: 20,
                },
                locations: {
                    name: "Locations",
                    selected: [],
                    data: data.locations,
                    max: 8,
                },
            },
        },
        cns: {
            title: "Clubs & Societies",
            url_builder: build_cns_url,
            data: {
                clubs: {
                    name: "Clubs",
                    selected: [],
                    data: data.clubs,
                    max: 8,
                },
                societies: {
                    name: "Societies",
                    selected: [],
                    data: data.societies,
                    max: 8,
                },
            },
        },
    };

    function build_url(data, path) {
        let params = new URLSearchParams();

        for (let [key, value] of Object.entries(data)) {
            if (value.selected.length > 0) {
                params.set(key, value.selected);
            }
        }

        return `${window.location.protocol}//${window.location.hostname}/${path}?${params.toString()}`;
    }

    function build_timetable_url() {
        return build_url(api_data.timetable.data, "api");
    }

    function build_cns_url() {
        return build_url(api_data.cns.data, "api/cns");
    }
</script>

<div class="mx-4 md:mx-16 lg:mx-32">
    {#each Object.entries(api_data) as [group, data]}
        <div class="mb-4 last:mb-0">
            <div class="text-2xl font-bold mb-2">{data.title}</div>
            <div class="flex flex-row">
                <div class="overflow-hidden">
                    <p>
                        {#key api_data}
                            {data.url_builder()}
                        {/key}
                    </p>
                </div>
                <div>
                    {#key api_data}
                        <button
                            use:copy={data.url_builder()}
                            on:svelte-copy={(e) => alert("Copied URL to clipboard")}
                            on:svelte-copy:error={(e) => alert(e.detail.message)}
                            title="Copy URL to clipboard"
                            class="ml-2"
                        >
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke-width="1.5"
                                stroke="currentColor"
                                class="h-5 w-5"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184"
                                />
                            </svg>
                        </button>
                    {/key}
                </div>
            </div>
            <div role="tablist" class="tabs tabs-bordered">
                {#each Object.entries(data.data) as [key, option], i}
                    <input
                        type="radio"
                        name="selection_tabs_{group}"
                        role="tab"
                        class="tab"
                        aria-label={option.name}
                        checked={i === 0 ? "checked" : ""}
                    />
                    <div role="tabpanel" class="tab-content mt-2">
                        <Svelecte
                            class="mt-2"
                            options={option.data.map((item) => {
                                return { value: item.identity, text: item.name };
                            })}
                            multiple
                            max={option.max}
                            clearable
                            closeAfterSelect
                            bind:value={api_data[group].data[key].selected}
                        />
                    </div>
                {/each}
            </div>
        </div>
    {/each}
</div>
