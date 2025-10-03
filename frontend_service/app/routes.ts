import { type RouteConfig, index, route } from "@react-router/dev/routes";
import type { LoaderFunctionArgs } from "react-router";

export default [
    // The index route is now the login page
    index("routes/login.tsx"),
    // The dashboard is on its own dedicated route
    route("/dashboard", "routes/dashboard.tsx"),
    // The new support/chat route
    route("/support", "routes/support.tsx"),
] satisfies RouteConfig;
