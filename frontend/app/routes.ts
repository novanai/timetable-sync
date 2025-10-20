import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
    index("routes/home.tsx"),
    route("/timetable", "routes/timetable.tsx"),
] satisfies RouteConfig;
