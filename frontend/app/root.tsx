import type { Route } from "./+types/root";
import { useEffect } from 'react';
import { themeChange } from 'theme-change';
import {
  isRouteErrorResponse,
  Links,
  Meta,
  NavLink,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";
import { FaSun, FaMoon, FaGithub } from 'react-icons/fa';
import { MdOutlineKeyboardArrowDown } from "react-icons/md";
import "./app.css";

export const links: Route.LinksFunction = () => [
  { rel: "preconnect", href: "https://fonts.googleapis.com" },
  {
    rel: "preconnect",
    href: "https://fonts.gstatic.com",
    crossOrigin: "anonymous",
  },
  {
    rel: "stylesheet",
    href: "https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap",
  },
];

const pages = [
  { name: "Home", path: "/", external: false },
  { name: "Timetable Viewer", path: "/timetable", external: false },
  { name: "Timetable Generator", path: "/generator", external: false },
  { name: "API Documentation", path: "/api/docs", external: true },
]

const themes = [
  {
    group: "Light",
    icon: <FaSun size={48} />,
    themeList: [
      { name: "Blue", value: "winter" },
      { name: "Yellow", value: "bumblebee" },
      { name: "Green", value: "emerald" },
    ],
  },
  {
    group: "Dark",
    icon: <FaMoon size={48} />,
    themeList: [
      { name: "Blue", value: "night" },
      { name: "Pink", value: "dracula" },
      { name: "Green", value: "forest" },
    ],
  },
]

export function Layout({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    themeChange(false)
  }, []);

  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <Meta />
        <Links />
      </head>
      <body>
        <div className="min-h-screen flex flex-col bg-base-100">
          <div className="navbar">
            <div className="navbar-start">
              <div className="dropdown">
                <div tabIndex={0} role="button" className="btn btn-ghost lg:hidden hover:bg-base-300 border-none">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-5 w-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M4 6h16M4 12h8m-8 6h16"
                    />
                  </svg>
                </div>
                <ul
                  tabIndex={0}
                  className="menu menu-sm dropdown-content bg-base-100 rounded-box z-[1] mt-3 w-52 p-2 shadow"
                >
                  {pages.map((page) => (
                    <li key={page.path}>
                      {page.external ? (
                        <a
                          href={page.path}
                          className="hover:text-primary"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {page.name}
                        </a>
                      ) : (
                        <NavLink
                          to={page.path}
                          className={({ isActive }) =>
                            isActive ? "text-primary font-bold" : "hover:text-primary"
                          }
                        >
                          {page.name}
                        </NavLink>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
              <a className="btn btn-ghost text-xl hover:bg-base-300 border-none" href="/">TimetableSync</a>
            </div>
            <div className="navbar-center hidden lg:flex">
              <ul className="menu menu-horizontal">
                {pages.map((page) => (
                  <li key={page.path}>
                    {page.external ? (
                      <a
                        href={page.path}
                        className="hover:text-primary"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {page.name}
                      </a>
                    ) : (
                      <NavLink
                        to={page.path}
                        className={({ isActive }) =>
                          isActive ? "text-primary font-bold" : "hover:text-primary"
                        }
                      >
                        {page.name}
                      </NavLink>
                    )}
                  </li>
                ))}
              </ul>
            </div>
            <div className="navbar-end">
              <a href="https://github.com/novanai/timetable-sync" target="_blank" className="btn btn-ghost border-none hover:text-primary hover:bg-inherit hover:shadow-none">
                <FaGithub size={28} />
              </a>
              <div className="dropdown dropdown-end">
                <div tabIndex={0} role="button" className="btn hover:bg-base-300 border-none m-1">
                  Theme
                  <MdOutlineKeyboardArrowDown />
                </div>
                <ul tabIndex={-1} className="dropdown-content bg-base-300 rounded-box z-1 w-52 p-2 shadow-2xl">
                  {themes.map(({ group, icon, themeList }) => (
                    <div key={group}>
                      <div className="divider gap-1">
                        {icon}
                        <span>{group}</span>
                      </div>

                      {themeList.map(({ name, value }) => (
                        <li key={value}>
                          <label className="btn btn-sm btn-block btn-ghost justify-start has-[input:checked]:bg-base-100">
                            <input
                              type="radio"
                              name="theme-dropdown"
                              className="theme-controller hidden"
                              aria-label={name}
                              data-set-theme={value}
                            />

                            <span
                              data-theme={value}
                              className="w-3 h-3 rounded-full bg-primary"
                            />

                            <span>{name}</span>
                          </label>
                        </li>
                      ))}
                    </div>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          <div className="flex-1 m-4">
            {children}
          </div>

          <div className="footer footer-center bg-primary text-primary-content p-4">
            <div>
              <p>
                Made with ❤️ by <a href="https://github.com/novanai" className="link link-hover">nova</a>
              </p>
              <p>
                Powered by <a href="https://redbrick.dcu.ie" className="link link-hover">Redbrick</a>
              </p>
            </div>
          </div>
        </div>

        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

export default function App() {
  return <Outlet />;
}

export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  let message = "Oops!";
  let details = "An unexpected error occurred.";
  let stack: string | undefined;

  if (isRouteErrorResponse(error)) {
    message = error.status === 404 ? "404" : "Error";
    details =
      error.status === 404
        ? "The requested page could not be found."
        : error.statusText || details;
  } else if (import.meta.env.DEV && error && error instanceof Error) {
    details = error.message;
    stack = error.stack;
  }

  return (
    <main className="pt-16 p-4 container mx-auto">
      <h1>{message}</h1>
      <p>{details}</p>
      {stack && (
        <pre className="w-full p-4 overflow-x-auto">
          <code>{stack}</code>
        </pre>
      )}
    </main>
  );
}
