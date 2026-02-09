import {
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";

import { useState, createContext, useEffect, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { AppLayout } from '~/components/layout/AppLayout';

import nrScriptTemplate from "./nr.js?raw";

export const links = () => [
  { rel: "icon", href: "/relibank.png", type: "image/png" }
];

const NEW_RELIC_CONFIG = {
    // These values are hardcoded in nr.js
    // We'll use placeholders in the template and replace them here.
  ACCOUNT_ID: import.meta.env.VITE_NEW_RELIC_ACCOUNT_ID,
  BROWSER_APPLICATION_ID: import.meta.env.VITE_NEW_RELIC_BROWSER_APPLICATION_ID,
  LICENSE_KEY: import.meta.env.VITE_NEW_RELIC_LICENSE_KEY,
  TRUST_KEY: import.meta.env.VITE_NEW_RELIC_TRUST_KEY,
};

// Generate New Relic script with config values replaced
// This is computed once at module load since config values never change
const generateNrScript = () => {
    let script = nrScriptTemplate;

    script = script.replace(/accountID:"__ACCOUNT_ID__"/g, `accountID:"${NEW_RELIC_CONFIG.ACCOUNT_ID}"`);
    script = script.replace(/licenseKey:"__LICENSE_KEY__"/g, `licenseKey:"${NEW_RELIC_CONFIG.LICENSE_KEY}"`);
    script = script.replace(/applicationID:"__APPLICATION_ID__"/g, `applicationID:"${NEW_RELIC_CONFIG.BROWSER_APPLICATION_ID}"`);
    script = script.replace(/trustKey:"__TRUST_KEY__"/g, `trustKey:"${NEW_RELIC_CONFIG.TRUST_KEY}"`);

    return script;
};

// Pre-compute the NR script once at module load
const COMPUTED_NR_SCRIPT = generateNrScript();


// Create a context for login data
interface LoginContextType {
  isAuthenticated: boolean;
  handleLogin: (data: any) => void;
  handleLogout: () => void;
  userData: any;
  setUserData: (data: any) => void;
  browserUserId: string | null;
  setBrowserUserId: (id: string | null) => void;
}

export const LoginContext = createContext<LoginContextType>({
  isAuthenticated: false,
  handleLogin: () => {},
  handleLogout: () => {},
  userData: null,
  setUserData: () => {},
  browserUserId: null,
  setBrowserUserId: () => {},
});

// Create a context for the page data
export const PageContext = createContext({});


// Components have been extracted to separate files in app/components/layout/

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const isLoginPage = location.pathname === '/';

  // Initialize state as null to match server-side rendering
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userData, setUserData] = useState(null);
  const [isHydrated, setIsHydrated] = useState(false);
  const [browserUserId, setBrowserUserId] = useState<string | null>(null);

  const navigate = useNavigate();

  // Load from sessionStorage AFTER hydration to avoid mismatch
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedAuth = sessionStorage.getItem('isAuthenticated') === 'true';
      const storedUserData = sessionStorage.getItem('userData');

      setIsAuthenticated(storedAuth);

      if (storedUserData) {
        try {
          setUserData(JSON.parse(storedUserData));
        } catch (error) {
          console.error('Failed to parse userData from sessionStorage:', error);
          sessionStorage.removeItem('userData');
        }
      }

      setIsHydrated(true);
    }
  }, []);

  // Fetch browser user ID on app load
  useEffect(() => {
    if (typeof window !== 'undefined' && isHydrated) {
      // Check sessionStorage first
      const storedUserId = sessionStorage.getItem('browserUserId');
      if (storedUserId) {
        console.log('[Browser User] Loaded from sessionStorage:', storedUserId);
        setBrowserUserId(storedUserId);
        return;
      }

      // Fetch from API
      const fetchBrowserUserId = async () => {
        try {
          const response = await fetch('/accounts-service/browser-user');
          if (response.ok) {
            const data = await response.json();
            console.log(`[Browser User] Received: ${data.user_id} Source: ${data.source}`);
            setBrowserUserId(data.user_id);
            sessionStorage.setItem('browserUserId', data.user_id);
          } else {
            console.error('[Browser User] Failed to fetch user ID:', response.status);
          }
        } catch (error) {
          console.error('[Browser User] Error fetching user ID:', error);
        }
      };

      fetchBrowserUserId();
    }
  }, [isHydrated]);

  // Call New Relic setUserId when browserUserId changes
  useEffect(() => {
    if (typeof window !== 'undefined' && browserUserId) {
      if (window.newrelic && typeof window.newrelic.setUserId === 'function') {
        try {
          window.newrelic.setUserId(browserUserId);
          console.log('[New Relic] User ID set successfully:', browserUserId);
        } catch (error) {
          console.error('[New Relic] Failed to set user ID:', error);
        }
      } else {
        console.warn('[New Relic] Browser agent not available or setUserId method not found');
      }
    }
  }, [browserUserId]);

  // Wrapper to automatically sync to sessionStorage
  const updateUserData = (data: any) => {
    console.log('[Layout updateUserData] Updating userData:', data);
    setUserData(data);
    if (typeof window !== 'undefined') {
      if (data) {
        sessionStorage.setItem('userData', JSON.stringify(data));
      } else {
        sessionStorage.removeItem('userData');
      }
    }
  };

  const handleLogin = (data: any) => {
    console.log("[Layout handleLogin] Setting authentication data:", data);
    setIsAuthenticated(true);
    updateUserData(data);
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('isAuthenticated', 'true');
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    updateUserData(null);
    setBrowserUserId(null);
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('isAuthenticated');
      sessionStorage.removeItem('browserUserId');
    }
    navigate('/');
  };

  // Navigation effect
  useEffect(() => {
    console.log("[Layout] userData:", userData);
    console.log("[Layout] isAuthenticated:", isAuthenticated);
    if (isAuthenticated && !userData) {
      console.warn("Authenticated but no userData, logging out");
      handleLogout();
    } else if (isAuthenticated && userData) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, userData]);

  const contextValue = {
    isAuthenticated,
    handleLogin,
    handleLogout,
    userData,
    setUserData: updateUserData,
    browserUserId,
    setBrowserUserId
  };

  // The login page is a separate layout
  if (isLoginPage) {
    return (
      <html lang="en">
        <head>
          <script dangerouslySetInnerHTML={{ __html: COMPUTED_NR_SCRIPT }}></script>
          <meta charSet="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          {/* Prevent browser caching to avoid stale JS errors after Skaffold rebuilds.
              When Skaffold rebuilds the container, the browser may have cached the old index.html
              which references old JS file hashes that no longer exist after the build.
              This is for smoother development experience and can be safely removed in the future if needed. */}
          <meta httpEquiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
          <meta httpEquiv="Pragma" content="no-cache" />
          <meta httpEquiv="Expires" content="0" />
          <Meta />
          <Links />
        </head>
        <body>
          <LoginContext.Provider value={contextValue}>
            {children}
          </LoginContext.Provider>
          <ScrollRestoration />
          <Scripts />
        </body>
      </html>
    );
  }

  // All other pages will use the AppLayout wrapped in context
  return (
    <html lang="en">
      <head>
        <script dangerouslySetInnerHTML={{ __html: COMPUTED_NR_SCRIPT }}></script>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        {/* Prevent browser caching to avoid stale JS errors after Skaffold rebuilds.
            When Skaffold rebuilds the container, the browser may have cached the old index.html
            which references old JS file hashes that no longer exist after the build.
            This is for smoother development experience and can be safely removed in the future if needed. */}
        <meta httpEquiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
        <meta httpEquiv="Pragma" content="no-cache" />
        <meta httpEquiv="Expires" content="0" />
        <Meta />
        <Links />
      </head>
      <body>
        <LoginContext.Provider value={contextValue}>
          <AppLayout>
            {children}
          </AppLayout>
        </LoginContext.Provider>
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
};


export default function App() {
  // State management moved to Layout component
  // App just renders the Outlet for route content
  return <Outlet />;
}
