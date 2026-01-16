import type { Route } from "./+types/timetable";
import { useState, useEffect } from "react";
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
        { title: "TimetableViewer | TimetableSync" },
        { name: "description", content: "View your timetable." },
    ];
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

const createLoadOptions = (type: string) => {
    return async (inputValue: string): Promise<Option[]> => {
        if (!inputValue) return [];

        const category_type_id = category_type_mapping.get(type);

        const res = await fetch(`http://localhost/api/v3/timetable/category/${category_type_id}/items?query=${inputValue}`);
        const data = await res.json();

        return data.map((item: any) => ({
            label: item.name,
            value: item.identity,
        }));
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

export default function Timetable() {
    const [events, setEvents] = useState<Event[]>([]);

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

    const location = useLocation();

    async function fetchCalendar() {
        if (!courseOptions.length && !moduleOptions.length && !locationOptions.length) {
            return []
        };

        selects.map(({id, value}) => {
            // clear search params, set new ones
            searchParams.delete(id);

            value.map(({value}) => {
                searchParams.append(id, value);
            })
        })

        setSearchParams(searchParams);

        const res = await fetch(
            `http://localhost/api/v3/timetable/events?${searchParams.toString()}&extra_details=all`,
            {
                headers: {"media-type": "application/json"},
            }
        );
        return await res.json();
    }

    useEffect(() => {
        const getViewFromWith = () => window.innerWidth > 768 ? Views.WEEK : Views.DAY;
        const updateView = () => setView(getViewFromWith());

        updateView();
        window.addEventListener("resize", updateView);


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
                        `http://localhost/api/v3/timetable/category/${category_type_id}/items/${value}`
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
        <main>
            <Tabs className="mb-4">
                <TabList>
                    <Tab>Courses</Tab>
                    <Tab>Modules</Tab>
                    <Tab>Locations</Tab>
                </TabList>

                {selects.map(({ id, value, setValue }) => (
                    <TabPanel key={id}>
                        <AsyncSelect
                            isMulti
                            name={`select-${id}`}
                            cacheOptions
                            loadOptions={createLoadOptions(id)}
                            value={value}
                            onChange={setValue}
                            styles={{
                                menuPortal: (base) => ({ ...base, zIndex: 9999 }),
                            }}
                        />
                    </TabPanel>
                ))}
            </Tabs>

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
    );
}
