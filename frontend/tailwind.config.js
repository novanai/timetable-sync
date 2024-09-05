/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./src/**/*.{html,js,svelte,ts}",
    ],
    daisyui: {
        themes: ["winter", "dark", "night"],
    },
    plugins: [require('daisyui')],
};
