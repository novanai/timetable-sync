import type { Route } from "./+types/generator";
import { useState, useEffect, useMemo } from "react";
import AsyncSelect from 'react-select/async';
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import { FaClipboard } from "react-icons/fa";

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
    neutral20: "oklch(from var(--color-neutral-content) l c h / 0.25)",  // border, inner arrow
    // neutral30: "",  // border hover
    // neutral40: "",  // "no options" text
    neutral50: "var(--color-base-content)",  // text
    neutral60: "oklch(from var(--color-neutral-content) l c h / 0.25)",  // arrow active
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

const createLoadOptions = (group_type: string, category_type: string) => {
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
                    `/api/v3/${group_type}/category/${category_type}/items?query=${inputValue}`
                );
                const data = await res.json();

                callback(
                    data.map((item: any) => ({
                        label: item.name,
                        value: item.identity ?? item.id,
                    }))
                );
            } catch (e) {
                callback([]);
            }
        }, 300);
    };
};

const noOptionsMessage = (categoryType: string) => ({ inputValue }: { inputValue: string }) => {
    if (!inputValue) {
        return `Search for a ${categoryType}...`;
    }

    return `No ${categoryType} matching '${inputValue}'`;
};

export default function Timetable() {
    const [courseOptions, setCourseOptions] = useState<readonly Option[]>([]);
    const [moduleOptions, setModuleOptions] = useState<readonly Option[]>([]);
    const [locationOptions, setLocationOptions] = useState<readonly Option[]>([]);

    const [timetableURL, setTimetableURL] = useState<string>("");
    const [timetableCopied, setTimetableCopied] = useState<boolean>(false);

    const timetable_selects: Array<SelectConfig> = [
        { id: "course", value: courseOptions, setValue: setCourseOptions },
        { id: "module", value: moduleOptions, setValue: setModuleOptions },
        { id: "location", value: locationOptions, setValue: setLocationOptions },
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

    const handleCopy = async (elementId: string, setValue: React.Dispatch<React.SetStateAction<boolean>>) => {
        const el = document.getElementById(elementId);
        if (!el) return;

        try {
            await navigator.clipboard.writeText(el.innerText);
            setValue(true);
            setTimeout(() => setValue(false), 2000);
        } catch (err) {
            console.error("Copy failed", err);
        }
    };

    return (
        <div className="mx-4 md:mx-16 lg:mx-32">
            <h1 className="text-2xl font-bold mb-2">Timetable</h1>
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
                                placeholder={`Choose ${id}...`}
                                noOptionsMessage={noOptionsMessage(id)}
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
            <button
                className={`btn btn-sm mb-2 ${timetableCopied ? "btn-success" : "btn-primary"}`}
                onClick={() => handleCopy("timetable-url", setTimetableCopied)}
            >
                <span className="inline-flex items-center gap-1"><FaClipboard size={16} /> {timetableCopied ? "Copied!" : "Copy URL"}</span>
            </button>

            <button
                className="btn btn-sm mb-2 ml-2 btn-primary"
                onClick={() => window.open(`https://calendar.google.com/calendar/r?cid=${encodeURIComponent(timetableURL)}`, "_blank")}
            >
                <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 256 256" version="1.1" preserveAspectRatio="xMidYMid">
                    <g>
                        <polygon fill="#FFFFFF" points="195.368421 60.6315789 60.6315789 60.6315789 60.6315789 195.368421 195.368421 195.368421"></polygon>
                        <polygon fill="#EA4335" points="195.368421 256 256 195.368421 225.684211 190.196005 195.368421 195.368421 189.835162 223.098002"></polygon>
                        <path d="M1.42108547e-14,195.368421 L1.42108547e-14,235.789474 C1.42108547e-14,246.955789 9.04421053,256 20.2105263,256 L60.6315789,256 L66.8568645,225.684211 L60.6315789,195.368421 L27.5991874,190.196005 L1.42108547e-14,195.368421 Z" fill="#188038"></path>
                        <path d="M256,60.6315789 L256,20.2105263 C256,9.04421053 246.955789,1.42108547e-14 235.789474,1.42108547e-14 L195.368421,1.42108547e-14 C191.679582,15.0358547 189.835162,26.1010948 189.835162,33.1957202 C189.835162,40.2903456 191.679582,49.4356319 195.368421,60.6315789 C208.777986,64.4714866 218.883249,66.3914404 225.684211,66.3914404 C232.485172,66.3914404 242.590435,64.4714866 256,60.6315789 Z" fill="#1967D2"></path>
                        <polygon fill="#FBBC04" points="256 60.6315789 195.368421 60.6315789 195.368421 195.368421 256 195.368421"></polygon>
                        <polygon fill="#34A853" points="195.368421 195.368421 60.6315789 195.368421 60.6315789 256 195.368421 256"></polygon>
                        <path d="M195.368421,0 L20.2105263,0 C9.04421053,0 0,9.04421053 0,20.2105263 L0,195.368421 L60.6315789,195.368421 L60.6315789,60.6315789 L195.368421,60.6315789 L195.368421,0 Z" fill="#4285F4"></path>
                        <path d="M88.2694737,165.153684 C83.2336842,161.751579 79.7473684,156.783158 77.8442105,150.214737 L89.5326316,145.397895 C90.5936842,149.44 92.4463158,152.572632 95.0905263,154.795789 C97.7178947,157.018947 100.917895,158.113684 104.656842,158.113684 C108.48,158.113684 111.764211,156.951579 114.509474,154.627368 C117.254737,152.303158 118.635789,149.338947 118.635789,145.751579 C118.635789,142.08 117.187368,139.082105 114.290526,136.757895 C111.393684,134.433684 107.755789,133.271579 103.410526,133.271579 L96.6568421,133.271579 L96.6568421,121.701053 L102.72,121.701053 C106.458947,121.701053 109.608421,120.690526 112.168421,118.669474 C114.728421,116.648421 116.008421,113.886316 116.008421,110.366316 C116.008421,107.233684 114.863158,104.741053 112.572632,102.871579 C110.282105,101.002105 107.385263,100.058947 103.865263,100.058947 C100.429474,100.058947 97.7010526,100.968421 95.68,102.804211 C93.6602819,104.644885 92.1418208,106.968942 91.2673684,109.557895 L79.6968421,104.741053 C81.2294737,100.395789 84.0421053,96.5557895 88.1684211,93.2378947 C92.2947368,89.92 97.5663158,88.2526316 103.966316,88.2526316 C108.698947,88.2526316 112.96,89.1621053 116.732632,90.9978947 C120.505263,92.8336842 123.469474,95.3768421 125.608421,98.6105263 C127.747368,101.861053 128.808421,105.498947 128.808421,109.541053 C128.808421,113.667368 127.814737,117.153684 125.827368,120.016842 C123.84,122.88 121.397895,125.069474 118.501053,126.602105 L118.501053,127.292632 C122.241568,128.834789 125.490747,131.367752 127.898947,134.618947 C130.341053,137.903158 131.570526,141.827368 131.570526,146.408421 C131.570526,150.989474 130.408421,155.082105 128.084211,158.669474 C125.76,162.256842 122.543158,165.086316 118.467368,167.141053 C114.374737,169.195789 109.776842,170.240124 104.673684,170.240124 C98.7621053,170.256842 93.3052632,168.555789 88.2694737,165.153684 L88.2694737,165.153684 Z M160.067368,107.149474 L147.233684,116.429474 L140.816842,106.694737 L163.84,90.0884211 L172.665263,90.0884211 L172.665263,168.421053 L160.067368,168.421053 L160.067368,107.149474 Z" fill="#4285F4"></path>
                    </g>
                </svg>
                    Add to Google Calendar
            </button>
            <button
                className="btn btn-sm mb-2 ml-2 btn-primary"
                onClick={() => window.open(`webcal://${encodeURIComponent(timetableURL).replace(/^https?:\/\//i, '')}`, "_blank")}
            >
                <svg xmlns="http://www.w3.org/2000/svg" width="24px" height="24px" viewBox="0 0 24 24" fill="none">
                <path d="M3 9H21M7 3V5M17 3V5M6 12H10V16H6V12ZM6.2 21H17.8C18.9201 21 19.4802 21 19.908 20.782C20.2843 20.5903 20.5903 20.2843 20.782 19.908C21 19.4802 21 18.9201 21 17.8V8.2C21 7.07989 21 6.51984 20.782 6.09202C20.5903 5.71569 20.2843 5.40973 19.908 5.21799C19.4802 5 18.9201 5 17.8 5H6.2C5.0799 5 4.51984 5 4.09202 5.21799C3.71569 5.40973 3.40973 5.71569 3.21799 6.09202C3 6.51984 3 7.07989 3 8.2V17.8C3 18.9201 3 19.4802 3.21799 19.908C3.40973 20.2843 3.71569 20.5903 4.09202 20.782C4.51984 21 5.07989 21 6.2 21Z" stroke="#000000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                    Add to Apple Calendar
            </button>
            <button
                className="btn btn-sm mb-2 ml-2 btn-primary"
                onClick={() => window.open(`https://outlook.office.com/calendar/0/addfromweb?url=${encodeURIComponent(timetableURL)}`, "_blank")}
            >
                <svg xmlns="http://www.w3.org/2000/svg" width="24px" height="24px" viewBox="0 0 32 32">
                    <path d="M19.484,7.937v5.477L21.4,14.619a.489.489,0,0,0,.21,0l8.238-5.554a1.174,1.174,0,0,0-.959-1.128Z" fill="#0072c6"/>
                    <path d="M19.484,15.457l1.747,1.2a.522.522,0,0,0,.543,0c-.3.181,8.073-5.378,8.073-5.378V21.345a1.408,1.408,0,0,1-1.49,1.555H19.483V15.457Z" fill="#0072c6"/>
                    <path d="M10.44,12.932a1.609,1.609,0,0,0-1.42.838,4.131,4.131,0,0,0-.526,2.218A4.05,4.05,0,0,0,9.02,18.2a1.6,1.6,0,0,0,2.771.022,4.014,4.014,0,0,0,.515-2.2,4.369,4.369,0,0,0-.5-2.281A1.536,1.536,0,0,0,10.44,12.932Z" fill="#0072c6"/>
                    <path d="M2.153,5.155V26.582L18.453,30V2ZM13.061,19.491a3.231,3.231,0,0,1-2.7,1.361,3.19,3.19,0,0,1-2.64-1.318A5.459,5.459,0,0,1,6.706,16.1a5.868,5.868,0,0,1,1.036-3.616A3.267,3.267,0,0,1,10.486,11.1a3.116,3.116,0,0,1,2.61,1.321,5.639,5.639,0,0,1,1,3.484A5.763,5.763,0,0,1,13.061,19.491Z" fill="#0072c6"/>
                </svg>
                    Add to Outlook Calendar
            </button>

            <div id="timetable-url" className="mb-8">
                {timetableURL}
            </div>
        </div>
    );
}
