import {
  isRouteErrorResponse,
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";

import { AppLayout } from "./routes/dashboard";
import type { Route } from "./+types/root";
import "./app.css";

// import { BrowserAgent } from '@newrelic/browser-agent/loaders/browser-agent'
// Remaining import statements

// Populate using values from NerdGraph  
// const options = {
//   init: {distributed_tracing:{enabled:true},privacy:{cookies_enabled:true},ajax:{deny_list:["bam.nr-data.net"]}},
//   info: {beacon:"bam.nr-data.net",errorBeacon:"bam.nr-data.net",licenseKey:"NRJS-db2effc5142caf367f4",applicationID:"1134616390",sa:1},
//   loader_config: {accountID:"4182956",trustKey:"4120837",agentID:"1134616390",licenseKey:"NRJS-db2effc5142caf367f4",applicationID:"1134616390"}
// } 

// The agent loader code executes immediately on instantiation. 
// new BrowserAgent(options)

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <script src="./newrelic.js"></script>
        <Meta />
        <Links />
      </head>
      <body>
        <AppLayout>
          {children}
        </AppLayout>
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

export default function App() {
  return <Outlet />;
}
