# Migration to New Relic `.register()` API - Code Comparison

This document shows the exact code changes made to migrate from manual New Relic tracking to the official `.register()` API.

---

## File 1: `src/constants.ts` (NEW FILE)

**Purpose**: Define stable MFE configuration

```typescript
/**
 * New Relic Microfrontend Configuration
 *
 * This UUID must remain stable across deployments to maintain entity identity in New Relic.
 * Generate once using: uuidgen or https://www.uuidgenerator.net/
 */
export const AD_BANNER_MFE_CONFIG = {
  id: '550e8400-e29b-41d4-a716-446655440000',
  name: 'Ad Banner MFE',
  version: '1.0.0',
  tags: {
    team: 'marketing',
    type: 'promotion',
    feature: 'rewards-signup'
  }
} as const;
```

**Key Points**:
- UUID is generated once and never changes
- All MFE configuration centralized in one place
- Tags allow grouping/filtering in New Relic

---

## File 2: `src/types.ts`

### Added: Scoped Agent Interface

```typescript
/**
 * New Relic Scoped Agent Interface
 * Returned by window.newrelic.register()
 */
export interface NewRelicMFEAgent {
  setCustomAttribute: (name: string, value: string | number) => void;
  addPageAction: (name: string, attributes?: Record<string, any>) => void;
  noticeError: (error: Error, customAttributes?: Record<string, any>) => void;
  deregister: () => void;
  [key: string]: any;
}
```

### Updated: Window Interface

**Before**:
```typescript
RelibankMicrofrontends?: {
  AdBanner?: {
    mount: (options: MountOptions) => () => void;
  };
};
newrelic?: {
  setCustomAttribute: (name: string, value: string | number) => void;
  interaction: () => {
    setName: (name: string) => any;
    setAttribute: (name: string, value: string) => any;
    save: () => void;
  };
};
```

**After**:
```typescript
RelibankMicrofrontends?: {
  AdBanner?: {
    mount: (options: MountOptions) => () => void;
    agent?: NewRelicMFEAgent | null;  // ← Added
  };
};
newrelic?: {
  setCustomAttribute: (name: string, value: string | number) => void;
  interaction: () => {
    setName: (name: string) => any;
    setAttribute: (name: string, value: string) => any;
    save: () => void;
  };
  register: (config: {  // ← Added
    id: string;
    name: string;
    tags?: Record<string, string>;
  }) => NewRelicMFEAgent;
  addPageAction: (name: string, attributes?: Record<string, any>) => void;  // ← Added
};
```

---

## File 3: `src/index.tsx`

### Change 1: Imports

**Before**:
```typescript
import AdBanner from './AdBanner';
import type { MountOptions } from './types';
import './types';
```

**After**:
```typescript
import AdBanner from './AdBanner';
import type { MountOptions, NewRelicMFEAgent } from './types';  // ← Added type
import { AD_BANNER_MFE_CONFIG } from './constants';  // ← New import
import './types';
```

### Change 2: Registration Logic in `mountAdBanner()`

**Before**:
```typescript
export function mountAdBanner(options: MountOptions): () => void {
  console.log('[AdBanner Mount] Starting mount with options:', options);

  // Track microfrontend load with New Relic
  if (window.newrelic?.interaction) {
    try {
      window.newrelic.interaction()
        .setName('Microfrontend: Ad Banner Mount')
        .setAttribute('microfrontend', 'ad-banner')
        .save();
      console.log('[AdBanner Mount] New Relic interaction tracked');
    } catch (error) {
      console.error('[AdBanner Mount] Failed to track New Relic interaction:', error);
    }
  }

  // Mount React component...
```

**After**:
```typescript
export function mountAdBanner(options: MountOptions): () => void {
  console.log('[AdBanner Mount] Starting mount with options:', options);

  let mfeAgent: NewRelicMFEAgent | null = null;

  // Register with New Relic using the official .register() API
  if (window.newrelic?.register) {
    try {
      mfeAgent = window.newrelic.register({
        id: AD_BANNER_MFE_CONFIG.id,
        name: AD_BANNER_MFE_CONFIG.name,
        tags: AD_BANNER_MFE_CONFIG.tags
      });

      // Set MFE-specific attributes using scoped agent
      mfeAgent.setCustomAttribute('version', AD_BANNER_MFE_CONFIG.version);
      mfeAgent.setCustomAttribute('containerId', options.containerId);

      console.log('[AdBanner Mount] Registered with New Relic:', {
        id: AD_BANNER_MFE_CONFIG.id,
        name: AD_BANNER_MFE_CONFIG.name
      });
    } catch (error) {
      console.error('[AdBanner Mount] Failed to register with New Relic:', error);
      mfeAgent = null;
    }
  } else {
    console.warn('[AdBanner Mount] New Relic .register() API not available');
  }

  // Mount React component...
```

**Key Changes**:
- Store scoped agent in `mfeAgent` variable
- Use `.register()` instead of `.interaction()`
- Set custom attributes on scoped agent
- Better error handling and logging

### Change 3: Store Agent Globally (NEW)

**Added before rendering** (inserted after root creation, before `root.render()`):

```typescript
// Store scoped agent globally for component to access
if (mfeAgent) {
  window.RelibankMicrofrontends = {
    ...window.RelibankMicrofrontends,
    AdBanner: {
      mount: mountAdBanner,
      agent: mfeAgent  // ← Store scoped agent
    }
  };
}
```

**Purpose**: Make scoped agent accessible to component for event tracking

### Change 4: Deregistration on Unmount

**Before** (unmount logic):
```typescript
if (newCount <= 0) {
  console.log('[AdBanner Mount] Unmounting component - no more active mounts');
  try {
    const rootToUnmount = rootsMap.get(options.containerId);
    if (rootToUnmount) {
      rootToUnmount.unmount();
      rootsMap.delete(options.containerId);
      mountCountsMap.delete(options.containerId);
      console.log('[AdBanner Mount] Root unmounted and removed from map');
    }
  } catch (error) {
    console.error('[AdBanner Mount] Failed to unmount:', error);
  }
}
```

**After** (unmount logic):
```typescript
if (newCount <= 0) {
  console.log('[AdBanner Mount] Unmounting component - no more active mounts');
  try {
    const rootToUnmount = rootsMap.get(options.containerId);
    if (rootToUnmount) {
      rootToUnmount.unmount();
      rootsMap.delete(options.containerId);
      mountCountsMap.delete(options.containerId);
      console.log('[AdBanner Mount] Root unmounted and removed from map');
    }
  } catch (error) {
    console.error('[AdBanner Mount] Failed to unmount:', error);
  }

  // Deregister from New Relic
  if (mfeAgent?.deregister) {
    try {
      mfeAgent.deregister();
      console.log('[AdBanner Mount] Deregistered from New Relic');

      // Clear agent from global state
      if (window.RelibankMicrofrontends?.AdBanner) {
        window.RelibankMicrofrontends.AdBanner.agent = null;
      }
    } catch (error) {
      console.error('[AdBanner Mount] Failed to deregister from New Relic:', error);
    }
  }
}
```

**Key Changes**:
- Call `.deregister()` on cleanup
- Clear agent from global state
- Proper error handling

---

## File 4: `src/AdBanner.tsx`

### Complete Before/After

**Before** (lines 1-37):
```typescript
import type { AdBannerProps } from './types';

const AdBanner = ({ onSignUpClick }: AdBannerProps) => {
  const { useEffect } = window.React;
  const { Card, Box, Typography, Button } = window.MaterialUI;

  // Track microfrontend load with New Relic
  useEffect(() => {
    if (window.newrelic) {
      try {
        window.newrelic.setCustomAttribute('microfrontendName', 'ad-banner');
        window.newrelic.setCustomAttribute('componentType', 'microfrontend');
        console.log('[AdBanner] New Relic custom attributes set');
      } catch (error) {
        console.error('[AdBanner] Failed to set New Relic attributes:', error);
      }
    }
  }, []);

  // Track button clicks as SPA interactions
  const handleSignUpClick = () => {
    if (window.newrelic?.interaction) {
      try {
        window.newrelic.interaction()
          .setName('AdBanner: Sign Up Clicked')
          .setAttribute('microfrontend', 'ad-banner')
          .save();
        console.log('[AdBanner] Sign up click tracked in New Relic');
      } catch (error) {
        console.error('[AdBanner] Failed to track sign up click:', error);
      }
    }

    if (onSignUpClick) {
      onSignUpClick();
    }
  };

  return (
    // ... JSX ...
  );
};
```

**After** (lines 1-29):
```typescript
import type { AdBannerProps } from './types';

const AdBanner = ({ onSignUpClick }: AdBannerProps) => {
  const { Card, Box, Typography, Button } = window.MaterialUI;

  // Track button clicks using scoped New Relic agent
  const handleSignUpClick = () => {
    // Access scoped agent from global state
    const mfeAgent = window.RelibankMicrofrontends?.AdBanner?.agent;

    if (mfeAgent?.addPageAction) {
      try {
        mfeAgent.addPageAction('adBannerSignUpClicked', {
          buttonId: 'dashboard-rewards-signup-btn',
          feature: 'rewards-signup',
          location: 'dashboard'
        });
        console.log('[AdBanner] Sign up click tracked via scoped agent');
      } catch (error) {
        console.error('[AdBanner] Failed to track click:', error);
      }
    } else {
      console.warn('[AdBanner] New Relic scoped agent not available for tracking');
    }

    if (onSignUpClick) {
      onSignUpClick();
    }
  };

  return (
    // ... JSX unchanged ...
  );
};
```

**Key Changes**:
1. **Removed**: `useEffect` hook that set custom attributes
   - Attributes now set during registration in mount function
2. **Removed**: `window.React.useEffect` import
3. **Changed**: Event tracking method
   - From: `window.newrelic.interaction().setName(...).save()`
   - To: `mfeAgent.addPageAction('eventName', { attributes })`
4. **Changed**: Event name
   - From: "AdBanner: Sign Up Clicked"
   - To: "adBannerSignUpClicked" (camelCase for consistency)
5. **Added**: More detailed attributes (buttonId, feature, location)

---

## Summary of Changes

### What Was Removed
- ❌ Manual `useEffect` setting custom attributes
- ❌ Global `window.newrelic.setCustomAttribute()` calls
- ❌ Manual `interaction().setName().save()` pattern

### What Was Added
- ✅ Centralized MFE configuration (`constants.ts`)
- ✅ Scoped agent types (`NewRelicMFEAgent` interface)
- ✅ `.register()` API call on mount
- ✅ `.deregister()` API call on unmount
- ✅ Scoped agent stored globally
- ✅ `addPageAction()` for event tracking
- ✅ Better error handling and logging

### Benefits
- ✅ Proper entity creation in New Relic
- ✅ Automatic performance metrics
- ✅ Scoped data collection
- ✅ Cleaner component code (no useEffect)
- ✅ Better maintainability

### Backward Compatibility
- ✅ No changes to host application required
- ✅ Same mount/unmount API
- ✅ Graceful degradation if `.register()` not available

---

## Migration Pattern for Other Microfrontends

To migrate other microfrontends to this pattern:

1. **Create `constants.ts`**
   - Generate new UUID (don't reuse)
   - Define name, version, tags

2. **Update `types.ts`**
   - Add `NewRelicMFEAgent` interface
   - Update `Window` interface

3. **Update mount function**
   - Call `.register()` at start
   - Store scoped agent globally
   - Set custom attributes on agent

4. **Update unmount function**
   - Call `.deregister()` at end
   - Clear agent from global state

5. **Update component**
   - Remove manual `setCustomAttribute` calls
   - Use `mfeAgent.addPageAction()` for events
   - Access agent from global state

6. **Test**
   - Verify console logs
   - Check entity creation in New Relic
   - Validate NRQL queries

---

## Testing Quick Reference

### Console Logs to Look For

**Success**:
```
✓ [AdBanner Mount] Registered with New Relic: {id: "550e8400...", name: "Ad Banner MFE"}
✓ [AdBanner Mount] Component rendered successfully
✓ [AdBanner] Sign up click tracked via scoped agent
✓ [AdBanner Mount] Deregistered from New Relic
```

**Configuration Issue**:
```
⚠ [AdBanner Mount] New Relic .register() API not available
```

### NRQL Query to Verify

```sql
SELECT * FROM MicroFrontEndTiming
WHERE entityGuid LIKE '%550e8400-e29b-41d4-a716-446655440000%'
SINCE 1 hour ago
```

Should return rows with `timeToLoad`, `timeToRegister`, `timeAlive`.

---

## Next Steps

1. Enable register API in container agent
2. Deploy the build
3. Test in browser
4. Verify in New Relic UI
5. Monitor for 24 hours
6. Apply pattern to other microfrontends
