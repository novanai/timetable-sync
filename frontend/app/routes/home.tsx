import { Link } from "react-router";
import type { Route } from "./+types/home";

export function meta({ }: Route.MetaArgs) {
  return [
    { title: "New React Router App" },
    { name: "description", content: "Welcome to React Router!" },
  ];
}

export default function Home() {
  return (
    <div className="mx-4 md:mx-16 lg:mx-32 text-ellipsis overflow-hidden">
      <h1 className="text-primary text-2xl font-semibold mb-2">
        Add to Google Calendar
      </h1>
      <ol className="list-decimal ml-5 mb-3">
        <li>
          On your computer, open <Link to="https://calendar.google.com/" className="text-secondary link link-hover">Google Calendar</Link>
        </li>
        <li>Go to Settings &gt; Add Calendar &gt; From URL</li>
        <li>
          Enter the calendar's address, which you can <Link to="/generator" className="text-secondary link link-hover">generate here</Link>
        </li>
      </ol>
      <p className="mb-3">To make sure you calendar syncs on mobile devices:</p>
      <ul className="list-disc ml-8">
        <li>
          On Android devices: open Google Calendar, go to settings, select the
          calendar and enable the "Sync" option
        </li>
        <li>
          On Apple devices: go to
          <Link to="https://calendar.google.com/calendar/syncselect" className="text-secondary link link-hover">https://calendar.google.com/calendar/syncselect</Link>, 
          select the calendar(s) you want to sync, and then save
        </li>
      </ul>
      <br />

      <h1 className="text-primary text-2xl font-semibold mb-2">
        Add to Apple Calendar
      </h1>
      <ol className="list-decimal ml-5 mb-3">
        <li>On your Apple device, open the Calendar app</li>
        <li>
          Go to Calendars &gt; Add Calendar &gt; Add Subscription Calendar
        </li>
        <li>
          Enter the calendar's address, which you can
          <Link to="/generator" className="text-secondary link link-hover">generate here</Link>,
          and then click "Subscribe"
        </li>
      </ol>
      <br />

      <h1 className="text-primary text-2xl font-semibold mb-2">
        Download an iCal file
      </h1>
      <p>
        If you want to download an iCal file, just go to the calendar's address, which you can
        <Link to="/generator" className="text-secondary link link-hover">generate here</Link>,
        and download the generated iCal file when prompted.
      </p>
    </div>
  );
}
