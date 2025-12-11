# Alert System Frontend Implementation Plan

## Overview

This plan outlines the implementation of an Alert Management section in the admin dashboard with real-time toast notifications for new alerts.

---

## Current Frontend Architecture

| Aspect | Technology |
|--------|------------|
| Framework | Next.js 15.5.4 (App Router) |
| React | 19.1.0 |
| UI Library | HeroUI + shadcn/ui (Radix primitives) |
| Styling | Tailwind CSS v4 |
| State Management | React useState/useEffect (no Redux/Zustand) |
| API Client | Custom fetch-based (`/src/lib/api-client.ts`) |
| Auth | NextAuth.js v4.24.11 |
| Tables | TanStack React Table |
| Charts | Recharts |

---

## Implementation Phases

### Phase 1: TypeScript Types & API Client Extension

**Files to create/modify:**

1. **`/src/types/alert.ts`** (NEW)
   ```typescript
   // Alert types matching backend schemas
   export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';
   export type AlertStatus = 'created' | 'assigned' | 'acknowledged' | 'investigating' | 'resolved' | 'escalated';
   export type ResolutionType = 'false_alarm' | 'resolved' | 'escalated' | 'no_action_required';

   export interface Alert {
     id: string;
     title: string;
     description: string;
     severity: AlertSeverity;
     status: AlertStatus;
     location: {
       zone_id: string;
       building?: string;
       floor?: string;
       coordinates?: { lat: number; lng: number };
     };
     anomaly_type: string;
     anomaly_id?: string;
     affected_entities: string[];
     data_sources: string[];
     evidence: Record<string, unknown>;
     assigned_to?: string;
     assigned_staff_name?: string;
     assigned_at?: string;
     acknowledged_at?: string;
     resolved_at?: string;
     resolved_by?: string;
     resolver_name?: string;
     resolution_type?: ResolutionType;
     resolution_notes?: string;
     escalation_count: number;
     is_mock: boolean;
     created_at: string;
     updated_at: string;
   }

   export interface AlertsResponse {
     total: number;
     alerts: Alert[];
     page: number;
     page_size: number;
   }

   export interface StaffMember {
     id: string;
     name: string;
     email: string;
     phone?: string;
     role: 'security' | 'supervisor' | 'admin' | 'maintenance';
     status: 'available' | 'busy' | 'off_duty';
     current_workload: number;
   }
   ```

2. **`/src/lib/api-client.ts`** (MODIFY - add alert endpoints)
   ```typescript
   // Add to existing apiClient object:

   // ===== ALERT ENDPOINTS =====
   async getAlerts(params?: {
     status?: string;
     severity?: string;
     page?: number;
     page_size?: number;
   }) { ... },

   async getAlert(alertId: string) { ... },

   async acknowledgeAlert(alertId: string, staffId: string) { ... },

   async resolveAlert(alertId: string, data: {
     staff_id: string;
     resolution_type: string;
     resolution_notes: string;
   }) { ... },

   async escalateAlert(alertId: string, data: {
     escalate_to: string;
     reason: string;
   }) { ... },

   async assignAlert(alertId: string, staffId: string) { ... },

   async getAlertHistory(alertId: string) { ... },

   // ===== STAFF ENDPOINTS =====
   async getStaffList(availableOnly?: boolean) { ... },

   async getStaffDashboard(staffId: string) { ... },
   ```

---

### Phase 2: Toast Notification System

**Files to create:**

1. **`/src/components/ui/toaster.tsx`** (NEW)
   - Install and configure `sonner` toast library (lightweight, React 19 compatible)
   - Alternative: Use `react-hot-toast` or build custom with Radix Toast

   ```bash
   npm install sonner
   ```

2. **`/src/components/ui/toast.tsx`** (NEW)
   - Custom toast component with alert severity styling
   - Support for action buttons (View, Dismiss)
   - Auto-dismiss with configurable duration
   - Sound notification option for critical alerts

3. **`/src/components/providers.tsx`** (MODIFY)
   - Add Toaster provider to the app

---

### Phase 3: Real-time Alert Polling/SSE

**Files to create:**

1. **`/src/hooks/useAlerts.ts`** (NEW)
   - Custom hook for fetching alerts
   - Polling mechanism (every 30 seconds configurable)
   - Track new alerts since last fetch
   - Trigger toast for new alerts

   ```typescript
   export function useAlerts(options?: {
     pollInterval?: number;
     onNewAlert?: (alert: Alert) => void;
   }) {
     // Returns: { alerts, loading, error, refetch, newAlertsCount }
   }
   ```

2. **`/src/hooks/useAlertNotifications.ts`** (NEW)
   - Hook to manage alert notification state
   - Tracks acknowledged notifications
   - Persists to localStorage to prevent duplicate toasts

3. **`/src/components/alert-notification-listener.tsx`** (NEW)
   - Component that runs in sidebar layout
   - Listens for new alerts and triggers toasts
   - Shows toast with: severity icon, title, "View" action

---

### Phase 4: Alerts Dashboard Page

**Files to create:**

1. **`/src/app/dashboard/alerts/page.tsx`** (NEW)
   - Main alerts list page with filters
   - Server component for initial data
   - Features:
     - Filter by status (all, active, resolved)
     - Filter by severity
     - Sort by date/severity
     - Pagination
     - Search by title/description

2. **`/src/app/dashboard/alerts/[alertId]/page.tsx`** (NEW)
   - Alert detail page
   - Full alert information
   - Action buttons (acknowledge, resolve, escalate)
   - Assignment history
   - Investigation notes timeline

3. **`/src/app/dashboard/alerts/layout.tsx`** (NEW - optional)
   - Layout wrapper for alerts section

---

### Phase 5: Alert Components

**Files to create:**

1. **`/src/components/alerts/alert-list.tsx`** (NEW)
   - Reusable alert list component
   - TanStack Table integration
   - Columns: Severity, Title, Status, Location, Assigned To, Time, Actions
   - Row click to view details
   - Inline quick actions

2. **`/src/components/alerts/alert-card.tsx`** (NEW)
   - Card view for single alert
   - Used in list and detail pages
   - Severity-based styling (matching existing anomaly-list.tsx pattern)

3. **`/src/components/alerts/alert-detail.tsx`** (NEW)
   - Full alert detail view
   - Evidence display
   - Affected entities list
   - Map integration (if coordinates available)

4. **`/src/components/alerts/alert-actions.tsx`** (NEW)
   - Action buttons component
   - Acknowledge button (if assigned to current user)
   - Resolve dialog with resolution type selector
   - Escalate dialog with staff selector
   - Reassign dropdown

5. **`/src/components/alerts/alert-filters.tsx`** (NEW)
   - Filter bar component
   - Status filter (multi-select)
   - Severity filter (multi-select)
   - Date range picker
   - Search input

6. **`/src/components/alerts/alert-history-timeline.tsx`** (NEW)
   - Timeline of alert actions
   - Shows: created, assigned, acknowledged, notes, resolved
   - Actor information for each action

7. **`/src/components/alerts/resolve-alert-dialog.tsx`** (NEW)
   - Modal for resolving alerts
   - Resolution type selector
   - Notes textarea
   - Confirm button

8. **`/src/components/alerts/escalate-alert-dialog.tsx`** (NEW)
   - Modal for escalating alerts
   - Staff selector (supervisors/admins)
   - Reason textarea
   - Confirm button

9. **`/src/components/alerts/assign-alert-dialog.tsx`** (NEW)
   - Modal for assigning/reassigning alerts
   - Available staff list with workload indicators
   - Confirm button

---

### Phase 6: Sidebar Navigation Update

**Files to modify:**

1. **`/src/components/sidebar-layout.tsx`** (MODIFY)
   - Add "Alerts" menu item under Management Console
   - Add alert count badge (unresolved alerts)
   - Icon: `Bell` or `ShieldAlert` from lucide-react

   ```tsx
   <SidebarMenuItem>
     <SidebarMenuButton asChild data-active={pathname.startsWith("/dashboard/alerts")}>
       <Link href="/dashboard/alerts" className="flex items-center gap-3">
         <Bell className="h-5 w-5 flex-shrink-0" />
         <span className="truncate">Security Alerts</span>
         {activeAlertCount > 0 && (
           <Badge variant="destructive" className="ml-auto">
             {activeAlertCount}
           </Badge>
         )}
       </Link>
     </SidebarMenuButton>
   </SidebarMenuItem>
   ```

---

### Phase 7: Dashboard Integration

**Files to modify:**

1. **`/src/app/dashboard/page.tsx`** (MODIFY)
   - Add "Recent Alerts" card to dashboard overview
   - Show last 5 active alerts
   - "View All" link to alerts page

2. **`/src/components/dashboard/recent-alerts-card.tsx`** (NEW)
   - Compact alert list for dashboard
   - Shows severity, title, time ago
   - Click to view detail

---

## File Structure Summary

```
src/
├── app/
│   └── dashboard/
│       └── alerts/
│           ├── page.tsx              # Alert list page
│           ├── [alertId]/
│           │   └── page.tsx          # Alert detail page
│           └── layout.tsx            # Optional layout
├── components/
│   ├── alerts/
│   │   ├── alert-list.tsx            # Main list component
│   │   ├── alert-card.tsx            # Single alert card
│   │   ├── alert-detail.tsx          # Full detail view
│   │   ├── alert-actions.tsx         # Action buttons
│   │   ├── alert-filters.tsx         # Filter bar
│   │   ├── alert-history-timeline.tsx # Audit timeline
│   │   ├── resolve-alert-dialog.tsx  # Resolve modal
│   │   ├── escalate-alert-dialog.tsx # Escalate modal
│   │   └── assign-alert-dialog.tsx   # Assign modal
│   ├── dashboard/
│   │   └── recent-alerts-card.tsx    # Dashboard widget
│   ├── ui/
│   │   ├── toaster.tsx               # Toast container
│   │   └── toast.tsx                 # Toast component (if custom)
│   ├── alert-notification-listener.tsx # Global listener
│   ├── sidebar-layout.tsx            # MODIFY - add alerts nav
│   └── providers.tsx                 # MODIFY - add toast provider
├── hooks/
│   ├── useAlerts.ts                  # Alert fetching hook
│   └── useAlertNotifications.ts      # Notification state hook
├── lib/
│   └── api-client.ts                 # MODIFY - add endpoints
└── types/
    └── alert.ts                      # NEW - alert types
```

---

## Component Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                        SidebarLayout                            │
│  ┌─────────────────┐  ┌──────────────────────────────────────┐ │
│  │    Sidebar      │  │              Main Content             │ │
│  │  ┌───────────┐  │  │  ┌────────────────────────────────┐  │ │
│  │  │ Dashboard │  │  │  │     /dashboard/alerts          │  │ │
│  │  │ Anomalies │  │  │  │  ┌──────────────────────────┐  │  │ │
│  │  │ Zones     │  │  │  │  │    AlertFilters          │  │  │ │
│  │  │ Alerts ●3 │◄─┼──┼──┤  └──────────────────────────┘  │  │ │
│  │  │ Profile   │  │  │  │  ┌──────────────────────────┐  │  │ │
│  │  └───────────┘  │  │  │  │    AlertList             │  │  │ │
│  └─────────────────┘  │  │  │  ┌────────────────────┐  │  │  │ │
│                       │  │  │  │   AlertCard        │  │  │  │ │
│  ┌─────────────────┐  │  │  │  │   AlertCard        │  │  │  │ │
│  │AlertNotification│  │  │  │  │   AlertCard        │  │  │  │ │
│  │   Listener     │  │  │  │  └────────────────────┘  │  │  │ │
│  │  (polls API)   │  │  │  └──────────────────────────┘  │  │ │
│  └────────┬────────┘  │  └────────────────────────────────┘  │ │
│           │           └──────────────────────────────────────┘ │
│           ▼                                                    │
│  ┌─────────────────┐                                           │
│  │    Toaster      │  ← Shows toast for new alerts             │
│  │  ┌───────────┐  │                                           │
│  │  │🔴 Critical │  │                                           │
│  │  │ New Alert  │  │                                           │
│  │  │ [View]     │  │                                           │
│  │  └───────────┘  │                                           │
│  └─────────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Toast Notification Flow

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Backend API │────▶│  useAlerts Hook │────▶│ Compare with │
│  /api/alerts │     │  (polling 30s)  │     │ previous IDs │
└──────────────┘     └─────────────────┘     └──────┬───────┘
                                                     │
                                          New alerts found?
                                                     │
                              ┌───────────────────────┴────────────────────┐
                              ▼                                            ▼
                     ┌─────────────────┐                          ┌─────────────┐
                     │  Show Toast per │                          │   No action │
                     │   new alert     │                          └─────────────┘
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │ User clicks     │
                     │ "View" button   │
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │ Navigate to     │
                     │ /alerts/[id]    │
                     └─────────────────┘
```

---

## Alert Status State Machine

```
                    ┌──────────┐
                    │ CREATED  │
                    └────┬─────┘
                         │ assign
                         ▼
                    ┌──────────┐
          ┌────────│ ASSIGNED │────────┐
          │        └────┬─────┘        │
          │             │ acknowledge  │ timeout
          │             ▼              │ (escalate)
          │        ┌────────────┐      │
          │        │ACKNOWLEDGED│      │
          │        └────┬───────┘      │
          │             │ investigate  │
          │             ▼              │
          │     ┌─────────────────┐    │
          │     │  INVESTIGATING  │    │
          │     └───────┬─────────┘    │
          │             │              │
          │    ┌────────┴────────┐     │
          │    │                 │     │
          │    ▼                 ▼     ▼
     ┌──────────┐          ┌───────────┐
     │ RESOLVED │          │ ESCALATED │
     └──────────┘          └───────────┘
```

---

## Styling Consistency

Match existing anomaly severity colors from `anomaly-list.tsx`:

| Severity | Text Color | Background | Border |
|----------|------------|------------|--------|
| Critical | `text-red-500` | `bg-red-950/30` | `border-red-900/50` |
| High | `text-orange-500` | `bg-orange-950/30` | `border-orange-900/50` |
| Medium | `text-yellow-500` | `bg-yellow-950/30` | `border-yellow-900/50` |
| Low | `text-blue-500` | `bg-blue-950/30` | `border-blue-900/50` |

---

## Dependencies to Install

```bash
npm install sonner  # Toast notifications
# OR
npm install react-hot-toast
```

No other new dependencies required - leveraging existing:
- `@tanstack/react-table` for tables
- `lucide-react` for icons
- `date-fns` for date formatting
- Existing shadcn components (Dialog, Badge, Button, etc.)

---

## Implementation Order

1. **Phase 1**: Types & API Client (foundation)
2. **Phase 2**: Toast System (needed for notifications)
3. **Phase 3**: Polling Hook (connects toast to API)
4. **Phase 4**: Alerts Page (main UI)
5. **Phase 5**: Alert Components (reusable parts)
6. **Phase 6**: Sidebar Update (navigation)
7. **Phase 7**: Dashboard Integration (final polish)

---

## API Endpoints Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/alerts` | List alerts with filters |
| GET | `/api/v1/alerts/{id}` | Get alert details |
| POST | `/api/v1/alerts/{id}/assign` | Assign to staff |
| POST | `/api/v1/alerts/{id}/acknowledge` | Acknowledge alert |
| POST | `/api/v1/alerts/{id}/resolve` | Resolve alert |
| POST | `/api/v1/alerts/{id}/escalate` | Escalate alert |
| GET | `/api/v1/alerts/{id}/history` | Get audit history |
| GET | `/api/v1/staff` | List staff members |
| GET | `/api/v1/staff/{id}/dashboard` | Staff dashboard |

---

## Security Considerations

1. **Authorization**: Only SUPER_ADMIN users can access alerts section
2. **Action Permissions**:
   - Acknowledge: Only assigned staff or admins
   - Resolve: Only assigned staff or admins
   - Escalate: Any admin
   - Assign: Only admins
3. **Audit Trail**: All actions logged via backend

---

## Testing Checklist

- [ ] Alert list loads and displays correctly
- [ ] Filters work (status, severity, search)
- [ ] Pagination works
- [ ] Alert detail page shows all information
- [ ] Acknowledge action works
- [ ] Resolve action works with all resolution types
- [ ] Escalate action works
- [ ] Toast notifications appear for new alerts
- [ ] Toast "View" button navigates correctly
- [ ] Sidebar badge shows correct count
- [ ] Dashboard widget shows recent alerts
- [ ] Mobile responsive layout
- [ ] Loading states display correctly
- [ ] Error states handled gracefully

---

## Future Enhancements (Out of Scope)

- WebSocket/SSE for true real-time updates (currently polling)
- Push notifications (browser Notification API)
- Alert sound effects
- Bulk actions (resolve multiple, assign multiple)
- Alert analytics/reports
- Staff mobile app integration
- Demo mode UI for presentations
