import type { Route } from "./+types/timetable";
import { useState, useRef } from "react";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import listPlugin from "@fullcalendar/list";
import iCalendarPlugin from "@fullcalendar/icalendar";
import momentTimezonePlugin from "@fullcalendar/moment-timezone";
import AsyncSelect from 'react-select/async';
import MultiValue from 'react-select';


// import ColorHash from 'color-hash';

// import * as ColorHashModule from "color-hash";
// const ColorHash = (ColorHashModule as any).default || (ColorHashModule as any).ColorHash;

import ColorHashModule from "color-hash";
const ColorHash = ColorHashModule.default || ColorHashModule;  // I don't know why this works

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

var colorHash = new ColorHash({ lightness: [0.6, 0.7, 0.8], saturation: [0.4, 0.5, 0.6] });

const loadOptions = async (inputValue: string): Promise<Option[]> => {
  if (!inputValue) return [];

  const res = await fetch(`http://localhost/api/all/course?query=${inputValue}`);
  const data = await res.json();

  return data.map((item: any) => ({
    label: item.name,
    value: item.identity,
  }));
};

export default function Timetable() {
  const [courseIds, setCourseIds] = useState(new Set<string>());
  const calendarRef = useRef<FullCalendar | null>(null);

  const handleSelectChange = (courseIdsSelection: MultiValue<Option>) => {
    let tempCourseIds: Set<string> = new Set(courseIdsSelection.map((option: Option) => option.value))

    function diffSets(oldSet: Set<string>, newSet: Set<string>) {
      const added = [...newSet].filter(x => !oldSet.has(x));
      const removed = [...oldSet].filter(x => !newSet.has(x));
      return { added, removed };
    }

    const diff = diffSets(courseIds, tempCourseIds);
    setCourseIds(tempCourseIds)
    
    diff.removed.map((courseId: string) => calendarRef.current?.getApi().getEventSourceById(courseId)?.remove())
    diff.added.map((courseId: string) => {calendarRef.current?.getApi().addEventSource({
      id: courseId,
      url: `http://localhost/api?courses=${courseId}`,
      format: "ics"
    })})
  };

  const setEventColour = (info) => {
    const colour = colorHash.hex(
      (info.event.title.split(" ")[0]),
    )
    info.el.style.backgroundColor = colour;
  }

  const renderEventContent = (arg) => {
     const { event } = arg;
    const { description, location } = event.extendedProps as {
      description?: string;
      location?: string;
    };

    return (
      <div>
        <strong>{event.title}</strong>
        {location && <div>{location}</div>}
        {description && (
          <div
            // style={{
            //   fontSize: 'smaller',
            //   color: 'gray',
            //   whiteSpace: 'pre-line',
            //   overflow: 'hidden',
            //   textOverflow: 'ellipsis',
            // }}
          >
            {description.split('\n').map((line, i) => (
              <span>
                {line}
                <br />
              </span>
            ))}
          </div>
        )}
      </div>
    );
  }


  return (
    <main>
      <AsyncSelect
        isMulti
        name="course-select"
        cacheOptions
        loadOptions={loadOptions}
        defaultOptions
        onChange={handleSelectChange}
        menuPortalTarget={typeof document !== "undefined" ? document.body : null}  // bc of ssr
        styles={{
          menuPortal: base => ({ ...base, zIndex: 9999 })
        }}
      />

      <FullCalendar
        ref={calendarRef}
        plugins={[timeGridPlugin, listPlugin, momentTimezonePlugin, iCalendarPlugin]}
        initialView="timeGridWeek"
        headerToolbar={{
          left: "prev,next today",
          center: "title",
          right: "timeGridWeek,timeGridDay,listWeek",
        }}
        height="80vh"
        locale="en-GB"
        timeZone="Europe/Dublin"
        slotLabelFormat={{
            hour: "numeric",
            minute: "numeric"
        }}
        allDaySlot={false}
        weekends={true}
        slotMinTime="08:00:00"
        slotMaxTime="19:00:00"
        editable={false}
        firstDay={1} // Monday
        nowIndicator={true}
        slotDuration="01:00:00"
        expandRows={true}
        eventDidMount={setEventColour}
        eventContent={renderEventContent}
        eventTextColor={"#000"}
        eventBorderColor={"#0000"}
      />
    </main>
  );
}
