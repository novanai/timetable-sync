<script>
    export let data;

    import { onMount } from "svelte";
    import { Calendar } from "@fullcalendar/core";
    import timeGridPlugin from "@fullcalendar/timegrid";
    import listPlugin from "@fullcalendar/list";
    import momentTimezonePlugin from "@fullcalendar/moment-timezone";
    import { toMoment } from "@fullcalendar/moment";
    import Svelecte from "svelecte";
    import ColorHash from "color-hash";

    var colorHash = new ColorHash({ lightness: 0.7, saturation: 0.5 });

    let modal_title = "";
    let modal_content = "";

    let timetable_data = {
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
    };
    // TODO: store events as {module/course identity: {event identity: event}}
    let events = {};

    let calendarEl;
    let calendar;

    function initCalendar() {
        calendar = new Calendar(calendarEl, {
            plugins: [timeGridPlugin, listPlugin, momentTimezonePlugin],
            initialView: getDefaultView(),
            headerToolbar: {
                left: "prev,next today",
                center: "title",
                right: "timeGridWeek,timeGridDay,listWeek",
            },
            locale: "en-GB",
            timeZone: "Europe/Dublin",
            slotLabelFormat: {
                hour: "numeric",
                minute: "numeric",
            },
            allDaySlot: false,
            weekends: false,
            slotMinTime: "08:00:00",
            slotMaxTime: "19:00:00",
            editable: false,
            firstDay: 1, // Monday
            nowIndicator: true,
            slotDuration: "01:00:00",
            expandRows: true,
            height: calcHeight(getDefaultView()),
            windowResize: function (info) {
                calendar.setOption("height", calcHeight(info.view.type));
            },
            eventContent: function (info) {
                return { html: info.event.title };
            },
            eventTextColor: "#000",
            eventBorderColor: "#0000",
            eventClick: updateAndDisplayModal,
            datesSet: fetchEvents,
        });
        calendar.render();
    }

    onMount(async () => {
        initCalendar();

        return () => {
            calendar && calendar.destroy();
        };
    });

    function getDefaultView() {
        return window.innerWidth > 768 ? "timeGridWeek" : "timeGridDay";
    }

    function calcHeight(viewType) {
        if (viewType == "timeGridDay") {
            return 1050;
        }
        let height = 2850 - (225 * window.innerWidth) / 128;
        if (height > 1500) {
            height = 1500;
        } else if (height < 1050) {
            height = 1050;
        }
        return height;
    }

    async function fetchEvents(info = null) {
        let events_data;
        if (
            timetable_data.courses.selected.length == 0 &&
            timetable_data.modules.selected.length == 0 &&
            timetable_data.locations.selected.length == 0
        ) {
            events_data = [];
        } else {
            let view = calendar.view;
            let params = new URLSearchParams();

            params.set("courses", timetable_data.courses.selected);
            params.set("modules", timetable_data.modules.selected);
            params.set("locations", timetable_data.locations.selected)
            params.set("start", view.currentStart.toISOString());
            params.set("end", view.currentEnd.toISOString());
            params.set("format", "json");
            params.set("display", "true");

            let response = await fetch(`/api?${params.toString()}`);
            events_data = await response.json();
        }

        updateEvents(events_data);
    }

    function updateEvents(events_data) {
        calendar.getEvents().forEach((event, _) => event.remove());
        events = {};

        events_data.forEach(function (event, _) {
            calendar.addEvent({
                id: event.identity,
                // groupId
                start: event.start,
                end: event.end,
                title: `<p class="font-bold">${event.display.summary}</p><p>📄 ${event.display.description}</p><p>📍 ${event.display.location}</p>`,
                backgroundColor: colorHash.hex(
                    (event.module_name
                        ? event.module_name
                        : event.name
                    ).replaceAll(" ", ""),
                ),
            });
            events[event.identity] = event;
        });
    }

    // Copied from https://stackoverflow.com/a/19622253
    function displayList(a) {
        return [a.slice(0, a.length - 1 || 1).join(", ")]
            .concat(a.slice().splice(-1, Number(a.length > 1)))
            .join(" & ");
    }

    function updateAndDisplayModal(info) {
        let event = events[info.event.id];
        modal_title = event.display.summary;

        let start = toMoment(info.event.start, calendar).format("HH:mm");
        let end = toMoment(info.event.end, calendar).format("HH:mm");
        let date = toMoment(info.event.start, calendar).format(
            "dddd, D MMMM YYYY",
        );
        modal_content =
            `<p>🕑 ${start}-${end} • ${date}` +
            `<p>📄 ${event.display.description}</p>` +
            `<p>📍 ${event.display.location_long}</p>` +
            (event.staff_member != null
                ? `<p>🧑‍🏫 ${event.staff_member}</p>`
                : "") +
            (event.weeks != null ? `🗓️ Weeks ${displayList(event.weeks)}` : "");
        document.getElementById("info_modal").showModal();
    }
</script>

<div role="alert" class="alert">
    <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        class="stroke-info h-6 w-6 shrink-0"
    >
        <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        ></path>
    </svg>
    <span>
        This page is still under development and you may encounter issues.
    </span>
</div>

<br />

<div role="tablist" class="tabs tabs-bordered">
    {#each Object.entries(timetable_data) as [key, option], i}
        <input
            type="radio"
            name="selection_tabs"
            role="tab"
            class="tab"
            aria-label={option.name}
            checked={i === 0 ? "checked" : ""}
        />
        <div role="tabpanel" class="tab-content mt-2">
            <Svelecte
                class="mt-2"
                options={option.data}
                multiple
                max={option.max}
                clearable
                closeAfterSelect
                bind:value={timetable_data[key].selected}
                on:change={fetchEvents}
            />
        </div>
    {/each}
</div>

<br />

<div bind:this={calendarEl}></div>

<dialog id="info_modal" class="modal">
    <div class="modal-box">
        <form method="dialog">
            <button
                class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2"
            >
                ✕
            </button>
        </form>
        <h3 class="text-lg font-bold">{modal_title}</h3>
        <p class="py-4">{@html modal_content}</p>
    </div>
    <form method="dialog" class="modal-backdrop">
        <button class="cursor-default"></button>
    </form>
</dialog>
