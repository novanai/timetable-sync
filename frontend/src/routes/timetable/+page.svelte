<script>
    export let data;

    import Svelecte from "svelecte";
    import Calendar from "@event-calendar/core";
    import TimeGrid from "@event-calendar/time-grid";
    import ListWeek from "@event-calendar/list";
    import ColorHash from "color-hash";

    var colorHash = new ColorHash({ lightness: 0.7, saturation: 0.5 });

    let modal_title = "";
    let modal_content = "";

    let timetable_data = {
        courses: {
            name: "Courses",
            selected: [],
            data: data.courses,
            max: 3,
        },
        modules: {
            name: "Modules",
            selected: [],
            data: data.modules,
            max: 20,
        },
    };
    let events = {};

    let ec;
    let plugins = [TimeGrid, ListWeek];
    let options = {
        // Default to day view on smaller devices
        view: window.innerWidth > 768 ? "timeGridWeek" : "timeGridDay",
        headerToolbar: {
            start: "prev,next today",
            center: "title",
            end: "timeGridWeek,timeGridDay,listWeek",
        },
        allDaySlot: false,
        hiddenDays: [6, 0], // Saturday, Sunday
        slotMinTime: "08:00:00",
        slotMaxTime: "19:00:00",
        editable: false,
        firstDay: 1, // Monday
        nowIndicator: true,
        slotDuration: "01:00:00",
        slotHeight: 96,
        eventTextColor: "#000",
        eventClick: updateAndDisplayModal,
        datesSet: fetchEvents,
    };

    async function fetchEvents(info = null) {
        let events_data;
        if (
            timetable_data.courses.selected.length == 0 &&
            timetable_data.modules.selected.length == 0
        ) {
            events_data = [];
        } else {
            let view = ec.getView();
            let params = new URLSearchParams();

            params.set("courses", timetable_data.courses.selected);
            params.set("modules", timetable_data.modules.selected);
            params.set("start", view.currentStart.toISOString());
            params.set("end", view.currentEnd.toISOString());
            params.set("format", "json");
            params.set("display", "true");

            let response = await fetch(`/api?${params.toString()}`);
            events_data = await response.json();
        }

        updateEvents(events_data);
    }

    function convertDate(date) {
        return new Date(
            date.toLocaleString("en-US", { timeZone: "Europe/Dublin" }),
        );
    }

    function updateEvents(events_data) {
        ec.getEvents().forEach((item, _) => ec.removeEventById(item.id));
        events = {};

        events_data.forEach(function (event, _) {
            let module_codes = new Set();
            event.parsed_name_data.forEach((data, _) =>
                data.module_codes.forEach((code, _) => module_codes.add(code)),
            );
            module_codes = Array.from(module_codes);

            ec.addEvent({
                id: event.identity,
                start: convertDate(new Date(event.start)),
                end: convertDate(new Date(event.end)),
                title: {
                    html: `<span class="font-bold">${event.display.summary}</span><br>📄 ${event.display.description}<br>📍 ${event.display.location}`,
                },
                backgroundColor: colorHash.hex(module_codes.join("")),
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
        let start = convertDate(new Date(event.start)).toLocaleTimeString(
            "en-GB",
            { hour: "2-digit", minute: "2-digit" },
        );
        let end = convertDate(new Date(event.end)).toLocaleTimeString("en-GB", {
            hour: "2-digit",
            minute: "2-digit",
        });
        let date = convertDate(new Date(event.start)).toLocaleDateString(
            "en-GB",
            { weekday: "long", day: "numeric", month: "long", year: "numeric" },
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

    window.addEventListener("theme-update", function (e) {
        let theme = e.detail.value;
        if (theme == "winter") {
            document
                .getElementById("calendar-container")
                .classList.remove("ec-dark");
        } else {
            document
                .getElementById("calendar-container")
                .classList.add("ec-dark");
        }
    });
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
            />
        </div>
    {/each}
</div>

<br />

<div
    id="calendar-container"
    class={localStorage.getItem("theme") != "winter" ? "ec-dark" : ""}
>
    <Calendar bind:this={ec} {plugins} {options} />
</div>

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
