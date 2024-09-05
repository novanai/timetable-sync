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
        { name: "Dark", value: "dark" },
        { name: "Night", value: "night" },
    ];
    let pages = [
        { name: "Home", value: "/" },
        { name: "Timetable Viewer", value: "/timetable" },
        { name: "Timetable Generator", value: "/generator" },
        { name: "API Documentation", value: "/docs" },
    ];
</script>

<head>
    <script>
        function dispatchThemeUpdate(theme) {
            window.dispatchEvent(
                new CustomEvent("theme-update", { detail: { value: theme } }),
            );
        }
    </script>
</head>

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
                        class={activeUrl === page.value ? "text-primary" : ""}
                        >{page.name}</a
                    >
                </li>
            {/each}
        </ul>
    </div>
    <div class="navbar-end">
        <div class="dropdown dropdown-end">
            <div tabindex="0" role="button" class="btn m-1">
                Theme
                <svg
                    width="12px"
                    height="12px"
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
                            onclick="dispatchThemeUpdate('{value}')"
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
