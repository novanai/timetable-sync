import type { Route } from "./+types/timetable";
import { useState, useEffect, useMemo } from "react";
import { useSearchParams, useLocation } from "react-router";
import AsyncSelect from 'react-select/async';
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import { Calendar, Views, momentLocalizer } from "react-big-calendar";
import type { Event, View } from "react-big-calendar";
import moment from "moment";

import ColorHashModule from "color-hash";
const ColorHash = ColorHashModule.default || ColorHashModule;

var colorHash = new ColorHash({ lightness: [0.6, 0.7, 0.8], saturation: [0.4, 0.5, 0.6] });

moment.updateLocale('en-GB', {
    week: {
        dow: 1,
        doy: 4,
    }
})

const localizer = momentLocalizer(moment);

export function meta({ }: Route.MetaArgs) {
    return [
        { title: "Timetable Viewer | TimetableSync" },
        { name: "description", content: "View your timetable." },
    ];
}

const select_colours = {
    primary: "var(--color-primary)",  // border active
    // primary75: "",
    // primary50: "",
    primary25: "var(--color-base-300)",  // active select option background
    danger: "var(--color-error-content)",  // remove option 'X'
    dangerLight: "var(--color-error)",  // remove option 'X' background
    neutral0: "var(--color-base-100)",  // select menu background
    // neutral5: "",
    neutral10: "var(--color-base-300)",  // selected option background
    neutral20: "var(--color-base-content)",  // border, inner arrow
    // neutral30: "",  // border hover
    // neutral40: "",  // "no options" text
    neutral50: "var(--color-base-content)",  // text
    neutral60: "var(--color-base-content)",  // arrow active
    // neutral70: "",
    neutral80: "var(--color-base-content)",  // cursor, input text
    // neutral90: "",
}

type Option = {
    label: string;
    value: string;
}

type SelectConfig = {
    id: string;
    value: readonly Option[];
    setValue: React.Dispatch<React.SetStateAction<readonly Option[]>>;
};

const category_type_mapping = new Map()
category_type_mapping.set("module", "525fe79b-73c3-4b5c-8186-83c652b3adcc")
category_type_mapping.set("location", "1e042cb1-547d-41d4-ae93-a1f2c3d34538")
category_type_mapping.set("course", "241e4d36-60e0-49f8-b27e-99416745d98d")

const createLoadOptions = (category_type: string) => {
    const category_type_id = category_type_mapping.get(category_type);

    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    return (inputValue: string, callback: (options: Option[]) => void) => {
        if (!inputValue) {
            callback([]);
            return;
        }

        if (timeoutId) {
            clearTimeout(timeoutId);
        }

        timeoutId = setTimeout(async () => {
            try {
                const res = await fetch(
                    `/api/v3/timetable/category/${category_type_id}/items?query=${inputValue}`
                );
                const data = await res.json();

                callback(
                    data.map((item: any) => ({
                        label: item.name,
                        value: item.identity,
                    }))
                );
            } catch (e) {
                callback([]);
            }
        }, 300);
    };
};

function parseCalendarJSON(data: any[]): Event[] {
    return data.map(event => ({
        title: event.display.summary,
        start: new Date(event.start),
        end: new Date(event.end),
        allDay: false,

        resource: event,
    }));
}

function formatWeeks(weeks: number[]): string {
    if (weeks.length === 0) return "";

    const ranges: string[] = [];

    let start = weeks[0];
    let end = weeks[0];

    for (let i = 1; i < weeks.length; i++) {
        const current = weeks[i];

        if (current === end + 1) {
            end = current;
        } else {
            ranges.push(start === end ? `${start}` : `${start}-${end}`);
            start = end = current;
        }
    }

    ranges.push(start === end ? `${start}` : `${start}-${end}`);

    return ranges.join(", ");
}

export default function Timetable() {
    const [events, setEvents] = useState<Event[]>([]);
    const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);

    const [courseOptions, setCourseOptions] = useState<readonly Option[]>([]);
    const [moduleOptions, setModuleOptions] = useState<readonly Option[]>([]);
    const [locationOptions, setLocationOptions] = useState<readonly Option[]>([]);

    const [searchParams, setSearchParams] = useSearchParams();

    const [view, setView] = useState<View>(Views.WEEK);

    const selects: Array<SelectConfig> = [
        { id: "course", value: courseOptions, setValue: setCourseOptions },
        { id: "module", value: moduleOptions, setValue: setModuleOptions },
        { id: "location", value: locationOptions, setValue: setLocationOptions },
    ]

    const handleEventClick = (event: Event) => {
        setSelectedEvent(event);
    };

    const closeModal = () => {
        setSelectedEvent(null);
    };

    const location = useLocation();

    async function fetchCalendar() {
        selects.map(({ id, value }) => {
            // clear search params, set new ones
            searchParams.delete(id);

            value.map(({ value }) => {
                searchParams.append(id, value);
            })
        })

        setSearchParams(searchParams);

        if (!courseOptions.length && !moduleOptions.length && !locationOptions.length) {
            return []
        };

        const res = await fetch(
            `/api/v3/timetable/events?${searchParams.toString()}&extra_details=all`,
            {
                headers: { "media-type": "application/json" },
            }
        );
        return await res.json();
    }

    useEffect(() => {
        setView(window.innerWidth > 768 ? Views.WEEK : Views.DAY);
    }, []);

    useEffect(() => {
        const loadSelectedOptions = async () => {
            const params = new URLSearchParams(location.search);

            for (const item of selects) {
                const values = params.getAll(item.id)
                if (!values) return;

                item.setValue(await Promise.all(values.map(async (value) => {
                    const category_type_id = category_type_mapping.get(item.id);
                    const res = await fetch(
                        `/api/v3/timetable/category/${category_type_id}/items/${value}`
                    )
                    const data = await res.json()
                    return { label: data["name"], value: value };
                })))
            }
        };

        loadSelectedOptions();
    }, []);

    useEffect(() => {
        const loadEvents = async () => {
            const data = await fetchCalendar();
            setEvents(parseCalendarJSON(data));
        };

        loadEvents();
    }, [courseOptions, moduleOptions, locationOptions]);

    return (
        <>
            <main>
                <div className="mx-4 md:mx-16 lg:mx-32">
                    <Tabs className="mb-4">
                        <TabList>
                            <Tab>Courses</Tab>
                            <Tab>Modules</Tab>
                            <Tab>Locations</Tab>
                        </TabList>

                        {selects.map(({ id, value, setValue }) => {
                            const loadOptions = useMemo(
                                () => createLoadOptions(id),
                                [id]
                            );

                            return (
                                <TabPanel key={id}>
                                    <AsyncSelect
                                        isMulti
                                        name={`select-${id}`}
                                        cacheOptions
                                        loadOptions={loadOptions}
                                        value={value}
                                        onChange={setValue}
                                        styles={{
                                            menuPortal: (base) => ({ ...base, zIndex: 9999 }),
                                        }}
                                        theme={(theme) => ({
                                            ...theme,
                                            colors: {
                                                ...theme.colors,
                                                ...select_colours,
                                            },
                                        })}
                                    />
                                </TabPanel>
                            )
                        })}
                    </Tabs>
                </div>

                <Calendar
                    localizer={localizer}
                    defaultDate={new Date()}
                    view={view}
                    views={[Views.WEEK, Views.DAY]}
                    onView={setView}
                    min={new Date(0, 0, 0, 8, 0)}
                    max={new Date(0, 0, 0, 19, 0)}
                    style={{ height: "960px" }}
                    events={events}
                    onSelectEvent={handleEventClick}
                    eventPropGetter={(event) => {
                        const backgroundColor = colorHash.hex((event.title as string).split(" ")[0]);

                        return {
                            style: {
                                backgroundColor,
                            },
                        };
                    }}
                    components={{
                        event: ({ event }) => (
                            <div>
                                <p><b>{event.title}</b></p>
                                <p>📄 {event.resource.display.description}</p>
                                <p>📍 {event.resource.display.location}</p>
                            </div>
                        )
                    }}
                />
            </main>

            {selectedEvent && (
                <dialog className="modal modal-open">
                    <div className="modal-box">
                        <button
                            className="btn btn-sm btn-circle btn-ghost absolute right-2 top-2"
                            onClick={closeModal}
                        >
                            ✕
                        </button>

                        <h3 className="text-lg font-bold mb-2">{selectedEvent.title}</h3>
                        <p>
                            🕑 {selectedEvent.start && localizer.format(selectedEvent.start, "HH:mm")}-{selectedEvent.end && localizer.format(selectedEvent.end, "HH:mm")} • {selectedEvent.start && localizer.format(selectedEvent.start, "dddd, D MMMM YYYY")}
                        </p>
                        <p>📄 {selectedEvent.resource.display.description}</p>
                        <p>📍 {selectedEvent.resource.display.location_long}</p>
                        {selectedEvent.resource.staff_member && (<p>🧑‍🏫 Staff Member: {selectedEvent.resource.staff_member}</p>)}
                        {selectedEvent.resource.weeks && (<p>🗓️ Weeks: {formatWeeks(selectedEvent.resource.weeks)}</p>)}
                    </div>

                    <form method="dialog" className="modal-backdrop">
                        <button onClick={closeModal} className="cursor-default"></button>
                    </form>
                </dialog>
            )}
        </>
    );
}
