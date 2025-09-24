import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
    // The index route is now the login page
    index("routes/login.tsx"),
    // The dashboard is on its own dedicated route
    route("/dashboard", "routes/dashboard.tsx"),
    // Other pages are also dedicated routes
    // route("/accounts", "routes/dashboard.tsx"),
    // route("/accounts/:accountId", "routes/dashboard.tsx"),
    // route("/settings", "routes/dashboard.tsx"),
] satisfies RouteConfig;
