import type { OpenAsBlobOptions } from "node:fs";
import type { Route } from "./+types/generator";
import { useState, useEffect, useMemo } from "react";
import AsyncSelect from 'react-select/async';
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';

export function meta({ }: Route.MetaArgs) {
    return [
        { title: "Timetable URL Generator | TimetableSync" },
        { name: "description", content: "Generate your timetable URL." },
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
category_type_mapping.set("society", "society")
category_type_mapping.set("club", "club")

const createLoadOptions = (group_type: string, category_type: string) => {
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
                    `/api/v3/${group_type}/category/${category_type_id}/items?query=${inputValue}`
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



export default function Timetable() {
    const [courseOptions, setCourseOptions] = useState<readonly Option[]>([]);
    const [moduleOptions, setModuleOptions] = useState<readonly Option[]>([]);
    const [locationOptions, setLocationOptions] = useState<readonly Option[]>([]);
    const [clubOptions, setClubOptions] = useState<readonly Option[]>([]);
    const [societyOptions, setSocietyOptions] = useState<readonly Option[]>([]);

    const [timetableURL, setTimetableURL] = useState<string>("");
    const [cnsURL, setCnsURL] = useState<string>("");

    const timetable_selects: Array<SelectConfig> = [
        { id: "course", value: courseOptions, setValue: setCourseOptions },
        { id: "module", value: moduleOptions, setValue: setModuleOptions },
        { id: "location", value: locationOptions, setValue: setLocationOptions },
    ]

    const cns_selects: Array<SelectConfig> = [
        { id: "club", value: clubOptions, setValue: setClubOptions },
        { id: "society", value: societyOptions, setValue: setSocietyOptions },
    ]

    useEffect(() => {
        const params = new URLSearchParams();

        timetable_selects.map(({ id, value }) => {
            value.map(({ value }) => {
                params.append(id, value);
            })
        })


        setTimetableURL(`${window.location.protocol}//${window.location.hostname}/api/v3/timetable/events?${params.toString()}`)
    }, [courseOptions, moduleOptions, locationOptions]);

    useEffect(() => {
        const params = new URLSearchParams();

        cns_selects.map(({ id, value }) => {
            value.map(({ value }) => {
                params.append(id, value);
            })
        })


        setCnsURL(`${window.location.protocol}//${window.location.hostname}/api/v3/cns/events?${params.toString()}`)
    }, [clubOptions, societyOptions]);

    return (
        <main>
            <Tabs className="mb-4">
                <TabList>
                    {/* TODO: should be a map from selects */}
                    <Tab>Courses</Tab>
                    <Tab>Modules</Tab>
                    <Tab>Locations</Tab>
                </TabList>

                {timetable_selects.map(({ id, value, setValue }) => {
                    const loadOptions = useMemo(
                        () => createLoadOptions("timetable", id),
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
            <div>
                {timetableURL}
            </div>

            <Tabs className="mb-4">
                <TabList>
                    <Tab>Clubs</Tab>
                    <Tab>Societies</Tab>
                </TabList>

                {cns_selects.map(({ id, value, setValue }) => {
                    const loadOptions = useMemo(
                        () => createLoadOptions("cns", id),
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
            <div>
                {cnsURL}
            </div>
        </main>
    );
}
