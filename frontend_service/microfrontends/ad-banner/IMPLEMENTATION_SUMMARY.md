# New Relic `.register()` API Implementation Summary

## Implementation Completed ✅

Successfully implemented New Relic's official `.register()` API for the Ad Banner microfrontend following the documented pattern.

---

## Changes Made

### 1. Created Constants File

**File**: `src/constants.ts` (NEW)

Defines stable MFE configuration:
- **UUID**: `550e8400-e29b-41d4-a716-446655440000` (never changes)
- **Name**: Ad Banner MFE
- **Version**: 1.0.0
- **Tags**: team=marketing, type=promotion, feature=rewards-signup

### 2. Updated Type Definitions

**File**: `src/types.ts`

Added:
- `NewRelicMFEAgent` interface for scoped agent methods
- Updated `Window.RelibankMicrofrontends.AdBanner` to include `agent` property
- Added `register()` method to `Window.newrelic` interface

### 3. Updated Mount Function

**File**: `src/index.tsx`

**Before** (manual approach):
```typescript
if (window.newrelic?.interaction) {
  window.newrelic.interaction()
    .setName('Microfrontend: Ad Banner Mount')
    .setAttribute('microfrontend', 'ad-banner')
    .save();
}
```

**After** (`.register()` API):
```typescript
let mfeAgent: NewRelicMFEAgent | null = null;

if (window.newrelic?.register) {
  try {
    mfeAgent = window.newrelic.register({
      id: AD_BANNER_MFE_CONFIG.id,
      name: AD_BANNER_MFE_CONFIG.name,
      tags: AD_BANNER_MFE_CONFIG.tags
    });

    mfeAgent.setCustomAttribute('version', AD_BANNER_MFE_CONFIG.version);
    mfeAgent.setCustomAttribute('containerId', options.containerId);

    console.log('[AdBanner Mount] Registered with New Relic:', {
      id: AD_BANNER_MFE_CONFIG.id,
      name: AD_BANNER_MFE_CONFIG.name
    });
  } catch (error) {
    console.error('[AdBanner Mount] Failed to register with New Relic:', error);
  }
}
```

**Stores agent globally**:
```typescript
if (mfeAgent) {
  window.RelibankMicrofrontends = {
    ...window.RelibankMicrofrontends,
    AdBanner: {
      mount: mountAdBanner,
      agent: mfeAgent  // ← Scoped agent stored here
    }
  };
}
```

**Deregisters on unmount**:
```typescript
if (mfeAgent?.deregister) {
  try {
    mfeAgent.deregister();
    console.log('[AdBanner Mount] Deregistered from New Relic');

    if (window.RelibankMicrofrontends?.AdBanner) {
      window.RelibankMicrofrontends.AdBanner.agent = null;
    }
  } catch (error) {
    console.error('[AdBanner Mount] Failed to deregister:', error);
  }
}
```

### 4. Updated Component

**File**: `src/AdBanner.tsx`

**Removed**:
- Manual `useEffect` that called `setCustomAttribute` (lines 8-18)
- Manual `interaction()` tracking (lines 22-32)

**Added**:
- Uses scoped agent from global state
- `addPageAction` instead of `interaction()`

**Before**:
```typescript
useEffect(() => {
  if (window.newrelic) {
    window.newrelic.setCustomAttribute('microfrontendName', 'ad-banner');
  }
}, []);

const handleSignUpClick = () => {
  if (window.newrelic?.interaction) {
    window.newrelic.interaction()
      .setName('AdBanner: Sign Up Clicked')
      .setAttribute('microfrontend', 'ad-banner')
      .save();
  }
};
```

**After**:
```typescript
const handleSignUpClick = () => {
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
  }
};
```

### 5. Created Documentation

**File**: `README.md` (NEW)

Comprehensive documentation covering:
- New Relic integration details
- Entity configuration
- Container requirements
- Verification steps
- NRQL queries
- Troubleshooting

---

## Build Verification

```bash
$ npm run build:mfe:ad-banner
✓ built in 71ms
Output: public/microfrontends/ad-banner/ad-banner.js (5.20 kB │ gzip: 2.24 kB)
```

Build successful with no compilation errors.

---

## What Changed (High Level)

| Aspect | Before | After |
|--------|--------|-------|
| **Registration** | Manual `interaction()` calls | Official `.register()` API |
| **Agent Scope** | Global `window.newrelic` | Scoped `mfeAgent` per MFE |
| **Entity Creation** | Manual (none) | Automatic in New Relic |
| **Performance Metrics** | None | timeToLoad, timeToRegister, timeAlive |
| **Data Attribution** | Mixed with container | Isolated to MFE entity |
| **Lifecycle Tracking** | None | register → deregister |
| **Custom Attributes** | Set globally | Set on scoped agent |
| **Event Tracking** | SPA interactions | Page actions via scoped agent |

---

## Benefits Unlocked

1. ✅ **Automatic Entity Creation**: "Ad Banner MFE" entity appears in New Relic
2. ✅ **Performance Timing**: Automatic timeToLoad, timeToRegister, timeAlive metrics
3. ✅ **Data Scoping**: All MFE events isolated to its entity
4. ✅ **Relationship Mapping**: Visual connection between container and MFE
5. ✅ **Team Assignment**: Can assign teams/repositories to MFE entity
6. ✅ **Better Debugging**: Errors/logs clearly attributed to MFE
7. ✅ **Independent Monitoring**: Monitor MFE performance separately

---

## Next Steps for Testing

### 1. Enable Register API in Container

The container's New Relic browser agent must enable the API:

**Option A: Via New Relic UI**
- Go to Browser app settings
- Enable "Micro Frontend Monitoring"
- Set: `api.register.enabled: true`

**Option B: Via Configuration** (if using agent config)
```javascript
window.NREUM.init.api = {
  register: {
    enabled: true,
    duplicate_data_to_container: false
  }
};
```

### 2. Deploy the Build

```bash
# Already built - copy to pod or restart Skaffold
npm run build:mfe:ad-banner
```

### 3. Verify in Browser Console

Expected logs on mount:
```
[AdBanner Mount] Registered with New Relic: {id: "550e8400...", name: "Ad Banner MFE"}
[AdBanner Mount] Component rendered successfully
```

Expected logs on click:
```
[AdBanner] Sign up click tracked via scoped agent
```

Expected logs on unmount:
```
[AdBanner Mount] Deregistered from New Relic
```

### 4. Verify in New Relic UI

**Entity Check** (Browser > Micro-Frontends):
- Look for "Ad Banner MFE" entity
- Verify entity GUID contains: `550e8400-e29b-41d4-a716-446655440000`

**NRQL Queries**:

Check MFE timing:
```sql
SELECT * FROM MicroFrontEndTiming
WHERE entityGuid LIKE '%550e8400-e29b-41d4-a716-446655440000%'
SINCE 10 minutes ago
```

Check page actions:
```sql
SELECT * FROM PageAction
WHERE actionName = 'adBannerSignUpClicked'
SINCE 10 minutes ago
```

Check lifecycle metrics:
```sql
SELECT average(timeToLoad), average(timeToRegister), average(timeAlive)
FROM MicroFrontEndTiming
WHERE entityGuid LIKE '%550e8400%'
SINCE 1 hour ago
```

---

## Backward Compatibility

✅ **No breaking changes to host application**

The dashboard (`app/routes/dashboard.tsx`) continues to use the same API:

```typescript
window.RelibankMicrofrontends.AdBanner.mount({
  containerId: 'ad-banner-container',
  onSignUpClick: () => { /* ... */ }
});
```

The only difference is that now the MFE properly registers with New Relic internally.

---

## Files Modified

1. ✅ `src/constants.ts` - NEW (MFE configuration)
2. ✅ `src/types.ts` - Updated (added scoped agent types)
3. ✅ `src/index.tsx` - Updated (register/deregister lifecycle)
4. ✅ `src/AdBanner.tsx` - Updated (use scoped agent for tracking)
5. ✅ `README.md` - NEW (comprehensive documentation)

---

## Configuration Required (Container Side)

The host application's New Relic browser agent needs:

- **Agent Version**: ≥ 1.313.0
- **Agent Type**: Pro or Pro+SPA (not Lite)
- **Configuration**: `api.register.enabled: true`

Without this configuration, the MFE will log a warning but continue to function without New Relic tracking.

---

## Troubleshooting Reference

### Warning: `.register()` API not available

**Log**:
```
[AdBanner Mount] New Relic .register() API not available
```

**Cause**: Container agent doesn't have register API enabled

**Solution**: Enable in New Relic UI or agent config

### Entity Not Appearing

**Wait**: 3-5 minutes for entity to appear in New Relic
**Check**: Browser console for errors
**Verify**: Container agent version ≥ 1.313.0

### Events Not Attributed to MFE

**Check**: Scoped agent is stored at `window.RelibankMicrofrontends.AdBanner.agent`
**Verify**: Registration succeeded (check console logs)
**Test**: Run NRQL query for entity GUID

---

## Implementation Complete ✅

The Ad Banner microfrontend now uses New Relic's official `.register()` API for proper observability and entity management. All changes are backward compatible and ready for testing once the container agent is configured.
