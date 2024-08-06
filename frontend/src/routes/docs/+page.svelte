<script>
    import { onMount } from 'svelte';
    import SwaggerUI from 'swagger-ui';
    import 'swagger-ui/dist/swagger-ui.css';
   
    onMount(async () => {
        SwaggerUI({
            url: "/api/openapi.json",
            dom_id: '#swagger-ui-container'
        });
    });
</script>

<div id="swagger-ui-container"></div>
