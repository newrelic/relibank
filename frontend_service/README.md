# ReliBank Frontend Service

A React-based banking demo application built with React Router v7, Material-UI, and New Relic Browser monitoring. This is a **demo application** designed to showcase New Relic's observability capabilities with intentional behaviors for telemetry demonstration.

## 🏗️ Architecture Overview

### Tech Stack
- **Framework**: React Router v7 (SPA mode with client-side routing)
- **UI Library**: Material-UI (MUI)
- **State Management**: React Context API
- **Styling**: Material-UI theme system + Emotion
- **Charts**: Recharts
- **Build Tool**: Vite
- **Language**: TypeScript
- **Monitoring**: New Relic Browser Agent

### 🎨 Theme & Branding

**Color System**: Green + Gold palette based on the ReliBank logo

**Primary Colors (Green)** - Trust & Stability:
- Forest Green `#1a3d1a` - Main brand color (buttons, headers, active states)
- Sage Green `#7a9b3e` - Accents, success states, chart data
- Deep Green `#0f2610` - Dark accents and shadows

**Secondary Colors (Lime)** - Fresh & Modern:
- Lime Accent `#8db600` - Highlights and secondary actions
- Light Lime `#a8cc3a` - Hover states and bright accents

**Tertiary Colors (Gold)** - Wealth & Premium:
- Amber Gold `#d97706` - Warnings, premium features, total balance displays
- Light Gold `#fbbf24` - Call-to-action buttons, promotional highlights
- Deep Amber `#b45309` - Dark gold accents

**Theme Configuration**:
- Defined in `app/components/layout/AppLayout.tsx` (authenticated pages)
- Defined in `app/routes/login.tsx` (login page)
- Uses MUI's `createTheme()` with complete palette configuration

**Static Assets**:
- **Location**: `public/` directory
- **Logo**: `relibank.png` (928x1232px portrait)
  - Used in Sidebar (64x64px container with gap: 1 spacing)
  - Used in Login page (64x64px container)
  - Used as favicon (defined in `app/root.tsx`)
  - Images preserve aspect ratio with `objectFit: 'contain'` in fixed square containers

### Key Features
- Single Page Application (SPA) with client-side routing
- Hot Module Replacement (HMR) in development
- Responsive design with mobile-first breakpoints (xs/sm/md/lg/xl)
- Responsive dashboard with real-time balance updates
- Fund transfer functionality with optimistic updates and error rollback
- New Relic Browser instrumentation for error tracking
- **Browser User ID Tracking**: Automatic user ID assignment and tracking for New Relic sessions
  - Random user selection from database or header-based override
  - Persistent across navigation using sessionStorage
  - Integrated with New Relic Browser's `setUserId()` method
- Recurring payments integration with transaction-service backend

---

## 🔍 New Relic Browser User ID Tracking

### Overview
The frontend automatically assigns and tracks user IDs for New Relic Browser sessions, enabling granular session tracking and user behavior analysis in New Relic.

### How It Works

**On Application Load**:
1. Checks `sessionStorage` for existing `browserUserId`
2. If not found, fetches a user ID from `/accounts-service/browser-user` endpoint
3. Stores user ID in `sessionStorage` for persistence across navigation
4. Calls `window.newrelic.setUserId()` to associate the ID with the New Relic session

**Header Override for Testing**:
- Send `x-browser-user-id: <uuid>` header to the browser-user endpoint
- Useful for automated testing (Postman, Selenium) to track specific user sessions

**User ID Assignment**:
- **Priority 1**: Uses `x-browser-user-id` header if provided and valid (exists in database)
- **Priority 2**: Randomly selects a user ID from the `user_account` table
- Returns both `user_id` and `source` (header/random) for debugging

### Implementation Details

**TypeScript Definitions** (`app/types/newrelic.d.ts`):
```typescript
interface NewRelicBrowserAgent {
  setUserId(userId: string): void;
  setCustomAttribute(name: string, value: string | number | boolean): void;
  // ... other methods
}
```

**State Management** (`app/root.tsx`):
- `browserUserId` state in `LoginContext`
- Three useEffect hooks:
  1. Hydration and sessionStorage loading
  2. Browser user ID fetching from API
  3. New Relic `setUserId()` call when ID changes

**Session Persistence**:
- Stored in `sessionStorage.browserUserId`
- Cleared on logout
- Separate per browser tab (sessionStorage behavior)

### Testing

**Manual Testing**:
```bash
# Test random assignment
curl http://localhost:5002/accounts-service/browser-user

# Test header override
curl -H "x-browser-user-id: 550e8400-e29b-41d4-a716-446655440000" \
     http://localhost:5002/accounts-service/browser-user
```

**Automated Tests**:
- `tests/test_browser_user_tracking.py` - Browser endpoint tests
- `tests/test_apm_user_tracking.py` - Header propagation tests

**New Relic Verification**:
1. Open New Relic Browser UI → Sessions
2. Filter by user ID to see specific user sessions
3. Check session attributes for `userId` field

---

## 📊 Component Hierarchy

### Login Page (`/`)

```
Layout (root.tsx)
└─ html
   ├─ head
   │  ├─ script (New Relic Browser Agent)
   │  ├─ meta (charset, viewport)
   │  ├─ Meta (React Router meta tags)
   │  └─ Links (React Router links)
   │
   └─ body
      ├─ LoginContext.Provider ← Authentication state
      │  └─ LoginPage (routes/login.tsx)
      │     └─ ThemeProvider
      │        ├─ CssBaseline
      │        └─ Box (centered container)
      │           └─ Container
      │              └─ Paper (login card)
      │                 ├─ Lock icon + "ReliBank Login" title
      │                 ├─ Alert (error messages)
      │                 └─ Box (form)
      │                    ├─ TextField (username with Person icon)
      │                    ├─ TextField (password with Lock + Visibility toggle)
      │                    ├─ Button "Sign In" / CircularProgress
      │                    └─ "Don't have an account? Sign Up" link
      │
      ├─ ScrollRestoration
      └─ Scripts
```

**Key Points:**
- Minimal layout without navigation
- Centered login card on full-screen background
- Has access to `LoginContext` for `handleLogin()` function
- Separate theme from authenticated pages

---

### Authenticated Pages (`/dashboard`, `/payments`, `/support`, `/settings`)

```
Layout (root.tsx)
└─ html
   ├─ head
   │  ├─ script (New Relic Browser Agent)
   │  ├─ meta tags
   │  ├─ Meta
   │  └─ Links
   │
   └─ body
      └─ LoginContext.Provider ← Authentication + userData state
         └─ AppLayout (components/layout/AppLayout.tsx)
            └─ ThemeProvider
               ├─ CssBaseline
               └─ Box (full viewport flex container)
                  │
                  ├─ Sidebar (components/layout/Sidebar.tsx)
                  │  └─ Box (256px width, left column)
                  │     ├─ BusinessIcon + "ReliBank" logo
                  │     └─ List (navigation)
                  │        ├─ Dashboard link (with DashboardIcon)
                  │        ├─ Payments link (with PaymentIcon)
                  │        ├─ Support link (with SupportAgentIcon)
                  │        └─ Settings link (with SettingsIcon)
                  │
                  └─ Box (flex: 1, main content column)
                     └─ PageContext.Provider
                        │
                        ├─ Header (components/layout/Header.tsx)
                        │  └─ Box (top bar)
                        │     ├─ Typography (page title: "Dashboard" / "Support" / "Settings")
                        │     └─ Box (right side)
                        │        ├─ IconButton (NotificationsIcon)
                        │        ├─ Divider
                        │        ├─ Avatar (first letter of username)
                        │        └─ Typography (username, e.g., "Alice")
                        │
                        ├─ Box (scrollable content area, flex-grow)
                        │  └─ {children} ← ROUTE COMPONENT RENDERS HERE
                        │     │
                        │     ├─ DashboardPage (routes/dashboard.tsx)
                        │     │  └─ Grid container
                        │     │     ├─ OverviewCard (Total Balance)
                        │     │     ├─ OverviewCard (Checking)
                        │     │     ├─ OverviewCard (Savings)
                        │     │     ├─ TransferCard (components/dashboard/TransferCard.tsx)
                        │     │     ├─ SpendingChart
                        │     │     ├─ SpendingCategories (PieChart)
                        │     │     └─ RecentTransactions
                        │     │
                        │     ├─ PaymentsPage (routes/payments.tsx)
                        │     │  └─ Grid container
                        │     │     ├─ PayBillCard (one-time payments)
                        │     │     ├─ RecurringPaymentsCard (recurring payments)
                        │     │     ├─ PaymentMethodsCard (payment methods)
                        │     │     └─ RecentPaymentsCard (payment history)
                        │     │
                        │     ├─ SupportPage (routes/support.tsx)
                        │     │
                        │     └─ SettingsPage (routes/settings.tsx)
                        │
                        └─ Footer (components/layout/Footer.tsx)
                           └─ Box
                              ├─ Typography (disclaimer)
                              └─ Typography (© 2023 ReliBank)
```

**Key Points:**
- Full application layout with persistent Sidebar, Header, and Footer
- Main content area scrolls independently
- All components have access to `LoginContext` (userData, isAuthenticated)
- Consistent navigation across all authenticated pages

---

## 📱 Responsive Design System

The application uses Material-UI's responsive breakpoints for mobile-first design:

**Breakpoint System:**
- `xs`: 0px+ (mobile)
- `sm`: 600px+ (tablet)
- `md`: 900px+ (small desktop)
- `lg`: 1200px+ (desktop)
- `xl`: 1536px+ (large desktop)

**Responsive Padding Pattern:**
All pages use consistent responsive horizontal padding:
```typescript
sx={{ px: { xs: 2, sm: 4, md: 8, lg: 16, xl: 32 } }}
```

This creates:
- Mobile: 16px padding (xs: 2 × 8px)
- Tablet: 32px padding (sm: 4 × 8px)
- Small Desktop: 64px padding (md: 8 × 8px)
- Desktop: 128px padding (lg: 16 × 8px)
- Large Desktop: 256px padding (xl: 32 × 8px)

**Grid Spacing:**
```typescript
<Grid container spacing={{ xs: 2, sm: 3, md: 4 }}>
```

**Responsive Typography:**
Headers scale based on screen size:
```typescript
sx={{ fontSize: { xs: '1.75rem', sm: '2rem', md: '2.125rem' } }}
```

**Card Stacking Behavior:**

*Dashboard Page:*
- **Overview cards**: Stack vertically on mobile (`xs: 12`), display in 3 columns on desktop (`md: 4`)
  - Avoids awkward 2-1 layout on tablets by skipping `sm` breakpoint
- **Transfer + Chart**: Stack on mobile (`xs: 12`), side-by-side on desktop (`lg: 4` / `lg: 8`)

*Payments Page:*
- **Pay Bill + Payment Methods**: Stack on mobile (`xs: 12`), 2 columns on desktop (`lg: 6`)
- **Fixed height on desktop** (`500px`) with vertical scrolling in payment methods list

**Height Management:**
Cards use responsive heights to ensure proper layout:
```typescript
sx={{ height: { xs: 'auto', lg: '500px' } }}
```

On mobile, cards auto-size to their content. On desktop, fixed heights with scrolling ensure cards align properly and match heights.

---

## 🗂️ Project Structure

```
frontend_service/
├── app/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppLayout.tsx      # Main layout wrapper with theme
│   │   │   ├── Header.tsx         # Top bar with username + notifications
│   │   │   ├── Sidebar.tsx        # Left navigation menu
│   │   │   └── Footer.tsx         # Bottom disclaimer + copyright
│   │   ├── dashboard/
│   │   │   └── TransferCard.tsx   # Fund transfer form component
│   │   └── payments/
│   │       ├── PayBillCard.tsx           # One-time payments (bank + card)
│   │       ├── RecurringPaymentsCard.tsx # Recurring payment management
│   │       ├── PaymentMethodsCard.tsx    # Payment methods display
│   │       └── RecentPaymentsCard.tsx    # Payment history
│   │
│   ├── routes/
│   │   ├── home.tsx               # Default route (redirects to login)
│   │   ├── login.tsx              # Login page
│   │   ├── dashboard.tsx          # Dashboard with accounts + charts
│   │   ├── payments.tsx           # Payments page with bill pay
│   │   ├── support.tsx            # Support/chatbot page
│   │   └── settings.tsx           # Settings page
│   │
│   ├── types/
│   │   └── user.ts                # TypeScript interfaces
│   │
│   ├── root.tsx                   # Root layout + context providers
│   ├── routes.ts                  # Route configuration
│   └── entry.client.tsx           # Client-side entry point
│
├── public/                        # Static assets
│   └── relibank.png               # Logo (928x1232px portrait)
│
├── vite.config.ts                 # Vite + proxy configuration
├── package.json
└── README.md
```

---

## 💳 Payments Functionality

The frontend includes comprehensive bill payment functionality integrating with the bill-pay-service backend.

### Payment Components

Located in `app/components/payments/`:

1. **PayBillCard.tsx**
   - One-time bill payments
   - Unified payment method dropdown (bank accounts + credit cards)
   - Supports both bank transfers and card payments
   - IDs: `pay-bill-*` prefix

2. **RecurringPaymentsCard.tsx**
   - Set up recurring payments
   - Manage and cancel recurring payments
   - Configurable frequency (weekly/monthly/quarterly/annually)
   - IDs: `recurring-payment-*` prefix

3. **PaymentMethodsCard.tsx**
   - Display saved bank accounts and credit cards
   - Add new Stripe test cards
   - Uses flexbox layout with vertical scrolling for long lists
   - Matches height of PayBillCard on desktop (500px with overflowY: 'auto')
   - IDs: `payment-method-*` prefix

4. **RecentPaymentsCard.tsx**
   - Display payment history from transaction service
   - Combines mock data with real transactions
   - Shows payment status with color-coded chips
   - Refreshes automatically when new payments are made

### Transaction Service Integration

**Recurring Payments Endpoint:**

The frontend fetches recurring payment schedules from the transaction-service:

- **Endpoint**: `GET /transaction-service/recurring-payments`
- **Response**: Array of `RecurringScheduleRecord` objects
- **Data**: ScheduleID, BillID, AccountID, Amount, Currency, Frequency, StartDate, Timestamp, CancellationUserID, CancellationTimestamp
- **Filtering**: Backend automatically filters out cancelled schedules (where CancellationTimestamp exists)
- **Frontend Integration**: RecurringPaymentsCard combines backend data with mock data for comprehensive demos
- **Key Handling**: Mock recurring payment IDs use string prefix ('mock-1', 'mock-2') to prevent key conflicts with database numeric IDs

### Bill Pay Service Endpoint Coverage

**✅ All 6 user-facing endpoints are implemented:**

| Endpoint | Method | Component | Function | Purpose |
|----------|--------|-----------|----------|---------|
| `/bill-pay-service/pay` | POST | PayBillCard.tsx | `handleBankPayment()` | Bank-to-bank transfers |
| `/bill-pay-service/card-payment` | POST | PayBillCard.tsx | `handleCardPayment()` | Credit/debit card payments |
| `/bill-pay-service/recurring` | POST | RecurringPaymentsCard.tsx | `handleAddRecurring()` | Set up recurring payments |
| `/bill-pay-service/cancel/{bill_id}` | POST | RecurringPaymentsCard.tsx | `handleCancelPayment()` | Cancel recurring payment |
| `/bill-pay-service/payment-method` | POST | PaymentMethodsCard.tsx | `handleAddPaymentMethod()` | Add payment method |
| `/bill-pay-service/payment-methods/{customer_id}` | GET | PaymentMethodsCard.tsx, PayBillCard.tsx | `fetchPaymentMethods()` | List saved payment methods |

**Internal endpoints (not in UI):**
- `/bill-pay-service/seed-demo-customers` - Admin endpoint for seeding test data
- `/bill-pay-service` - Root health check
- `/bill-pay-service/health` - Health check endpoint

### Payment Features

**Unified Payment Method Dropdown (PayBillCard):**
- Single dropdown showing all payment options in one place
- Format: `{Type} •••• {last4}` (e.g., "Checking •••• 6789", "Visa •••• 1234")
- Replaces previous design that had separate payee text field and account dropdown
- Automatically detects bank accounts vs credit cards and routes to appropriate API
- Bank accounts use routing number last 4 digits
- Cards show brand and last 4 digits
- Simpler UX for bill payments

**Stripe Test Cards:**
- Pre-configured test cards for demo purposes
- Visa, Mastercard, American Express test cards
- No actual Stripe.js integration required
- Uses Stripe test payment method tokens

**Form Pre-filling:**
- All forms pre-filled with test values that work with real database accounts
- Enables quick demonstration and testing
- Values map to actual accounts in init.sql

### ID Attributes for Synthetic Testing

All payment components include unique `id` attributes following this convention:

**Pattern:** `{component-area}-{element-purpose}-{element-type}`

**Examples:**
- `pay-bill-payee` - Payee name input
- `pay-bill-payment-method` - Payment method dropdown
- `pay-bill-submit-btn` - Submit button
- `recurring-payment-frequency` - Frequency dropdown
- `payment-method-card-select` - Test card selector

**See `.claude.md` for complete ID naming conventions and patterns.**

---

## 🔑 Key Concepts

### State Management

**LoginContext** (`root.tsx`)
- **Location**: Provided in `Layout` component
- **State**:
  - `isAuthenticated: boolean`
  - `userData: UserAccount[] | null` (array of checking/savings accounts)
  - `handleLogin: (data) => void`
  - `setUserData: (data) => void`
- **Persistence**: Syncs with `sessionStorage` automatically
- **Initialization**: Initializes to `null`, loads from sessionStorage after component mount

**Why state is in Layout, not App:**
- `Layout` wraps the entire page including `AppLayout` (Header/Sidebar/Footer)
- Allows Header to access `userData` for displaying username
- Previously, state was in `App` component which only wrapped route content

### Data Flow

```
User logs in
    ↓
handleLogin(userData) called
    ↓
setUserData(userData) + sessionStorage.setItem()
    ↓
LoginContext updates
    ↓
Header re-renders with username (useState + useEffect force update)
    ↓
Dashboard receives userData from context
    ↓
TransferCard accesses userData from context (no prop drilling)
```

---

## 🎯 Demo-Specific Behaviors

> **⚠️ IMPORTANT**: This is a **demo application** with intentional behaviors designed to showcase New Relic telemetry. Do not "fix" these behaviors unless explicitly updating demo scenarios.

### 1. No Overdraft Validation (Frontend)

**Location**: `app/components/dashboard/TransferCard.tsx` (lines 74-84)

**Behavior**: Users can transfer more than their account balance.

**Example**: Transfer $10,000 from an account with $100 balance.

**Purpose**:
- Demonstrates backend validation errors
- Shows New Relic error telemetry in action
- Allows testing error scenarios easily

**Production difference**: Real apps would check `transferAmount <= sourceAccount.balance`

---

### 1a. Default Transfer Amount

**Location**: `app/components/dashboard/TransferCard.tsx`

**Behavior**: The transfer form pre-fills with $5.00 for quicker demo testing.

**Implementation**:
```typescript
const [amount, setAmount] = useState('5.00');  // Default value
```

After successful transfer, the amount resets to '5.00' (not empty) for convenience during repeated demos.

**Purpose**:
- Speeds up demo scenarios by having form ready to submit
- Reduces friction during repeated transfers
- Makes testing and demonstrations more efficient

**Production difference**: Real apps typically start with empty transfer amounts to avoid accidental submissions.

---

### 2. Rollback on Transfer Errors

**Location**: `app/components/dashboard/TransferCard.tsx` (lines 125-134, 173-180)

**Behavior**:
- UI updates immediately when transfer is initiated (optimistic update)
- If API fails, the **balances and transactions are rolled back** to original state
- Error is reported to New Relic and UI shows correct balances

**Example Flow**:
1. User has $100 in checking
2. Transfer $50 to savings
3. Balance immediately shows $50 in checking, $50 added to savings (optimistic)
4. API returns 500 error or insufficient funds
5. **Balance rolls back to $100** in checking + error message displays
6. New Relic captures the error with context

**Implementation**:
```typescript
// Original state is stored before optimistic update
const originalUserData = userData;
const originalTransactions = transactions;

setUserData(newUserData);  // Optimistic update

try {
  // API call
} catch (error) {
  setUserData(originalUserData);        // Rollback on error
  setTransactions(originalTransactions); // Rollback transactions
}
```

**Purpose**:
- Demonstrates proper error handling in React applications
- Shows how to maintain data integrity with optimistic updates
- Prevents UI state corruption when API calls fail

---

### 3. Broken Theme Toggle Button

**Location**: `app/components/layout/Header.tsx` (lines 48-76)

**Behavior**: A light/dark mode toggle button in the header that throws a JavaScript error when clicked.

**Visual**: Sun/moon icon (🌓) between notifications and user avatar

**What happens**:
1. User clicks the theme toggle button
2. Error is logged: `Error: Theme toggle is not implemented`
3. Error is reported to New Relic Browser with context
4. Uncaught error is thrown, potentially breaking UI

**Purpose**:
- Demonstrates frontend error tracking
- Shows New Relic Browser error reporting
- Illustrates impact of uncaught JavaScript errors on user experience
- Tests error boundary behavior

**Production difference**: Real apps would implement theme switching logic:
```typescript
// Production would do:
const handleThemeToggle = () => {
  setTheme(theme === 'light' ? 'dark' : 'light');
};
```

---

### 4. Blocking Fibonacci Calculation in Support Chat

**Location**: `app/routes/support.tsx` (lines 36-73)

**Behavior**: When users type phrases like "analyze my spending" or "spending analysis" in the support chat, it triggers a heavy synchronous calculation that freezes the UI.

**Visual**: Normal chat interface at `/support`

**What happens**:
1. User types "analyze my spending" or similar phrases
2. Triggers recursive Fibonacci calculation: `calculateFibonacci(44)`
3. Runs synchronously on main thread for ~8-13 seconds
4. UI completely freezes - buttons don't work, messages don't appear
5. After calculation completes, user's message finally appears
6. Console logs show timing: `[DEMO] Blocking calculation complete: fib(44) = ...`

**Trigger phrases** (case-insensitive):
- "analyze my spending"
- "analyse my spending"
- "spending analysis"
- "check my spending"

**Purpose**:
- Demonstrates frontend performance bottlenecks
- Shows impact of blocking JavaScript on main thread
- Illustrates poor user experience from synchronous heavy computations
- **Generates an INP (Interaction to Next Paint) spike in New Relic Browser**
- Tests New Relic Browser's Core Web Vitals monitoring and long task detection

**Production difference**: Real apps would use web workers or async processing:
```typescript
// Production would do:
const worker = new Worker('fibonacci-worker.js');
worker.postMessage(44);
worker.onmessage = (e) => {
  console.log('Result:', e.data);
};
```

---

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn
- Docker (for containerized deployment)

### Installation

```bash
cd frontend_service
npm install
```

### Environment Variables

Create a `.env` file or set these in your environment:

```bash
VITE_NEW_RELIC_ACCOUNT_ID=your_account_id
VITE_NEW_RELIC_BROWSER_APPLICATION_ID=your_app_id
VITE_NEW_RELIC_LICENSE_KEY=your_license_key
```

### Development

Start the development server with HMR:

```bash
npm run dev
```

Application runs at `http://localhost:3000`

### Backend Service Proxy

The Vite dev server proxies API requests to backend services:

```typescript
// vite.config.ts
proxy: {
  '/accounts-service': 'http://accounts-service.relibank.svc.cluster.local:5002',
  '/chatbot-service': 'http://chatbot-service.relibank.svc.cluster.local:5003',
  '/bill-pay-service': 'http://bill-pay-service.relibank.svc.cluster.local:5000'
}
```

Requests to `http://localhost:3000/accounts-service/*` are proxied to the accounts service.

---

## 🔧 Development Tips

### Testing Error Scenarios

**To test transfer errors (for New Relic demos):**

1. Scale down bill-pay-service:
   ```bash
   kubectl scale deployment bill-pay-service -n relibank --replicas=0
   ```

2. Attempt a transfer in the UI

3. Observe:
   - Balance updates immediately (optimistic)
   - Error message appears
   - **Balance rolls back to original amount**
   - Check New Relic Browser for captured error

4. Restore service:
   ```bash
   kubectl scale deployment bill-pay-service -n relibank --replicas=1
   ```

### Debugging Context Issues

If components show "Loading..." instead of user data:

1. Check browser console for `[Layout]` and `[Header]` debug logs
2. Verify `sessionStorage.getItem('userData')` has data
3. Ensure component is inside `LoginContext.Provider` (check component tree)
4. Check that `useEffect` hooks are running (state updates after mount)

### Common Issues

**State Initialization**:
- Ensure state initializes to `null`/`false` consistently
- Load from sessionStorage only in `useEffect` (runs after component mount)
- Avoid reading browser-specific values during initial render

**Username Not Displaying**:
- `userData` is an array: `userData[0].name` to access first account
- Extract first name: `userData[0].name.split(' ')[0]` gets "Alice" from "Alice Checking"

---

## 🏗️ Building for Production

Create a production build:

```bash
npm run build
```

Output:
```
build/
└── client/    # Static assets (bundled JS, CSS, HTML)
```

Note: Since SSR is disabled (`ssr: false` in `react-router.config.ts`), only client-side assets are generated.

### Docker Deployment

```bash
# Build image
docker build -t relibank-frontend .

# Run container
docker run -p 3000:3000 \
  -e VITE_NEW_RELIC_ACCOUNT_ID=your_account_id \
  -e VITE_NEW_RELIC_BROWSER_APPLICATION_ID=your_app_id \
  -e VITE_NEW_RELIC_LICENSE_KEY=your_license_key \
  relibank-frontend
```

---

## 📝 Code Style Guidelines

### Component Organization

1. **Layout components** in `app/components/layout/`
2. **Feature components** in `app/components/{feature}/`
3. **Route components** in `app/routes/`
4. **Shared types** in `app/types/`

### Naming Conventions

- Components: PascalCase (`TransferCard.tsx`)
- Functions: camelCase (`handleLogin`)
- Context: PascalCase with "Context" suffix (`LoginContext`)
- Types/Interfaces: PascalCase (`UserAccount`, `LoginContextType`)

### State Management

- Use Context API for global state (auth, user data)
- Use local `useState` for component-specific state
- Wrap state updates that need persistence with sync functions (e.g., `updateUserData`)

---

## 🧪 Testing Demo Scenarios

### Scenario 1: Successful Transfer

1. Login with any credentials
2. Navigate to Dashboard
3. Transfer $50 from Checking to Savings
4. ✅ Verify: Balance updates immediately
5. ✅ Verify: Success message appears
6. ✅ Verify: New transactions appear in list

### Scenario 2: Failed Transfer (Error Demo)

1. Stop bill-pay-service
2. Transfer any amount
3. ✅ Verify: Balance updates immediately (optimistic)
4. ✅ Verify: Error message appears
5. ✅ Verify: **Balance rolls back to original amount**
6. ✅ Verify: New Relic captures error with context

### Scenario 3: Overdraft Attempt (No Frontend Validation)

1. Check account balance (e.g., $1,500 in Checking)
2. Attempt to transfer $10,000
3. ✅ Verify: Form allows submission (no frontend validation)
4. ✅ Verify: Backend rejects with error
5. ✅ Verify: Balance shows incorrect amount
6. ✅ Verify: New Relic captures validation error

### Scenario 4: Frontend Error (Broken Theme Toggle)

1. Login and navigate to any page
2. Look for the sun/moon icon (🌓) in the header
3. Click the theme toggle button
4. ✅ Verify: Error appears in browser console
5. ✅ Verify: Uncaught error: "Theme toggle is not implemented"
6. ✅ Verify: New Relic Browser captures the error with context
7. ✅ Verify: UI may show error state or error boundary

**Purpose**: Demonstrates client-side JavaScript error tracking and error boundary behavior.

### Scenario 5: Blocking UI Performance (Support Chat - INP Spike)

1. Login and navigate to `/support`
2. Type any spending analysis phrase in the chat:
   - "analyze my spending"
   - "spending analysis"
   - "check my spending"
3. Press Enter or click Send
4. ✅ Verify: UI completely freezes for 8-13 seconds
5. ✅ Verify: Message doesn't appear immediately
6. ✅ Verify: Buttons become unresponsive
7. ✅ Verify: Console logs show: `[DEMO] Running blocking Fibonacci calculation...`
8. ✅ Verify: After ~10 seconds, message appears and UI unfreezes
9. ✅ Verify: New Relic Browser captures long task duration
10. ✅ Verify: **INP (Interaction to Next Paint) spike visible in New Relic Browser > Core Web Vitals**

**Purpose**: Demonstrates frontend performance bottlenecks from blocking JavaScript on the main thread. Specifically designed to generate a measurable INP spike in New Relic's Core Web Vitals monitoring.

---

## 🐛 Known Issues & Intentional Behaviors

### Not Bugs (By Design)

❌ **Don't "fix" these:**

1. **No overdraft validation** - Allows demonstrating backend errors
2. **Transfer with insufficient funds allowed** - Tests error telemetry and rollback logic
3. **Broken theme toggle button** - Demonstrates frontend error tracking
4. **Blocking Fibonacci in support chat** - Demonstrates UI performance issues

### Actual Bugs to Report

✅ **Do fix these:**

1. Context not accessible in components
2. New Relic agent not loading
3. Navigation broken after login
4. State not loading from sessionStorage

---

## 📚 Additional Resources

- [React Router v7 Docs](https://reactrouter.com/)
- [Material-UI Documentation](https://mui.com/material-ui/)
- [New Relic Browser Agent](https://docs.newrelic.com/docs/browser/browser-monitoring/)
- [Vite Configuration](https://vitejs.dev/config/)

---

## 🤝 Contributing

When making changes:

1. ✅ Preserve demo-specific behaviors (see warnings above)
2. ✅ Add comments for any intentional "anti-patterns"
3. ✅ Test both success and error scenarios
4. ✅ Verify New Relic instrumentation still works
5. ✅ Update this README if architecture changes

---

Built with ❤️ for New Relic demos
