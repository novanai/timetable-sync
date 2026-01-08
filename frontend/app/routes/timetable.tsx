import type { Route } from "./+types/timetable";
import { useState, useEffect } from "react";
import AsyncSelect from 'react-select/async';
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import { Calendar, momentLocalizer } from "react-big-calendar";
import type { Event } from "react-big-calendar";
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
        { title: "New React Router App" },
        { name: "description", content: "Welcome to React Router!" },
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

const createLoadOptions = (type: string) => {
    return async (inputValue: string): Promise<Option[]> => {
        if (!inputValue) return [];

        const res = await fetch(`http://localhost/api/all/${type}?query=${inputValue}`);
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

    const selects: Array<SelectConfig> = [
        { id: "course", value: courseOptions, setValue: setCourseOptions },
        { id: "module", value: moduleOptions, setValue: setModuleOptions },
        { id: "location", value: locationOptions, setValue: setLocationOptions },
    ]

    async function fetchCalenar() {
        const courses = Array.from(courseOptions.map(o => o.value)).join(",");
        const modules = Array.from(moduleOptions.map(o => o.value)).join(",");
        const locations = Array.from(locationOptions.map(o => o.value)).join(",");

        if (!courses && !modules && !locations) {
            return []
        };

        const res = await fetch(`http://localhost/api/?courses=${courses}&modules=${modules}&locations=${locations}&format=json&display=true`);
        return await res.json();
    }

    useEffect(() => {
        const loadEvents = async () => {
            const data = await fetchCalenar();
            setEvents(parseCalendarJSON(data));
        };

        loadEvents();
    }, [courseOptions, moduleOptions, locationOptions]);

    return (
        <main>
            <Tabs>
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
                defaultView="week"
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
