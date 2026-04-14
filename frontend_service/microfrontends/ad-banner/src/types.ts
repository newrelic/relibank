export interface AdBannerProps {
  onSignUpClick?: () => void;
}

export interface MountOptions {
  containerId: string;
  onSignUpClick?: () => void;
}

/**
 * New Relic Scoped Agent Interface
 * Returned by window.newrelic.register()
 */
export interface NewRelicMFEAgent {
  setCustomAttribute: (name: string, value: string | number) => void;
  addPageAction: (name: string, attributes?: Record<string, any>) => void;
  noticeError: (error: Error, customAttributes?: Record<string, any>) => void;
  deregister: () => void;
  log: (message: string, options?: { level?: 'info' | 'warn' | 'error' }) => void;
  recordCustomEvent: (eventType: string, attributes?: Record<string, any>) => void;
  measure: (name: string, options?: { start?: number; end?: number }) => void;
  [key: string]: any;
}

declare global {
  interface Window {
    React: {
      createElement: any;
      useEffect: any;
      [key: string]: any;
    };
    ReactDOM: {
      createRoot: any;
      [key: string]: any;
    };
    MaterialUI: any;
    RelibankMicrofrontends?: {
      AdBanner?: {
        mount: (options: MountOptions) => () => void;
        agent?: NewRelicMFEAgent | null;
      };
    };
    newrelic?: {
      setCustomAttribute: (name: string, value: string | number) => void;
      interaction: () => {
        setName: (name: string) => any;
        setAttribute: (name: string, value: string) => any;
        save: () => void;
      };
      register: (config: {
        id: string;
        name: string;
        tags?: Record<string, string>;
      }) => NewRelicMFEAgent;
      addPageAction: (name: string, attributes?: Record<string, any>) => void;
    };
  }
}

export {};
