# Ad Banner Microfrontend

A promotional banner component for the ReliBank Rewards Credit Card, extracted as a standalone microfrontend with New Relic observability.

## Features

- **Standalone Bundle**: Built as UMD module (~5KB gzipped)
- **New Relic Integration**: Uses official `.register()` API for proper monitoring
- **Lifecycle Management**: Proper mount/unmount with React Strict Mode support
- **Event Tracking**: Button clicks tracked via scoped New Relic agent

## New Relic Integration

This microfrontend implements New Relic's official `.register()` API pattern for proper microfrontend monitoring.

### Entity Configuration

- **Entity ID**: `550e8400-e29b-41d4-a716-446655440000` (stable UUID)
- **Entity Name**: Ad Banner MFE
- **Team**: marketing
- **Type**: promotion

### Automatic Metrics

When properly configured, New Relic automatically collects:

- `timeToLoad`: Time from registration to load complete
- `timeToRegister`: Time taken to register the MFE
- `timeAlive`: Duration the MFE is active

### Custom Attributes

The scoped agent sets:

- `version`: Microfrontend version (1.0.0)
- `containerId`: DOM container ID where MFE is mounted

### Page Actions

User interactions tracked:

- `adBannerSignUpClicked`: When user clicks "Sign Up" button
  - `buttonId`: ID of the button element
  - `feature`: rewards-signup
  - `location`: dashboard

## Building

```bash
npm run build:mfe:ad-banner
```

Output: `public/microfrontends/ad-banner/ad-banner.js`

## Usage

```typescript
// Mount the microfrontend
const unmount = window.RelibankMicrofrontends.AdBanner.mount({
  containerId: 'ad-banner-container',
  onSignUpClick: () => {
    console.log('User clicked sign up');
  }
});

// Later, unmount when done
unmount();
```

## Container Requirements

The host application must provide:

1. **Global Dependencies**: React, ReactDOM, MaterialUI
2. **New Relic Browser Agent**: With `.register()` API enabled
3. **DOM Container**: Element with specified ID

### Enabling .register() API

The container's New Relic browser agent must have the register API enabled:

**Via New Relic UI:**
1. Go to Browser app settings
2. Enable "Micro Frontend Monitoring"
3. Configuration: `api.register.enabled: true`

**Via Agent Configuration:**
```javascript
window.NREUM.init.api = {
  register: {
    enabled: true,
    duplicate_data_to_container: false
  }
};
```

## Verification

### Browser Console Logs

Successful mount:
```
[AdBanner Mount] Registered with New Relic: {id: "550e8400...", name: "Ad Banner MFE"}
[AdBanner Mount] Component rendered successfully
```

Successful click tracking:
```
[AdBanner] Sign up click tracked via scoped agent
```

Successful unmount:
```
[AdBanner Mount] Deregistered from New Relic
```

### New Relic Queries

Check MFE timing data:
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

### Entity in New Relic

Navigate to: **Browser > Micro-Frontends**

Should see "Ad Banner MFE" entity with:
- Entity GUID containing UUID: 550e8400-e29b-41d4-a716-446655440000
- Relationship to container browser app
- Performance metrics and events

## Architecture

### Files

- `src/index.tsx`: Mount/unmount logic, New Relic registration
- `src/AdBanner.tsx`: React component with click tracking
- `src/constants.ts`: MFE configuration (ID, name, tags)
- `src/types.ts`: TypeScript interfaces
- `vite.config.ts`: Build configuration

### Lifecycle

1. **Mount**: Call `.register()` with stable UUID
2. **Store Agent**: Save scoped agent to `window.RelibankMicrofrontends.AdBanner.agent`
3. **Track Events**: Use scoped agent for all New Relic calls
4. **Unmount**: Call `.deregister()` when unmounting

### React Strict Mode Handling

The mount function tracks mount counts to handle React Strict Mode's double-mounting:
- Only creates one root per container
- Only unmounts when all mount instances are cleaned up
- Deregisters from New Relic only on final unmount

## Troubleshooting

### Agent not available warning

```
[AdBanner Mount] New Relic .register() API not available
```

**Solution**: Enable the register API in the container's browser agent configuration.

### Entity not appearing in New Relic

**Checklist**:
- Container agent version ≥ 1.313.0
- `api.register.enabled: true` in agent config
- Wait 3-5 minutes for entity to appear
- Check for network errors in browser console

### Events not being tracked

**Checklist**:
- Verify scoped agent is stored: `window.RelibankMicrofrontends.AdBanner.agent`
- Check console for error messages
- Verify `.register()` succeeded (check logs)
- Test with NRQL query in New Relic

## Benefits

✅ **Automatic entity creation** in New Relic
✅ **Performance timing** (timeToLoad, timeToRegister, timeAlive)
✅ **Data scoping** - MFE events isolated to its entity
✅ **Relationship mapping** - Visual connection to container
✅ **Team assignment** - Can assign teams/repos to entity
✅ **Independent monitoring** - Monitor MFE separately from container
