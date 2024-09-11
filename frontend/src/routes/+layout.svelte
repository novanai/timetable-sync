<script>
    import { page } from "$app/stores";
    import { onMount } from "svelte";
    import { themeChange } from "theme-change";

    import "../app.css";

    onMount(() => {
        themeChange(false);
    });

    $: activeUrl = $page.url.pathname;

    let themes = [
        { name: "Light", value: "winter" },
        { name: "Dark", value: "night" },
    ];
    let pages = [
        { name: "Home", value: "/" },
        { name: "Timetable Viewer", value: "/timetable" },
        { name: "Timetable Generator", value: "/generator" },
        { name: "API Documentation", value: "/docs" },
    ];
</script>

<div class="min-h-screen">
    <div class="navbar bg-base-100">
        <div class="navbar-start">
            <div class="dropdown">
                <div tabindex="0" role="button" class="btn btn-ghost lg:hidden">
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-5 w-5"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M4 6h16M4 12h8m-8 6h16"
                        />
                    </svg>
                </div>
                <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
                <ul
                    tabindex="0"
                    class="menu menu-sm dropdown-content bg-base-100 rounded-box z-[1] mt-3 w-52 p-2 shadow"
                >
                    {#each pages as page}
                        <li>
                            <a
                                href={page.value}
                                class={activeUrl === page.value
                                    ? "text-primary"
                                    : ""}>{page.name}</a
                            >
                        </li>
                    {/each}
                </ul>
            </div>
            <a class="btn btn-ghost text-xl" href="/">TimetableSync</a>
        </div>
        <div class="navbar-center hidden lg:flex">
            <ul class="menu menu-horizontal px-1">
                {#each pages as page}
                    <li>
                        <a
                            href={page.value}
                            class={activeUrl === page.value
                                ? "text-primary"
                                : ""}>{page.name}</a
                        >
                    </li>
                {/each}
            </ul>
        </div>
        <div class="navbar-end">
            <a href="https://github.com/novanai/timetable-sync" target="_blank">
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 496 512"
                    class="h-7 w-7 fill-current mr-2"
                >
                    <!--!Font Awesome Free 6.6.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.-->
                    <path
                        d="M165.9 397.4c0 2-2.3 3.6-5.2 3.6-3.3 .3-5.6-1.3-5.6-3.6 0-2 2.3-3.6 5.2-3.6 3-.3 5.6 1.3 5.6 3.6zm-31.1-4.5c-.7 2 1.3 4.3 4.3 4.9 2.6 1 5.6 0 6.2-2s-1.3-4.3-4.3-5.2c-2.6-.7-5.5 .3-6.2 2.3zm44.2-1.7c-2.9 .7-4.9 2.6-4.6 4.9 .3 2 2.9 3.3 5.9 2.6 2.9-.7 4.9-2.6 4.6-4.6-.3-1.9-3-3.2-5.9-2.9zM244.8 8C106.1 8 0 113.3 0 252c0 110.9 69.8 205.8 169.5 239.2 12.8 2.3 17.3-5.6 17.3-12.1 0-6.2-.3-40.4-.3-61.4 0 0-70 15-84.7-29.8 0 0-11.4-29.1-27.8-36.6 0 0-22.9-15.7 1.6-15.4 0 0 24.9 2 38.6 25.8 21.9 38.6 58.6 27.5 72.9 20.9 2.3-16 8.8-27.1 16-33.7-55.9-6.2-112.3-14.3-112.3-110.5 0-27.5 7.6-41.3 23.6-58.9-2.6-6.5-11.1-33.3 2.6-67.9 20.9-6.5 69 27 69 27 20-5.6 41.5-8.5 62.8-8.5s42.8 2.9 62.8 8.5c0 0 48.1-33.6 69-27 13.7 34.7 5.2 61.4 2.6 67.9 16 17.7 25.8 31.5 25.8 58.9 0 96.5-58.9 104.2-114.8 110.5 9.2 7.9 17 22.9 17 46.4 0 33.7-.3 75.4-.3 83.6 0 6.5 4.6 14.4 17.3 12.1C428.2 457.8 496 362.9 496 252 496 113.3 383.5 8 244.8 8zM97.2 352.9c-1.3 1-1 3.3 .7 5.2 1.6 1.6 3.9 2.3 5.2 1 1.3-1 1-3.3-.7-5.2-1.6-1.6-3.9-2.3-5.2-1zm-10.8-8.1c-.7 1.3 .3 2.9 2.3 3.9 1.6 1 3.6 .7 4.3-.7 .7-1.3-.3-2.9-2.3-3.9-2-.6-3.6-.3-4.3 .7zm32.4 35.6c-1.6 1.3-1 4.3 1.3 6.2 2.3 2.3 5.2 2.6 6.5 1 1.3-1.3 .7-4.3-1.3-6.2-2.2-2.3-5.2-2.6-6.5-1zm-11.4-14.7c-1.6 1-1.6 3.6 0 5.9 1.6 2.3 4.3 3.3 5.6 2.3 1.6-1.3 1.6-3.9 0-6.2-1.4-2.3-4-3.3-5.6-2z"
                    />
                </svg>
            </a>
            <div class="dropdown dropdown-end">
                <div tabindex="0" role="button" class="btn m-1">
                    Theme
                    <svg
                        class="inline-block h-2 w-2 fill-current opacity-60"
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 2048 2048"
                    >
                        <path
                            d="M1799 349l242 241-1017 1017L7 590l242-241 775 775 775-775z"
                        ></path>
                    </svg>
                </div>
                <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
                <ul
                    tabindex="0"
                    class="dropdown-content bg-base-300 rounded-box z-[1] w-52 p-2 shadow-2xl"
                >
                    {#each themes as { name, value }}
                        <li>
                            <input
                                type="radio"
                                name="theme-dropdown"
                                class="theme-controller btn btn-sm btn-block btn-ghost justify-start"
                                aria-label={name}
                                data-set-theme={value}
                            />
                        </li>
                    {/each}
                </ul>
            </div>
        </div>
    </div>

    <div class="m-4">
        <slot></slot>
    </div>

    <footer
        class="footer footer-center bg-primary text-primary-content p-4 sticky top-full"
    >
        <aside>
            <p>
                Made with ❤️ by <a
                    href="https://github.com/novanai"
                    class="link link-hover">nova</a
                >
            </p>
            <p>
                Powered by <a
                    href="https://redbrick.dcu.ie"
                    class="link link-hover">Redbrick</a
                >
            </p>
        </aside>
    </footer>
</div>
