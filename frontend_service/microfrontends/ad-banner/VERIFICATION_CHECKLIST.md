# New Relic `.register()` API - Verification Checklist

Use this checklist to verify the implementation is working correctly.

---

## Pre-Deployment Checks

- [x] **Build succeeds without errors**
  ```bash
  npm run build:mfe:ad-banner
  ```
  Expected: ✓ built in ~71ms, output ~5.20 kB

- [x] **Code changes reviewed**
  - Constants file created with stable UUID
  - Types updated with scoped agent interface
  - Mount function calls `.register()`
  - Unmount function calls `.deregister()`
  - Component uses scoped agent for tracking

---

## Container Configuration

Before testing, ensure the container's New Relic browser agent is configured:

### Option 1: Via New Relic UI (Recommended)

- [ ] Log into New Relic
- [ ] Navigate to: Browser > [Your App] > Settings
- [ ] Find "Micro Frontend Monitoring" or "Register API" section
- [ ] Enable: `api.register.enabled: true`
- [ ] Save configuration
- [ ] Wait 5-10 minutes for changes to propagate

### Option 2: Via Agent Configuration

- [ ] Verify agent version ≥ 1.313.0
- [ ] Add to agent init:
  ```javascript
  window.NREUM.init.api = {
    register: {
      enabled: true,
      duplicate_data_to_container: false
    }
  };
  ```
- [ ] Deploy updated configuration

### Verify Agent Type

- [ ] Confirm agent is Pro or Pro+SPA (not Lite)
- [ ] Check: Browser app settings in New Relic UI

---

## Deployment

- [ ] Build microfrontend: `npm run build:mfe:ad-banner`
- [ ] Verify build output exists: `public/microfrontends/ad-banner/ad-banner.js`
- [ ] Deploy to target environment (copy to pod, restart Skaffold, etc.)
- [ ] Clear browser cache (hard refresh: Cmd+Shift+R or Ctrl+Shift+R)

---

## Browser Console Verification

### On Dashboard Load

- [ ] Open browser DevTools Console
- [ ] Navigate to dashboard page
- [ ] Look for registration log:
  ```
  [AdBanner Mount] Registered with New Relic: {id: "550e8400...", name: "Ad Banner MFE"}
  ```
- [ ] Look for render log:
  ```
  [AdBanner Mount] Component rendered successfully
  ```

### Expected Console Logs (Success)

```
[AdBanner Mount] Starting mount with options: {containerId: "ad-banner-container", ...}
[AdBanner Mount] Registered with New Relic: {id: "550e8400-e29b-41d4-a716-446655440000", name: "Ad Banner MFE"}
[AdBanner Mount] Created new root for container: ad-banner-container
[AdBanner Mount] Component rendered successfully
[AdBanner] Global API exposed on window.RelibankMicrofrontends.AdBanner
```

### Expected Console Logs (Register API Not Enabled)

```
[AdBanner Mount] Starting mount with options: {containerId: "ad-banner-container", ...}
[AdBanner Mount] New Relic .register() API not available
[AdBanner Mount] Created new root for container: ad-banner-container
[AdBanner Mount] Component rendered successfully
```

**If you see this warning**, the container agent doesn't have the register API enabled. Go back to "Container Configuration" section.

---

## Functional Testing

### Test 1: MFE Renders

- [ ] Navigate to dashboard
- [ ] Verify ad banner appears (green card with "5% Cash Back" message)
- [ ] Verify banner is styled correctly
- [ ] Check console for registration log

### Test 2: Button Click Tracking

- [ ] Click "Sign Up" button on ad banner
- [ ] Check console for tracking log:
  ```
  [AdBanner] Sign up click tracked via scoped agent
  ```
- [ ] Verify button still functions (calls `onSignUpClick` callback)

### Test 3: Navigation Away and Back

- [ ] From dashboard, navigate to another page
- [ ] Check console for deregister log:
  ```
  [AdBanner Mount] Deregistered from New Relic
  ```
- [ ] Navigate back to dashboard
- [ ] Check console for new registration log (should register again)

### Test 4: Agent Available in DevTools

- [ ] Open browser DevTools Console
- [ ] Type: `window.RelibankMicrofrontends.AdBanner.agent`
- [ ] Press Enter
- [ ] Verify object is returned with methods:
  - `setCustomAttribute`
  - `addPageAction`
  - `noticeError`
  - `deregister`

---

## New Relic UI Verification

### Entity Creation (5-10 minutes after first load)

- [ ] Log into New Relic
- [ ] Navigate to: **Browser > Micro-Frontends**
- [ ] Look for entity: **"Ad Banner MFE"**
- [ ] Click on entity to view details
- [ ] Verify entity GUID contains: `550e8400-e29b-41d4-a716-446655440000`

**Note**: Entity creation may take 3-10 minutes after first registration.

### Relationship Mapping

- [ ] In entity view, look for "Relationships" section
- [ ] Verify relationship to container browser app exists
- [ ] Click relationship to navigate between entities

---

## NRQL Query Verification

Run these queries in New Relic Query Builder (wait 5-10 minutes after testing):

### Query 1: Check MFE Timing Data

```sql
SELECT * FROM MicroFrontEndTiming
WHERE entityGuid LIKE '%550e8400-e29b-41d4-a716-446655440000%'
SINCE 1 hour ago
```

**Expected**: Rows showing timeToLoad, timeToRegister, timeAlive

- [ ] Query returns data
- [ ] `timeToRegister` is present (milliseconds)
- [ ] `timeToLoad` is present (milliseconds)
- [ ] `timeAlive` is present (milliseconds)

### Query 2: Check Page Actions

```sql
SELECT * FROM PageAction
WHERE actionName = 'adBannerSignUpClicked'
SINCE 1 hour ago
```

**Expected**: Rows for each button click

- [ ] Query returns data for button clicks
- [ ] Attributes present: `buttonId`, `feature`, `location`
- [ ] Timestamp matches when you clicked the button

### Query 3: Check Custom Attributes

```sql
SELECT * FROM MicroFrontEndTiming
WHERE entityGuid LIKE '%550e8400%'
FACET version, containerId
SINCE 1 hour ago
```

**Expected**: Custom attributes set during registration

- [ ] `version: "1.0.0"` is present
- [ ] `containerId: "ad-banner-container"` is present

### Query 4: Average Lifecycle Metrics

```sql
SELECT
  average(timeToLoad) as 'Avg Load Time (ms)',
  average(timeToRegister) as 'Avg Register Time (ms)',
  average(timeAlive) as 'Avg Time Alive (ms)',
  count(*) as 'Total Registrations'
FROM MicroFrontEndTiming
WHERE entityGuid LIKE '%550e8400%'
SINCE 1 hour ago
```

**Expected**: Aggregated performance data

- [ ] Average metrics are calculated
- [ ] Total registrations count matches expected (one per page load)

---

## Troubleshooting

### Issue: Warning "New Relic .register() API not available"

**Symptoms**:
- Console shows warning instead of success log
- No entity appears in New Relic

**Solutions**:
1. Verify container agent has `api.register.enabled: true`
2. Check agent version ≥ 1.313.0
3. Verify agent type is Pro or Pro+SPA (not Lite)
4. Clear browser cache and hard refresh
5. Wait 5-10 minutes for config changes to propagate

### Issue: Entity not appearing in New Relic

**Symptoms**:
- Console logs show successful registration
- No entity in Browser > Micro-Frontends

**Solutions**:
1. Wait 5-10 minutes for entity creation
2. Check for network errors in DevTools Network tab
3. Verify browser agent is sending data (check for requests to `bam.nr-data.net`)
4. Run NRQL query to check if data is being collected
5. Verify container agent configuration

### Issue: Events not attributed to MFE

**Symptoms**:
- Console logs show tracking
- No data in NRQL queries

**Solutions**:
1. Verify scoped agent exists: `window.RelibankMicrofrontends.AdBanner.agent`
2. Check console for error messages during tracking
3. Verify registration succeeded (check logs)
4. Wait 5-10 minutes for data ingestion
5. Check container agent configuration

### Issue: Deregister not called

**Symptoms**:
- No deregister log when navigating away
- Entity shows longer `timeAlive` than expected

**Solutions**:
1. Check if cleanup function is being called
2. Verify React Strict Mode isn't preventing cleanup
3. Check mount count logic in console logs
4. Test in production build (not dev mode)

---

## Success Criteria

All of the following should be true for successful implementation:

✅ **Build**
- [x] Microfrontend builds without errors
- [x] Output size ~5KB gzipped

✅ **Browser Console**
- [ ] Registration log appears on mount
- [ ] Deregister log appears on unmount
- [ ] Button click tracking log appears
- [ ] No errors in console

✅ **Functionality**
- [ ] Ad banner renders correctly
- [ ] Button click still works
- [ ] Navigation works (mount/unmount)

✅ **New Relic UI**
- [ ] Entity "Ad Banner MFE" appears in Browser > Micro-Frontends
- [ ] Entity GUID contains correct UUID
- [ ] Relationship to container exists

✅ **NRQL Queries**
- [ ] MicroFrontEndTiming data exists
- [ ] PageAction data exists for clicks
- [ ] Custom attributes present
- [ ] Performance metrics calculated

---

## Sign-Off

Once all checks pass:

- [ ] Implementation verified in dev environment
- [ ] Documentation reviewed
- [ ] Ready for staging deployment
- [ ] Team notified of New Relic entity creation

**Verified by**: _______________
**Date**: _______________
**Environment**: _______________

---

## Additional Resources

- **Documentation**: See `README.md` in this directory
- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`
- **New Relic Docs**: https://docs.newrelic.com/docs/browser/browser-monitoring/microfrontends/
- **Entity Explorer**: Browser > [Your App] > Micro-Frontends in New Relic UI
