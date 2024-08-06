import flowbitePlugin from 'flowbite/plugin'

/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./src/**/*.{html,js,svelte,ts}",
        "./node_modules/flowbite-svelte/**/*.{html,js,svelte,ts}",
        "./node_modules/flowbite-svelte-icons/**/*.{html,js,svelte,ts}",
    ],
    theme: {
        extend: {
            colors: {
                primary: {
                    "50": "#f0f9ff",
                    "100": "#e0f2fe",
                    "200": "#bae6fd",
                    "300": "#7dd3fc",
                    "400": "#38bdf8",
                    "500": "#0ea5e9",
                    "600": "#0284c7",
                    "700": "#0369a1",
                    "800": "#075985",
                    "900": "#0c4a6e"
                }
            }
        }
    },
    plugins: [flowbitePlugin]
};
