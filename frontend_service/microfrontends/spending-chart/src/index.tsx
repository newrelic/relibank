import SpendingChart from './SpendingChart';
import type { MountOptions, NewRelicMFEAgent } from './types';
import { SPENDING_CHART_MFE_CONFIG } from './constants';
import './types'; // Import for global type augmentation

// Track roots by container ID to avoid creating multiple roots
const rootsMap = new Map<string, any>();
// Track mount counts to handle React Strict Mode double mounting
const mountCountsMap = new Map<string, number>();

export function mountSpendingChart(options: MountOptions): () => void {
  console.log('[SpendingChart Mount] Starting mount with options:', options);

  let mfeAgent: NewRelicMFEAgent | null = null;

  // Register with New Relic using the official .register() API
  if (window.newrelic?.register) {
    try {
      mfeAgent = window.newrelic.register({
        id: SPENDING_CHART_MFE_CONFIG.id,
        name: SPENDING_CHART_MFE_CONFIG.name,
        tags: SPENDING_CHART_MFE_CONFIG.tags
      });

      // Set MFE-specific attributes using scoped agent
      mfeAgent.setCustomAttribute('version', SPENDING_CHART_MFE_CONFIG.version);
      mfeAgent.setCustomAttribute('containerId', options.containerId);

      console.log('[SpendingChart Mount] Registered with New Relic:', {
        id: SPENDING_CHART_MFE_CONFIG.id,
        name: SPENDING_CHART_MFE_CONFIG.name
      });
    } catch (error) {
      console.error('[SpendingChart Mount] Failed to register with New Relic:', error);
      mfeAgent = null;
    }
  } else {
    console.warn('[SpendingChart Mount] New Relic .register() API not available');
  }

  // Mount React component
  const container = document.getElementById(options.containerId);

  if (!container) {
    console.error(`[SpendingChart Mount] Container with id "${options.containerId}" not found`);
    return () => {
      console.warn('[SpendingChart Mount] Nothing to unmount - container was never found');
    };
  }

  // Increment mount count
  const currentCount = mountCountsMap.get(options.containerId) || 0;
  mountCountsMap.set(options.containerId, currentCount + 1);

  // Check if a root already exists for this container
  let root = rootsMap.get(options.containerId);

  if (!root) {
    // Create a new root only if one doesn't exist
    root = window.ReactDOM.createRoot(container);
    rootsMap.set(options.containerId, root);
    console.log('[SpendingChart Mount] Created new root for container:', options.containerId);
  } else {
    console.log('[SpendingChart Mount] Reusing existing root for container:', options.containerId);
  }

  // Store scoped agent globally for component to access
  if (mfeAgent) {
    window.RelibankMicrofrontends = {
      ...window.RelibankMicrofrontends,
      SpendingChart: {
        mount: mountSpendingChart,
        agent: mfeAgent
      }
    };
  }

  try {
    root.render(
      window.React.createElement(SpendingChart, {
        data: options.data
      })
    );
    console.log('[SpendingChart Mount] Component rendered successfully');
  } catch (error) {
    console.error('[SpendingChart Mount] Failed to render component:', error);
  }

  // Return unmount function
  return () => {
    console.log('[SpendingChart Mount] Cleanup called');

    // Decrement mount count
    const count = mountCountsMap.get(options.containerId) || 0;
    const newCount = count - 1;

    if (newCount <= 0) {
      // Only unmount if no more active mounts
      console.log('[SpendingChart Mount] Unmounting component - no more active mounts');
      try {
        const rootToUnmount = rootsMap.get(options.containerId);
        if (rootToUnmount) {
          rootToUnmount.unmount();
          rootsMap.delete(options.containerId);
          mountCountsMap.delete(options.containerId);
          console.log('[SpendingChart Mount] Root unmounted and removed from map');
        }
      } catch (error) {
        console.error('[SpendingChart Mount] Failed to unmount:', error);
      }

      // Deregister from New Relic
      if (mfeAgent?.deregister) {
        try {
          mfeAgent.deregister();
          console.log('[SpendingChart Mount] Deregistered from New Relic');

          // Clear agent from global state
          if (window.RelibankMicrofrontends?.SpendingChart) {
            window.RelibankMicrofrontends.SpendingChart.agent = null;
          }
        } catch (error) {
          console.error('[SpendingChart Mount] Failed to deregister from New Relic:', error);
        }
      }
    } else {
      // Still have active mounts, just decrement count
      mountCountsMap.set(options.containerId, newCount);
      console.log(`[SpendingChart Mount] Still ${newCount} active mount(s), keeping root alive`);
    }
  };
}

// Expose globally for host consumption
if (typeof window !== 'undefined') {
  window.RelibankMicrofrontends = {
    ...window.RelibankMicrofrontends,
    SpendingChart: { mount: mountSpendingChart }
  };
  console.log('[SpendingChart] Global API exposed on window.RelibankMicrofrontends.SpendingChart');
}
