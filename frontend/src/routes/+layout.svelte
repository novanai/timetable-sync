<script>
    import '../app.css';
    import {
        Navbar,
        NavBrand,
        NavLi,
        NavUl,
        NavHamburger,
    } from 'flowbite-svelte';
    import { page } from '$app/stores';

    $: activeUrl = $page.url.pathname;
</script>

<Navbar rounded color="primary">
    <NavBrand href="/">
        <img src="/favicon.png" class="me-3 h-6 sm:h-9" alt="TimetableSync Logo" />
        <span class="self-center whitespace-nowrap text-xl font-semibold">
            TimetableSync
        </span>
    </NavBrand>
    <NavHamburger />
    <NavUl {activeUrl}>
        <NavLi href="/">Home</NavLi>
        <NavLi href="/generator">Timetable Generator</NavLi>
        <NavLi href="/docs">API Documentation</NavLi>
    </NavUl>
    
</Navbar>

<slot></slot>
