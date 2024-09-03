<script>
    export let data;
    
    import { AccordionItem, Accordion, Alert, Modal } from 'flowbite-svelte';
    import { InfoCircleSolid } from 'flowbite-svelte-icons';
    import Svelecte from 'svelecte';
    import Calendar from '@event-calendar/core';
    import TimeGrid from '@event-calendar/time-grid';
    import ListWeek from '@event-calendar/list';
    import ColorHash from 'color-hash'

    var colorHash = new ColorHash({lightness: 0.7, saturation: 0.5});

    let modal_open = false;
    let modal_title = "";
    let modal_content = "";

    let courses = [];
    let modules = [];
    let events = {};

    let ec;
    let plugins = [TimeGrid, ListWeek];
    let options = {
        // Default to day view on smaller devices
        view: window.innerWidth > 768 ? 'timeGridWeek' : 'timeGridDay',
        headerToolbar: {
            start: 'prev,next today',
            center: 'title',
            end: 'timeGridWeek,timeGridDay,listWeek',
        },
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
        datesSet: fetchEvents,
    };

    async function fetchEvents(info = null) {
        let events_data
        if (courses.length == 0 && modules.length == 0) {
            events_data = []
        } else {
            let view = ec.getView()
            let params = new URLSearchParams()
            
            params.set('courses', courses)
            params.set('modules', modules)
            params.set('start', view.currentStart.toISOString())
            params.set('end', view.currentEnd.toISOString())
            params.set('format', 'json')
            params.set('display', 'true')
            
            let response = await fetch(`/api?${params.toString()}`)
            events_data = await response.json()
        }

        updateEvents(events_data)
    }

    function convertDate(date) {
        return new Date(date.toLocaleString('en-US', { timeZone: 'Europe/Dublin' }))
    }

    function updateEvents(events_data) {
        ec.getEvents().forEach((item, _) => ec.removeEventById(item.id))
        events = {}

        events_data.forEach(
            function (event, _) {
                let module_codes = new Set()
                event.parsed_name_data.forEach((data, _) => data.module_codes.forEach((code, _) => module_codes.add(code)))
                module_codes = Array.from(module_codes)

                ec.addEvent({
                    id: event.identity,
                    start: convertDate(new Date(event.start)),
                    end: convertDate(new Date(event.end)),
                    title: {'html': `<span class="font-bold">${event.display.summary}</span><br>📄 ${event.display.description}<br>📍 ${event.display.location}`},
                    backgroundColor: colorHash.hex(module_codes.join(''))
                })
                events[event.identity] = event
            }
        )
        
    }

    // Copied from https://stackoverflow.com/a/19622253
    function displayList(a) {
        return [
                a
                .slice(0, a.length - 1 || 1)
                .join(", ")
            ]
            .concat(
                a
                .slice()
                .splice(-1, Number(a.length > 1))
            )
            .join(" & ");
    }

    function updateAndDisplayModal(info) {
        let event = events[info.event.id]
        modal_title = event.display.summary
        modal_content = (
            `<p>📄 ${event.display.description}</p>`
            + `<p>📍 ${event.display.location_long}</p>`
            + (event.staff_member != null ? `<p>🧑‍🏫 ${event.staff_member}</p>` : '')
            + (event.weeks != null ? `🗓️ Weeks ${displayList(event.weeks)}` : '')
        )
        modal_open = true;
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
      <Svelecte options={data.courses} multiple max=3 clearable closeAfterSelect bind:value={courses} on:change={fetchEvents} />  
    </AccordionItem>
    <AccordionItem>
        <span slot="header">Module Selection</span>
        <Svelecte options={data.modules} multiple max=20 clearable closeAfterSelect bind:value={modules} on:change={fetchEvents} />
    </AccordionItem>
</Accordion>

<br>

<Calendar bind:this={ec} {plugins} {options} />

<Modal bind:title={modal_title} bind:open={modal_open} xs autoclose outsideclose>
    <p>
        {@html modal_content}
    </p>
</Modal>
