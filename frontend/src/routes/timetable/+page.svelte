<script>
    export let data;
    
    import { AccordionItem, Accordion, Alert, Modal } from 'flowbite-svelte';
    import { InfoCircleSolid, MapPinAltOutline, FileLinesOutline } from 'flowbite-svelte-icons';
    import Svelecte from 'svelecte';
    import Calendar from '@event-calendar/core';
    import TimeGrid from '@event-calendar/time-grid';
    import ListWeek from '@event-calendar/list';

    let modal = false;
    let modal_content = "";

    let courses = [];
    let modules = [];

    let ec;
    let plugins = [TimeGrid, ListWeek];
    let options = {
        // Default to day view on smaller devices
        view: window.innerWidth > 768 ? 'timeGridWeek' : 'timeGridDay',  // https://github.com/vkurko/calendar?tab=readme-ov-file#view
        headerToolbar: {
            start: 'prev,next today',
            center: 'title',
            end: 'timeGridWeek,timeGridDay,listWeek',
        },
        eventSources: [{
            url: '/api/calendar',
            extraParams: {
                courses: courses,
                modules: modules,
            }
        }],
        allDaySlot: false,
        hiddenDays: [6, 0],  // Saturday, Sunday
        slotMinTime: '08:00:00',
        slotMaxTime: '19:00:00',
        editable: false,
        firstDay: 1,  // Monday
        nowIndicator: true,
        slotDuration: '01:00:00',
        slotHeight: 96,
        eventTextColor: '#000',
        eventClick: updateAndDisplayModal,
    };

    function updateOptions() {
        options.eventSources[0].extraParams.courses = courses;
        options.eventSources[0].extraParams.modules = modules;
        ec.refetchEvents();
    }

    function updateAndDisplayModal(info) {
        modal_content = info.event.title.html;
        modal = true;
    }
</script>

<Alert border color="blue">
    <InfoCircleSolid slot="icon" class="w-5 h-5" />
    <span class="font-bold">NOTE:</span>
    This page is still under development and you may encounter issues.
</Alert>

<br>

<Accordion>
    <AccordionItem open>
      <span slot="header">Course Selection</span>
      <Svelecte options={data.courses} multiple max=3 clearable closeAfterSelect bind:value={courses} on:change={updateOptions} />  
    </AccordionItem>
    <AccordionItem>
        <span slot="header">Module Selection</span>
        <Svelecte options={data.modules} multiple max=20 clearable closeAfterSelect bind:value={modules} on:change={updateOptions} />
    </AccordionItem>
</Accordion>

<br>

<Calendar bind:this={ec} {plugins} {options} />

<Modal bind:open={modal} xs autoclose outsideclose>
    <p>
        {@html modal_content}
    </p>
</Modal>
