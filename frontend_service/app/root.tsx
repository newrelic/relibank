import {
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";

import { useState, createContext, useEffect } from 'react';
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
};

const generateNrScript = () => {
    let script = nrScriptTemplate;

    script = script.replace(/accountID:"__ACCOUNT_ID__"/g, `accountID:"${NEW_RELIC_CONFIG.ACCOUNT_ID}"`);
    script = script.replace(/licenseKey:"__LICENSE_KEY__"/g, `licenseKey:"${NEW_RELIC_CONFIG.LICENSE_KEY}"`);
    script = script.replace(/applicationID:"__APPLICATION_ID__"/g, `applicationID:"${NEW_RELIC_CONFIG.BROWSER_APPLICATION_ID}"`);

    return script;
};


// Create a context for login data
interface LoginContextType {
  isAuthenticated: boolean;
  handleLogin: (data: any) => void;
  handleLogout: () => void;
  userData: any;
  setUserData: (data: any) => void;
}

export const LoginContext = createContext<LoginContextType>({
  isAuthenticated: false,
  handleLogin: () => {},
  handleLogout: () => {},
  userData: null,
  setUserData: () => {},
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
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('isAuthenticated');
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

  const dynamicNrScriptContent = generateNrScript();

  const contextValue = {
    isAuthenticated,
    handleLogin,
    handleLogout,
    userData,
    setUserData: updateUserData
  };

  // The login page is a separate layout
  if (isLoginPage) {
    return (
      <html lang="en">
        <head>
          <script dangerouslySetInnerHTML={{ __html: dynamicNrScriptContent }}></script>
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
        <script dangerouslySetInnerHTML={{ __html: dynamicNrScriptContent }}></script>
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
