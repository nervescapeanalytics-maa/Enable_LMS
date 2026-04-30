# ENABLE PROGRAM — Admin Console v4.0 (Purple Edition)

## Complete Documentation

**URL:** `http://192.168.1.113:8000/admin`  
**Version:** 4.0 (Purple Edition)  
**Framework:** Django Admin (Customized)  
**Theme:** Purple Gradient Design System (`#844FC1`)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Theme System & Dark Mode](#2-theme-system--dark-mode)
3. [Header & Navigation](#3-header--navigation)
4. [Sidebar Navigation](#4-sidebar-navigation)
5. [Dashboard (Home Page)](#5-dashboard-home-page)
6. [Change List (Table View)](#6-change-list-table-view)
7. [Column-Level Filtering](#7-column-level-filtering)
8. [Row Click-to-Edit](#8-row-click-to-edit)
9. [Search Enhancement (Ctrl+K)](#9-search-enhancement-ctrlk)
10. [Back Button on Forms](#10-back-button-on-forms)
11. [Import/Export System](#11-importexport-system)
12. [Bulk Status Actions](#12-bulk-status-actions)
13. [Color-Coded Status Badges](#13-color-coded-status-badges)
14. [Keyboard Shortcuts](#14-keyboard-shortcuts)
15. [Toast Notifications](#15-toast-notifications)
16. [Admin Profile Dropdown](#16-admin-profile-dropdown)
17. [Live Clock](#17-live-clock)
18. [Enhanced Form Layout](#18-enhanced-form-layout)
19. [Responsive Design](#19-responsive-design)
20. [Registered Models & Apps](#20-registered-models--apps)
21. [Sidebar Model Reference — Every Model in Detail](#21-sidebar-model-reference--every-model-in-detail)
    - 21.1 [ACCOUNTS](#211-accounts) — Students, Teachers, Admins, Parents, Roles, Permissions, Role Permissions
    - 21.2 [ACADEMICS](#212-academics) — Academic Sessions, Groups, Categories, Subjects, Chapters, Topics, Batches, Batch Students, Batch Teachers, Languages, States, Cities, Religions, Schools, Subject Sections
    - 21.3 [ASSESSMENTS](#213-assessments) — Tests, Test Sections, Questions, Test Attempts, Test Attempt Answers, Test Feedbacks, Offline Test Marks
    - 21.4 [ATTENDANCE](#214-attendance) — Attendances, Attendance Correction Requests, Attendance Summaries
    - 21.5 [CLASSES](#215-classes) — YouTube Channels, Scheduled Classes, Class Access Tokens, Class Watch Times
    - 21.6 [COMMUNICATION](#216-communication) — Support Tickets, Ticket Messages, Announcements, Announcement Reads, Direct Messages, Notifications
    - 21.7 [MATERIALS](#217-materials) — Study Materials, Material Accesses, Photo Galleries, Scholarships, Topper Students
    - 21.8 [SESSIONS TRACKING](#218-sessions-tracking) — User Devices, User Sessions, Login History, User Activities
    - 21.9 [AUDIT](#219-audit) — Audit Logs, Audit Purge Policies, Backup Policies, Backup History
    - 21.10 [SYSTEM CONFIG](#2110-system-config) — System Settings, Feature Flags, MFA Policies, Maintenance Windows, Founder Infos, Enquiry Forms, AI Feature Configs, Class Link Configs, Attendance Rules
    - 21.11 [REALTIME](#2111-realtime) — Realtime Events
    - 21.12 [TENANTS](#2112-tenants) — Tenants

---

## 1. Overview

### 1.1 What Is This?

The **ENABLE PROGRAM Admin Console** is a fully customized Django Administration interface designed specifically for **coaching institutes, tuition centers, and online education platforms**. It transforms Django's default admin into a modern, branded, production-grade management console with:

- Purple gradient design system with dark mode support
- Client-side column filtering on every data table
- One-click CSV Import/Export on 22+ models
- Real-time dashboard with animated statistics
- Color-coded status badges for visual data scanning
- Keyboard shortcuts for power users
- Responsive layout for tablet/mobile access

### 1.2 Example

When an admin navigates to `http://192.168.1.113:8000/admin/`, they see a dashboard with live statistics (total students, active batches, today's attendance), app modules arranged in a grid, and a purple-branded header with a live clock and profile dropdown — instead of Django's plain white admin interface.

### 1.3 Why This Feature Was Added

Django's default admin is functional but visually plain, lacks branding, and requires developer knowledge to use effectively. For a coaching institute, the admin console is used daily by non-technical staff (center managers, academic coordinators). A polished, intuitive interface:

- **Reduces training time** — Staff can navigate visually instead of memorizing URLs
- **Increases adoption** — A professional look builds trust and encourages consistent use
- **Reduces errors** — Color-coded badges and clear layouts minimize data entry mistakes

### 1.4 How It's Used — Real-Time Use Case

**Scenario:** A center manager at a coaching institute opens the admin console every morning to:
1. Check today's attendance statistics on the dashboard
2. View and filter the Batch Students table to see enrollments
3. Export a CSV of students in the "NEET 2025" batch for SMS notifications
4. Import a CSV of new student registrations received overnight

### 1.5 Who Uses It?

| Role | Usage | If Not Available |
|------|-------|------------------|
| **Super Admin** | Full system configuration, user management, all models | Would need direct database access or Django shell |
| **Center Manager** | Student/batch management, attendance review, reports | Would need spreadsheets and manual tracking |
| **Academic Coordinator** | Subject/chapter management, test configuration | Would need separate content management tools |
| **IT Administrator** | System settings, audit logs, backup policies | Would need server-level access for every config change |

---

## 2. Theme System & Dark Mode

### 2.1 What Is This?

A **three-way theme selector** (Light / Dark / System) built into the admin profile dropdown. The entire admin interface — header, sidebar, tables, forms, modals, dropdowns, scrollbars — adapts to the selected theme. The System option follows the operating system's `prefers-color-scheme` setting and updates in real-time.

### 2.2 Example

- **Light mode:** White backgrounds (`#FFFFFF`), dark text (`#0f172a`), purple accents
- **Dark mode:** Dark backgrounds (`#0f0f1a`, `#1a1a2e`), light purple text (`#c4b5fd`), adjusted contrast for every element
- **System mode:** Automatically follows the user's OS/browser dark mode preference

### 2.3 Why This Feature Was Added

- Staff working **late-night shifts** (exam result upload, class scheduling) benefit from dark mode to reduce eye strain
- **Different environments** — some admin areas have dim lighting (server rooms, video control booths)
- **Accessibility** — some users have visual preferences that a single theme cannot accommodate
- **Modern expectation** — users expect dark mode in 2025+ applications

### 2.4 How It's Used

1. Click the **user avatar/name** in the top-right corner of the header
2. In the profile dropdown, find the **Theme** section
3. Click **Light**, **Dark**, or **System**
4. The active theme shows a purple checkmark
5. The choice is saved to `localStorage` and persists across browser sessions

### 2.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| All admin users | Profile dropdown → Theme section | Users would be stuck with a single light theme, potentially causing eye strain during extended sessions |

---

## 3. Header & Navigation

### 3.1 What Is This?

A **sticky gradient header bar** that remains pinned to the top of the screen while scrolling. It contains:

- **Site branding** — "ENABLE PROGRAM — Admin Console" with a link to the dashboard
- **Live clock** — Real-time date and time display (see [Section 17](#17-live-clock))
- **Website link** — Quick jump to the public-facing website (`/`)
- **Dashboard link** — Quick jump to the staff dashboard (`/staff/dashboard/`)
- **Admin profile** — User avatar, name, and dropdown menu (see [Section 16](#16-admin-profile-dropdown))

### 3.2 Example

The header shows:  
`[ENABLE PROGRAM — Admin Console]  [● Mon, 16 Feb 2026, 10:30:15 AM]  [🌐 Website]  [📊 Dashboard]  [👤 Admin ▾]`

All elements remain visible even when scrolling long tables or forms.

### 3.3 Why This Feature Was Added

- **Context preservation** — Users always know which system they're in
- **Quick navigation** — One-click access to the website and dashboard without using the browser's back button or typing URLs
- **Time awareness** — The live clock helps staff track time during exam data entry, class scheduling, and attendance marking
- **Professional appearance** — Gradient purple header with shadow creates a branded experience

### 3.4 How It's Used — Real-Time Use Case

**Scenario:** An academic coordinator is editing a test configuration deep in the admin. They need to quickly check the public website to verify how the test appears to students:
1. Click **"Website"** in the header → opens the frontend in the same tab
2. Verify the test listing
3. Click the browser back button or use the admin bookmark to return

### 3.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| All admin users | Visible on every page | Users would need to manually type URLs or use browser bookmarks to switch between admin, website, and dashboard |

---

## 4. Sidebar Navigation

### 4.1 What Is This?

A **260px left sidebar** listing all registered Django admin models organized by app. Each app group has:

- **Collapsible headers** — Click any app name (e.g., "ACADEMICS", "ASSESSMENTS") to collapse/expand its model list
- **Active page highlighting** — Current page is marked with a purple left-border accent
- **State persistence** — Collapsed/expanded state is saved in `localStorage` so it survives page reloads
- **Search filter** — A text input at the top to quickly filter the sidebar by model name

### 4.2 Example

```
ACADEMICS            ▾
├─ Academic sessions
├─ Batches            ← correctly pluralized
├─ Batch students
├─ Categories         ← correctly pluralized
├─ Cities             ← correctly pluralized
├─ Chapters
├─ Groups
├─ Languages
└─ ...
ASSESSMENTS          ▸  (collapsed)
ATTENDANCE           ▾
├─ Attendances
├─ Attendance summaries  ← correctly pluralized
└─ ...
```

### 4.3 Why This Feature Was Added

- **Organized navigation** — With 51 models across 12 apps, a flat list would be overwhelming. Collapsible groups let users focus on the app they're working with
- **Quick access** — The search filter helps find models instantly instead of scrolling
- **Correct English** — Django's auto-pluralization produces errors like "Batchs", "Categorys", "Citys". All 14 irregular plurals are now fixed
- **Reduced clutter** — Add-links are hidden from the sidebar (available on the changelist page instead)

### 4.4 How It's Used — Real-Time Use Case

**Scenario:** A center manager needs to add a new city to the reference data:
1. If the "ACADEMICS" section is collapsed, click it to expand
2. Click **"Cities"** in the sidebar
3. The Cities changelist opens with the sidebar showing "Cities" highlighted

### 4.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| All admin users | Left sidebar on every page | Users would see a messy, non-collapsible list with grammatically incorrect labels ("Batchs", "Categorys"), making navigation slower and less professional |

---

## 5. Dashboard (Home Page)

### 5.1 What Is This?

The admin dashboard at `/admin/` is enhanced with **real-time statistics cards** showing key metrics:

| Stat | Source |
|------|--------|
| Total Students | `Student.objects.count()` |
| Total Teachers | `Teacher.objects.count()` |
| Active Batches | `Batch.objects.filter(status='ACTIVE').count()` |
| Total Tests | `Test.objects.count()` |
| Active Sessions | `UserSession.objects` (active count) |
| Tenants | `Tenant.objects.count()` |
| AI Features Configured | `AIFeatureConfig.objects.count()` |
| Today's Attendance | Present / Absent / Late / On Leave counts |
| RBAC Stats | Role and permission counts by type |

Statistics are displayed as **animated counter cards** that count from 0 to the target number on page load (800ms, ease-out cubic).

### 5.2 Example

When loading the dashboard, four stat cards appear at the top:
```
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│    156       │ │     12       │ │      8       │ │     45       │
│  Students    │ │  Teachers    │ │Active Batches│ │    Tests     │
│         👥   │ │         👨‍🏫   │ │         📚   │ │         📝   │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

The numbers animate from 0 to 156, 0 to 12, etc. over ~1 second with a smooth easing effect.

### 5.3 Why This Feature Was Added

- **At-a-glance status** — Institute directors and managers need to see key numbers without clicking into individual model pages
- **Morning briefing** — The first thing a manager sees when opening the admin sets context for the day
- **Accountability** — Teacher count, attendance stats, and session counts help track operational health
- **Data-driven decisions** — Immediately spot anomalies (e.g., 0 attendance today = system issue or holiday)

### 5.4 How It's Used — Real-Time Use Case

**Scenario:** Institute director opens the admin at 9 AM every Monday:
1. Sees **156 students** enrolled — up from 148 last week → growth is healthy
2. Sees **Today's attendance: 0** — it's Monday morning, classes haven't started yet
3. Sees **8 Active Batches** — confirms all batches are still active
4. Clicks on the "Academics" app module to drill into batch details

### 5.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| Institute Director | Dashboard home page | Would need to click into each model and mentally aggregate counts |
| Center Manager | Dashboard home page | Would have no quick view of daily operations |
| Academic Coordinator | Dashboard home page | Would need a separate reporting tool |

---

## 6. Change List (Table View)

### 6.1 What Is This?

Every model's list view (changelist) is enhanced with:

- **Card-style table** — Results wrapped in a bordered card with shadow and rounded corners
- **Sticky headers** — Column headers stay visible while scrolling long tables
- **Zebra-stripe rows** — Alternating subtle purple tint for readability
- **Hover highlighting** — Rows glow on mouse hover
- **Sorted column accent** — The currently sorted column header is highlighted in purple
- **Full-width layout** — Django's default right-side filter panel is hidden; the table uses 100% width

### 6.2 Example

A Student list view shows:
```
┌─────────────────────────────────────────────────────────────────────┐
│ ☐  NAME ▼🔽    EMAIL 🔽     BATCH 🔽   STATUS 🔽   ENROLLED 🔽   │ ← sticky headers with filter icons
├─────────────────────────────────────────────────────────────────────┤
│ ☐  Naveen Reddy  naveen@lms  NEET-2025  [Active]   Feb 14, 2026  │ ← clickable row
│ ☐  Kavya Saxena  kavya@lms   JEE-A      [Active]   Feb 14, 2026  │
│ ☐  Nisha Verma   nisha@lms   NEET-2025  [Active]   Feb 14, 2026  │ ← zebra stripe
└─────────────────────────────────────────────────────────────────────┘
```

### 6.3 Why This Feature Was Added

- **Data density** — Full-width tables show more columns without scrolling
- **Visual hierarchy** — Sticky headers, hover states, and zebra stripes help scan large datasets
- **Consistency** — Every model list looks the same, reducing cognitive load
- **Professional appearance** — Card-style design with shadows mimics modern SaaS dashboards

### 6.4 How It's Used — Real-Time Use Case

**Scenario:** Academic coordinator reviews all 25 batch student enrollments:
1. Opens **Batch students** from the sidebar
2. Sees the full-width table with sticky headers
3. Scrolls down — headers stay visible for reference
4. Hovers over a row to identify it, clicks to open the edit form

### 6.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| All admin users | Every model's list view | Users would see Django's plain, narrow table with a filter sidebar consuming 25% of the width |

---

## 7. Column-Level Filtering

### 7.1 What Is This?

**Every column header** in every changelist table displays a small **funnel (🔽) icon**. Clicking the icon opens a dropdown panel listing all unique values in that column with checkboxes, a search input, value counts, and Clear/Done buttons. Multiple columns can be filtered simultaneously. Filters are applied client-side with instant row hide/show — no page reload required.

### 7.2 Example

Clicking the filter icon on the "BATCH" column header:

```
  BATCH ▼ 🔽  ← click the funnel icon
  ┌─────────────────────────┐
  │ 🔍 Search...            │
  ├─────────────────────────┤
  │ ☐ Advanced-12           3│ ← 3 students in this batch
  │ ☑ Foundation-11          4│ ← selected (checked)
  │ ☐ JEE-2025-A            2│
  │ ☐ JEE-2025-B            3│
  │ ☑ NEET-2025              3│ ← selected (checked)
  ├─────────────────────────┤
  │ [Clear]          [Done] │
  └─────────────────────────┘
```

After selecting "Foundation-11" and "NEET-2025", a purple badge `2` appears on the funnel icon, and only rows matching those values are shown. Other rows are hidden instantly.

### 7.3 Why This Feature Was Added

- **Excel-like filtering** — Staff are familiar with Excel's column filter dropdowns. This brings the same UX to the admin
- **No page reload** — Django's built-in `list_filter` requires a full page reload. Column filters are instant
- **Multi-column** — Filter by batch AND status AND date simultaneously
- **Search within filter** — For columns with many values (e.g., 50 cities), the search input lets users find values quickly
- **Value counts** — Shows how many rows have each value, helping users understand data distribution

### 7.4 How It's Used — Real-Time Use Case

**Scenario:** Center manager wants to see which students in the "NEET 2025" batch are inactive:
1. Open **Batch Students** changelist
2. Click the funnel icon on **"BATCH"** column → select "NEET-2025" → click Done
3. Click the funnel icon on **"ACTIVE"** column → select "Inactive" → click Done
4. The table now shows only inactive students in the NEET 2025 batch
5. Select all visible rows and use the "Activate selected" action to reactivate them

### 7.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| Center Manager | Any changelist (Batch Students, Attendance, Tests) | Would need Django's sidebar filter (hidden by default) or manual page-by-page searching |
| Academic Coordinator | Subject/Chapter/Question lists | Would need to use database queries or exports to find specific records |
| IT Administrator | Audit logs, Login History | Would need CLI/SQL queries to filter security logs |

---

## 8. Row Click-to-Edit

### 8.1 What Is This?

Clicking **anywhere on a table row** (not just the link text) navigates to that record's edit page. The cursor changes to a pointer hand on hover. Clicks on checkboxes, links, and selects are excluded so they work normally.

### 8.2 Example

Instead of clicking precisely on "Naveen Reddy" (the link text), the user can click on the email column, the status column, or any empty space in the row — all navigate to the same edit page.

### 8.3 Why This Feature Was Added

- **Larger click target** — Reduces precision required, especially on touch devices or when quickly scanning rows
- **Familiar behavior** — Many modern admin interfaces (Google Admin, Shopify) use row-click navigation
- **Speed** — Saves time when reviewing multiple records in sequence

### 8.4 How It's Used

1. Open any changelist (e.g., Students)
2. Click anywhere on a row (outside of checkboxes/links)
3. The edit form for that record opens immediately

### 8.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| All admin users | Every changelist table | Users would need to precisely click on the specific link text in the first column, which can be difficult with long lists |

---

## 9. Search Enhancement (Ctrl+K)

### 9.1 What Is This?

The changelist search bar is enhanced with:
- **Keyboard shortcut** — Press `Ctrl+K` (or `Cmd+K` on Mac) from anywhere on the page to instantly focus the search bar
- **Styled search field** — Minimum 300px width, rounded corners, purple focus ring, card-style container
- **Placeholder text** — Shows "Search..." to indicate the field is active

### 9.2 Example

An admin is scrolled to the bottom of a long student list. They press `Ctrl+K` — the search bar at the top receives focus and they can immediately start typing a student name. No scrolling or clicking required.

### 9.3 Why This Feature Was Added

- **Power-user efficiency** — Keyboard shortcuts eliminate mouse movement
- **Familiar convention** — `Ctrl+K` is the universal "search" shortcut used by VS Code, Slack, Notion, and many other tools
- **Speed** — Finding a specific record in a large dataset should take seconds, not minutes

### 9.4 How It's Used — Real-Time Use Case

**Scenario:** A teacher calls the front desk to ask about a student's enrollment status:
1. Front desk staff presses `Ctrl+K` → search bar focuses
2. Types the student's name → hits Enter
3. Results filter to matching students
4. Clicks the row to view details → confirms enrollment status over the phone

### 9.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| All admin users | Any changelist with a search bar | Users would need to scroll up and click the search field manually |

---

## 10. Back Button on Forms

### 10.1 What Is This?

Every **Add** and **Change** form page now displays a **"← Back" button** next to the page title (`<h1>`). The button navigates to the model's changelist page (extracted from the breadcrumb trail).

### 10.2 Example

```
[← Back]  Change batch student
─────────────────────────────
BatchStudent object (f902e037-...)               [HISTORY]
```

Clicking "← Back" returns to the Batch Students changelist.

### 10.3 Why This Feature Was Added

- **No back button existed** — Django's default change form has no explicit back button; users had to use the browser's back button or click breadcrumbs
- **Breadcrumbs are small** — The breadcrumb links at the top are tiny and easy to miss
- **One-click return** — A prominent back button makes navigation intuitive, especially for non-technical staff
- **Consistency** — Modern web apps always provide a visible way to go back

### 10.4 How It's Used — Real-Time Use Case

**Scenario:** A center manager opens a batch student record to check enrollment details, then wants to return to the list:
1. Clicks the student row in the changelist (row click-to-edit)
2. Reviews the details on the change form
3. Clicks **"← Back"** → returns to the Batch Students list
4. No need to use browser history or find the breadcrumb link

### 10.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| All admin users | Every Add/Change form page | Users would rely on browser back button (which might break with form submissions) or tiny breadcrumb links |

---

## 11. Import/Export System

### 11.1 What Is This?

A complete data import/export system available on 22+ models with three capabilities:

| Feature | Action Type | Scope | Format |
|---------|-------------|-------|--------|
| **Export Selected as CSV** | Action dropdown | Selected rows only | CSV |
| **Export Selected as JSON** | Action dropdown | Selected rows only | JSON |
| **Export All CSV** (toolbar button) | Toolbar button | Entire table | CSV |
| **Import CSV** (toolbar button) | Toolbar button | Bulk create | CSV |

### 11.2 Example

**Export:** Select 5 students → Action: "📥 Export selected as CSV" → Go → Downloads `students_20260216_143000.csv`

**Import:** Click "Import CSV" button → Upload `new_students.csv` → System creates records → Shows "Created 15 records. 2 errors."

The CSV file contains headers matching model field names:
```csv
name,email,phone,batch,status
Rahul Kumar,rahul@example.com,9876543210,NEET-2025,ACTIVE
Priya Sharma,priya@example.com,9876543211,JEE-A,ACTIVE
```

### 11.3 Why This Feature Was Added

- **Bulk data entry** — Coaching institutes receive student registrations in batches (spreadsheets from partner schools, online forms). Importing CSV eliminates manual entry
- **Reporting** — Export student/attendance/test data for analysis in Excel, Google Sheets, or other tools
- **Backup** — Quick CSV export provides a human-readable backup of critical data
- **Migration** — Moving data between systems (e.g., old CS to new platform) uses CSV import
- **No developer needed** — Staff can import/export without any SQL or API knowledge

### 11.4 How It's Used — Real-Time Use Case

**Scenario: Monthly Student Import**
1. Marketing team collects new registrations in a Google Sheet
2. Exports as CSV → downloads `new_registrations.csv`
3. Opens Admin Console → **Students** changelist
4. Clicks **"Import CSV"** button (purple button in toolbar)
5. Uploads the CSV file
6. System processes it: "Created 23 records. 0 errors."
7. New students appear in the list immediately

**Scenario: Quarterly Report Export**
1. Director asks for a list of all active students with their batch assignments
2. Open **Batch Students** changelist
3. Click **"Export All CSV"** button (green button in toolbar)
4. Downloads `batchstudents_20260216_150000.csv`
5. Opens in Excel → creates pivot table by batch

### 11.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| Center Manager | Import new enrollments, export student lists | Would enter each record manually (20 minutes per batch of 50 students vs. 30 seconds with CSV import) |
| Academic Coordinator | Export question banks, import test configurations | Would need developer assistance for every bulk operation |
| Director/Owner | Export reports for board meetings | Would rely on someone else to generate reports |
| IT Administrator | Audit log export, system backup | Would need database-level export commands |

---

## 12. Bulk Status Actions

### 12.1 What Is This?

Three **bulk status actions** available in the action dropdown on every model:

| Action | Effect | Icon |
|--------|--------|------|
| **Activate Selected** | Sets `status='ACTIVE'` or `is_active=True` | ✅ |
| **Deactivate Selected** | Sets `status='INACTIVE'` or `is_active=False` | 🚫 |
| **Suspend Selected** | Sets `status='SUSPENDED'` | ⏸ |

### 12.2 Example

Select 5 delinquent students → Action: "🚫 Deactivate selected" → Go → "5 records deactivated." message appears → Status badges turn red "Inactive".

### 12.3 Why This Feature Was Added

- **Batch operations** — Activating/deactivating records one by one is impractical for 50+ records
- **Semester transitions** — At semester end, all batches need to be deactivated simultaneously
- **Fee defaulters** — Students with overdue fees can be suspended in bulk
- **Quick response** — If an issue is discovered (e.g., unauthorized teacher accounts), suspension can be applied immediately to all affected records

### 12.4 How It's Used — Real-Time Use Case

**Scenario: End of Semester**
1. Open **Batches** changelist
2. Select all batches from the previous semester (use checkbox at top to select all)
3. Action: "🚫 Deactivate selected" → Go
4. All selected batches become Inactive
5. New batches for next semester have already been created with Active status

### 12.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| Center Manager | Student/Batch management | Would need to open each record individually and toggle the status field — extremely time-consuming for 50+ records |
| Admin | User account management | Would need to write database queries to bulk-update status |

---

## 13. Color-Coded Status Badges

### 13.1 What Is This?

All status fields are displayed as **color-coded pill badges** instead of plain text. The system supports 14 status values plus boolean True/False:

| Status | Color | Badge |
|--------|-------|-------|
| ACTIVE | Green | `[Active]` with green background |
| INACTIVE | Red | `[Inactive]` with red background |
| SUSPENDED | Amber | `[Suspended]` with amber background |
| PENDING | Blue | `[Pending]` with blue background |
| DRAFT | Grey | `[Draft]` with grey background |
| PUBLISHED | Green | `[Published]` with green background |
| COMPLETED | Green | `[Completed]` with green background |
| CANCELLED | Red | `[Cancelled]` with red background |
| IN_PROGRESS | Amber | `[In Progress]` with amber background |
| SCHEDULED | Purple | `[Scheduled]` with purple background |
| LIVE | Red | `[Live]` with red background and pulse |
| OPEN | Green | `[Open]` with green background |
| CLOSED | Grey | `[Closed]` with grey background |
| RESOLVED | Green | `[Resolved]` with green background |
| True (boolean) | Green | `[Active]` |
| False (boolean) | Red | `[Inactive]` |

### 13.2 Example

In the Batch Students table:
```
│ Naveen Reddy  │ naveen@lms.com  │ NEET-2025 │ [Active]  │
│ Kavya Saxena  │ kavya@lms.com   │ JEE-A     │ [Active]  │
│ Amit Gupta    │ amit@lms.com    │ NEET-2025 │ [Inactive]│  ← red badge
```

The green "Active" and red "Inactive" badges are immediately visually distinguishable.

### 13.3 Why This Feature Was Added

- **Visual scanning** — In a table of 50 rows, spotting inactive records is instant with color badges vs. scanning text "ACTIVE"/"INACTIVE"
- **Status awareness** — Color conveys urgency: red = attention needed, green = healthy, amber = in progress
- **Professional appearance** — SaaS applications universally use color badges for status; plain text looks outdated
- **Consistency** — Every model uses the same badge system, creating a unified visual language across the admin

### 13.4 How It's Used

Status badges appear automatically on any model that has a `status` field or `is_active` field. No configuration needed — the `EnhancedModelAdmin` base class detects the field and applies badges via the `status_badge()` method.

### 13.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| All admin users | Every changelist with status columns | Users would see plain text like "ACTIVE" and "INACTIVE" — harder to scan, especially in large tables |

---

## 14. Keyboard Shortcuts

### 14.1 What Is This?

A set of **keyboard shortcuts** for power users, with a help panel accessible via `Shift+?`:

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` / `Cmd+K` | Focus the search bar |
| `G` then `D` | Navigate to Dashboard (`/admin/`) |
| `Shift+?` | Show/hide the keyboard shortcuts panel |
| `Escape` | Close any open modal or panel |

### 14.2 Example

Pressing `Shift+?` anywhere in the admin opens an overlay panel:

```
┌─────────────────────────────────────┐
│  ⌨ Keyboard Shortcuts              │
│                                     │
│  Search             [Ctrl + K]      │
│  Go to Dashboard    [G then D]      │
│  Show Shortcuts     [Shift + ?]     │
└─────────────────────────────────────┘
```

### 14.3 Why This Feature Was Added

- **Power-user productivity** — Regular admin users can navigate much faster with keyboard shortcuts
- **Modern UX convention** — Most SaaS tools (Slack, GitHub, Notion) provide `?` shortcut panels
- **Discoverability** — Users might not know about Ctrl+K without the panel listing all available shortcuts

### 14.4 How It's Used — Real-Time Use Case

**Scenario:** IT admin is investigating a login issue:
1. Presses `G` then `D` → navigates to dashboard instantly
2. From dashboard, clicks Login History in the sidebar
3. Presses `Ctrl+K` → searches for the user's email
4. Finds the login record quickly

### 14.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| Power admin users (IT, coordinators) | Any admin page | Would rely entirely on mouse navigation, which is slower for frequent users |

---

## 15. Toast Notifications

### 15.1 What Is This?

Django's success/warning/error messages are styled as **animated toast notifications** that:
1. Appear with a fade-in animation
2. Display for 5 seconds
3. Auto-dismiss with a fade-up animation
4. Use color-coded backgrounds: green (success), amber (warning), red (error)

### 15.2 Example

After saving a student record:
```
┌──────────────────────────────────────────────────────┐
│ ✓ The student "Naveen Reddy" was changed successfully │  ← green card
└──────────────────────────────────────────────────────┘
                       ↓ (auto-fades after 5 seconds)
```

### 15.3 Why This Feature Was Added

- **Non-intrusive feedback** — Messages confirm actions without blocking the interface
- **Auto-dismissal** — No need to manually close messages; they fade away naturally
- **Color coding** — Success (green), warning (amber), and error (red) messages are instantly recognizable

### 15.4 How It's Used

Toast notifications appear automatically whenever Django sends a message (after save, delete, import, export, etc.). No user action required — they appear and disappear on their own.

### 15.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| All admin users | After any save/delete/action | Messages would stay permanently on the page until the next navigation, cluttering the interface |

---

## 16. Admin Profile Dropdown

### 16.1 What Is This?

A **click-to-toggle dropdown menu** in the header showing:
- User avatar and name (with role label "Super Admin · ENABLE PROGRAM")
- **Theme selector** (Light / Dark / System)
- **Account links:** View Site, Dashboard, My Profile
- **Security links:** Change Password, Enable MFA, Manage Roles
- **Sign Out** button

### 16.2 Example

Clicking the user avatar in the header:
```
┌───────────────────────────────┐
│ 👤 Admin                      │
│    Super Admin · ENF Online   │
├───────────────────────────────┤
│ Theme                         │
│ [☀ Light] [🌙 Dark] [🖥 System]
├───────────────────────────────┤
│ Account                       │
│ 🌐 View Site                  │
│ 📊 Dashboard                  │
│ 👤 My Profile                 │
├───────────────────────────────┤
│ Security                      │
│ 🔑 Change Password            │
│ 🛡 Enable MFA                 │
│ 👥 Manage Roles               │
├───────────────────────────────┤
│ 🚪 Sign Out                   │
└───────────────────────────────┘
```

### 16.3 Why This Feature Was Added

- **Centralized settings** — All user-related actions in one place
- **Security access** — Quick links to change password and MFA settings encourage security best practices
- **Theme preference** — Users can switch themes without navigating away from their current page
- **Professional UX** — Standard pattern used by Google, Microsoft, and every modern SaaS admin panel

### 16.4 How It's Used — Real-Time Use Case

**Scenario:** New admin user's first day:
1. Logs in → sees the profile dropdown at top-right
2. Clicks profile → eyes drawn to "Change Password" → changes default password
3. Notices "Enable MFA" → sets up two-factor authentication
4. Tries "Dark" theme → decides to keep Light mode
5. Clicks "Dashboard" → explores the admin

### 16.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| All admin users | Header profile icon on every page | Users would need to navigate to `/admin/password_change/` manually; no integrated theme switching or security links |

---

## 17. Live Clock

### 17.1 What Is This?

A **real-time clock** displayed in the admin header bar, showing the current date and time in `en-IN` locale with 12-hour format. Updates every second.

### 17.2 Example

```
● Mon, 16 Feb, 2026, 10:30:15 AM
```

The green dot indicates the clock is live/updating. The format includes day name, date, and time with seconds.

### 17.3 Why This Feature Was Added

- **Time-sensitive operations** — Scheduling classes, setting exam dates/times, and marking attendance all require time awareness
- **Session awareness** — Admins can see how long they've been working without checking external clocks
- **Professional touch** — A live clock adds a dashboard-like feel to the admin console
- **No external tool needed** — Eliminates the need to check phone or desktop clock while working

### 17.4 How It's Used — Real-Time Use Case

**Scenario:** Academic coordinator is scheduling a live class:
1. Opens the Scheduled Classes form
2. Glances at the header clock → "Mon, 16 Feb, 2026, 10:45 AM"
3. Sets the class start time to 2:00 PM today
4. The clock helps verify the time is correct without checking another device

### 17.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| All admin users | Header bar on every page | No time reference within the admin; users would need to check system clock or phone to verify time-based entries |

---

## 18. Enhanced Form Layout

### 18.1 What Is This?

All Django admin forms (add/change pages) are styled with:
- **Card-style fieldsets** — Each section wrapped in a bordered card with a purple-tinted header
- **Row separators** — Light bottom borders between form rows for visual grouping
- **Purple focus rings** — Inputs glow with a purple box-shadow when focused
- **Native select dropdowns** — Preserved `menulist` appearance so selects work naturally (not custom-styled)
- **Related-widget fix** — Foreign key dropdowns with edit/add/view icons aligned in a row
- **Collapsible sections** — Django's built-in `collapse` fieldsets work with the theme
- **Save buttons at top and bottom** — `save_on_top=True` by default for long forms

### 18.2 Example

A student edit form:
```
┌────────────────────────────────────────────────┐
│  Personal Information                           │ ← purple-tinted header
├────────────────────────────────────────────────┤
│  FIRST NAME:     [Naveen            ]          │ ← purple focus ring on click
│ ──────────────────────────────────             │ ← subtle row separator
│  LAST NAME:      [Reddy             ]          │
│ ──────────────────────────────────             │
│  EMAIL:          [naveen@lms.com    ]          │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────┐
│  Academic Details                               │
├────────────────────────────────────────────────┤
│  BATCH:          [NEET-2025 ▾] ✏ ➕ 👁        │ ← FK with action icons
│ ──────────────────────────────────             │
│  STATUS:         [Active ▾]                    │
└────────────────────────────────────────────────┘
```

### 18.3 Why This Feature Was Added

- **Visual organization** — Card-style fieldsets group related fields clearly
- **Data entry efficiency** — Purple focus ring helps track which field is active
- **Consistent experience** — Same visual language as the table views and dashboard
- **Usability** — Native selects ensure dropdowns work on all browsers and devices

### 18.4 How It's Used

Form enhancements apply automatically to every add/change form in the admin. No configuration needed.

### 18.5 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| All admin users | Every add/change form | Users would see Django's plain, unstyled forms with no visual grouping or focus indicators |

---

## 19. Responsive Design

### 19.1 What Is This?

The admin console adapts to different screen sizes:

| Breakpoint | Changes |
|------------|---------|
| **> 1024px** | Full layout — sidebar, grid dashboard, full tables |
| **768px - 1024px** | Sidebar narrows to 220px, dashboard switches to single column |
| **< 768px** | Reduced content padding, smaller table cells, compact text |

### 19.2 Why This Feature Was Added

- **Tablet usage** — Center managers often use iPads during classroom walks to mark attendance or check schedules
- **Remote access** — Admins accessing the console from mobile devices during emergencies
- **Meeting presentations** — Dashboard stats displayed on tablets during board meetings

### 19.3 Who Uses It?

| Who | Where | What If Not Available |
|-----|-------|----------------------|
| Center managers | Tablet during classroom walks | Would need to pinch-zoom and scroll horizontally on small screens, making the admin unusable |

---

## 20. Registered Models & Apps

### 20.1 Complete App and Model List

The admin console manages **51 models across 12 apps**:

| App | Models | Key Purpose |
|-----|--------|-------------|
| **Accounts** | Student, Teacher, AdminUser, Parent, Role, Permission, RolePermission | User management and RBAC |
| **Academics** | AcademicSession, Group, Category, Subject, Chapter, Topic, Batch, BatchStudent, BatchTeacher, Language, State, City, Religion, School, SubjectSection | Core academic structure |
| **Classes** | YouTubeChannel, ScheduledClass, ClassAccessToken, ClassWatchTime | Live/recorded class management |
| **Assessments** | Test, TestSection, Question, TestAttempt, TestAttemptAnswer, TestFeedback, OfflineTestMarks | Testing and evaluation |
| **Attendance** | Attendance, AttendanceCorrectionRequest, AttendanceSummary | Attendance tracking |
| **Communication** | SupportTicket, TicketMessage, Announcement, AnnouncementRead, DirectMessage, Notification | Communication hub |
| **Materials** | StudyMaterial, MaterialAccess, PhotoGallery, Scholarship, TopperStudent | Learning resources |
| **Sessions Tracking** | UserDevice, UserSession, LoginHistory, UserActivity | Session and activity monitoring |
| **Audit** | AuditLog, AuditPurgePolicy, BackupPolicy, BackupHistory | Security and compliance |
| **System Config** | SystemSetting, FeatureFlag, MFAPolicy, MaintenanceWindow, FounderInfo, EnquiryForm, AIFeatureConfig, ClassLinkConfig, AttendanceRule | System configuration |
| **Realtime** | RealtimeEvent | Real-time event tracking |
| **Tenants** | Tenant | Multi-tenant management |

### 20.2 Models with Import/Export (22 models)

The following models have both **Import CSV** and **Export All CSV** toolbar buttons:

Student, Teacher, AdminUser, Parent, Subject, Batch, BatchStudent, School, ScheduledClass, Test, Question, OfflineTestMarks, Attendance, SupportTicket, Announcement, StudyMaterial, PhotoGallery, TopperStudent, FounderInfo, EnquiryForm, AIFeatureConfig, Tenant

### 20.3 How This Benefits Coaching Institutes

| Model | Real-World Use |
|-------|---------------|
| **Student** | Track all enrolled students with fees, batches, and contact info |
| **Batch** | Create batches like "NEET 2025 Batch A", "JEE Advanced 2026" with capacity limits |
| **BatchStudent** | Enroll students into batches — track who is in which batch |
| **ScheduledClass** | Schedule live YouTube classes with date, time, subject, and teacher |
| **Test** | Create and manage online/offline tests for each subject |
| **Attendance** | Daily attendance marking with present/absent/late/leave status |
| **Announcement** | Send school-wide or batch-specific announcements |
| **StudyMaterial** | Upload PDFs, videos, and notes for students to access |
| **SupportTicket** | Students/parents can raise queries; staff can track and resolve |

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total Registered Models | 51 |
| Total Django Apps | 12 |
| Models with Import/Export | 22 |
| CSS Theme Lines | ~770 |
| JavaScript Enhancement Lines | ~700 |
| Theme Options | 3 (Light / Dark / System) |
| Color-Coded Status Values | 14 + boolean |
| Keyboard Shortcuts | 4 |
| Responsive Breakpoints | 3 |
| Dashboard Statistics | 20+ |
| Admin Actions per Model | 4 (Export CSV, Export JSON, Activate, Deactivate) |

---

## 21. Sidebar Model Reference — Every Model in Detail

This section documents **every individual model** visible in the admin sidebar, organized by app section. Each entry describes what the model does, its admin features, a real-world coaching-institute example, and who uses it.

---

### 21.1 ACCOUNTS

The Accounts section manages all user types, their roles, and the permission system that controls what each user can do.

---

#### 21.1.1 Students

**What Is This?**

The central user record for every student enrolled at the coaching institute. Each student has a unique code (e.g., `STU2026001`), personal details, academic info (class level, exam target, stream), parent/guardian contacts, address, fee status, subscription details, notification preferences, and authentication data.

**Admin List Columns:** Student Code, Name (avatar + full name), Email, Phone, Class, Exam Target, Stream, Fee Status (colored badge), Status (colored badge), Created Date.

**Filters & Search:** Filter by Status, Class, Exam Target, Stream, Fee Status, Gender, Email Verified. Search by Student Code, First/Last Name, Email, Phone, Parent Name. Date hierarchy on Created Date.

**Available Actions:** Export as CSV, Export as JSON, Activate Selected, Deactivate Selected, Suspend Selected.

**Form Sections:** Identity (code, name, contact) → Academic (class, batch, exam target) → Fee & Financial (collapsed) → Parents/Guardian (collapsed) → Personal (collapsed, DOB/gender/blood group) → Address (collapsed) → Security & Auth (collapsed, MFA/password) → Communication (collapsed, notification channels) → Status & Timestamps.

**Import/Export:** Yes — CSV import for bulk enrollment, CSV/JSON export for reports.

**Example — Real-World Use Case**

A coaching institute receives 40 new JEE student registrations from a partner school via spreadsheet. The center manager imports the CSV with name, email, phone, class, and exam target. All 40 students are created in seconds. Each gets auto-assigned a student code. The manager then opens each batch (JEE-2025-A, JEE-2025-B) and assigns students through the BatchStudent model.

**Why This Model Exists**

Students are the primary users of the coaching platform. Every other feature — attendance, classes, tests, materials — references the student record. Without a structured student database, the institute would rely on spreadsheets or handwritten registers, making it impossible to track enrollment, fee status, or performance at scale.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Center Manager | Add/edit students, manage enrollment | Daily |
| Front Desk Staff | Search students by name/phone for inquiries | Multiple times daily |
| Accounts Team | Filter by Fee Status (Pending/Partial) to track dues | Weekly |
| Director | Export all students for enrollment reports | Monthly |

---

#### 21.1.2 Teachers

**What Is This?**

The user record for every teacher/instructor. Includes professional details (qualification, experience, department, employment type), YouTube channel integration (verified channel, permission to create streams), permissions (can edit student profiles, override attendance/scores), and financial info (bank details for salary).

**Admin List Columns:** Teacher Code, Name (green avatar + full name), Email, Phone, Employment Type, Department, YouTube Verified (red badge), Status, Created Date.

**Filters & Search:** Filter by Status, Employment Type, YouTube Verified, Email Verified, Can Create Streams. Search by Teacher Code, First/Last Name, Email, Phone.

**Available Actions:** Export as CSV, Export as JSON, Activate Selected, Deactivate Selected, Suspend Selected.

**Form Sections:** Identity → Professional (employment type, subjects, qualification, experience) → YouTube (collapsed, channel ID, verified status) → Permissions (collapsed, what teacher can do) → Contact (collapsed, personal details) → Security (collapsed) → Timestamps.

**Import/Export:** Yes.

**Example — Real-World Use Case**

The institute hires 3 new part-time physics teachers for the upcoming JEE batch. The academic coordinator creates their records, sets employment type to "Part-Time", and assigns their YouTube channels. Once youtube_channel_verified is set to True, the teachers can start live-streaming classes through the platform.

**Why This Model Exists**

Teachers drive the educational content — they conduct live classes, create tests, upload study materials, and mark attendance. A structured teacher record with YouTube integration, subject expertise, and granular permissions ensures each teacher can only access features relevant to their role.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Academic Coordinator | Add new teachers, assign subjects/batches | As needed |
| HR/Admin | Track employment type, manage bank details | Monthly |
| IT Admin | Verify YouTube channels, manage permissions | As needed |

---

#### 21.1.3 Admins

**What Is This?**

The user record for administrative staff. Each admin has an admin type (Super Admin, Tenant Admin, Branch Admin, Academic Admin, Finance Admin, Support Admin), a linked Role for RBAC, IP whitelist settings, session timeout configuration, theme/accent color preferences, and security controls (failed login lockout).

**Admin List Columns:** Admin Code, Name (amber avatar), Email, Admin Type (color-coded: Super=red, Tenant=amber, Branch=blue, Academic=green, Finance=purple, Support=cyan), Role (shield icon + name), Status, Created Date.

**Filters & Search:** Filter by Status, Admin Type, Role. Search by Admin Code, First/Last Name, Email.

**Available Actions:** Export as CSV, Export as JSON, Activate Selected, Deactivate Selected.

**Form Sections:** Identity → Role & Access Control (admin type, role, permissions override, managed branches) → Security (collapsed, MFA, IP whitelist, session timeout) → Preferences (collapsed, theme/accent/timezone) → Status.

**Example — Real-World Use Case**

The institute director creates a new "Academic Admin" for the chemistry department. The admin type is set to ACADEMIC_ADMIN, assigned the "Academic Coordinator" role, and managed_branches limited to "Main Campus". This admin can now manage batches, subjects, and tests but cannot access financial data or system settings.

**Why This Model Exists**

Different staff members need different levels of access. A front desk receptionist should not access financial reports. An academic coordinator should not modify system settings. The admin model, combined with admin types and RBAC roles, enforces principle of least privilege.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Super Admin | Create/manage other admin accounts | As needed |
| IT Admin | Set IP whitelists, session timeouts, MFA | During setup |

---

#### 21.1.4 Parents

**What Is This?**

The user record for student parents/guardians. Links to a primary student, stores relationship type (Father/Mother/Guardian), and has toggles for what the parent can view (attendance, results, fee details) and whether they receive notifications.

**Admin List Columns:** Parent Code, First Name, Last Name, Email, Relationship, Status.

**Filters & Search:** Filter by Status, Relationship. Search by Parent Code, First/Last Name, Email.

**Available Actions:** Export as CSV, Export as JSON, Activate Selected, Deactivate Selected.

**Example — Real-World Use Case**

When a new student enrolls, the front desk creates a parent record linked to the student. The parent can then log in to view their child's attendance, test results, and fee dues. If a parent requests to stop receiving SMS notifications, the center manager unsets notification_sms on their record.

**Why This Model Exists**

Parental engagement significantly impacts student outcomes. By giving parents a structured account with controlled access, the institute provides transparency (attendance & results) while maintaining privacy (parents only see their own child's data).

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Front Desk Staff | Create parent accounts during enrollment | During enrollment |
| Center Manager | Toggle parent notification preferences | As requested |

---

#### 21.1.5 Roles

**What Is This?**

Defines named roles within the RBAC (Role-Based Access Control) system. Each role has a code, name, type (System/Tenant Default/Custom), applies-to scope (Admin/Teacher/Student/Parent/All), hierarchy level (0–100), and optional parent role for permission inheritance.

**Admin List Columns:** Code, Name, Type Badge (System=red, Tenant Default=amber, Custom=purple), Applies To Badge, Level (monospace with color), Parent Role (arrow display), Permission Count (direct + inherited), Active Badge.

**Filters & Search:** Filter by Role Type, Applies To, Is Active. Search by Code, Name.

**Inline:** RolePermission inline — add permissions directly from the Role edit page.

**Available Actions:** Export as CSV, Activate Selected, Deactivate Selected.

**Form Sections:** Role Identity (code, name, description) → Classification (type, applies to, level) → Inheritance (parent role — with description about permission flow) → Status.

**Example — Real-World Use Case**

The institute defines roles like "Head Teacher" (level 80, applies to TEACHER, parent: "Teacher"), "Junior Teacher" (level 50, parent: "Teacher"), and "Academic Coordinator" (level 70, applies to ADMIN). The Head Teacher inherits all Teacher permissions plus additional ones like "Override Attendance" and "View All Batch Results". The permission count column shows "12 direct + 8 inherited = 20 total".

**Why This Model Exists**

Without roles, each admin/teacher would need permissions assigned individually. Roles provide template-based access control — assign a role and the user gets all associated permissions. The hierarchy (parent role) enables permission inheritance, reducing duplication.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Super Admin | Define and modify role hierarchy | During setup, quarterly review |
| IT Admin | Assign permissions to roles | As needed |

---

#### 21.1.6 Permissions

**What Is This?**

Defines granular actions a user can perform. Each permission has a unique code (e.g., `students.read.own`), module (Students, Tests, Attendance), category, action (Create/Read/Update/Delete/Execute/Approve/Export), and scope (Own/Batch/Branch/Tenant/Global).

**Admin List Columns:** Code, Name, Module Badge, Category Badge, Action Badge (Create=green, Read=blue, Update=amber, Delete=red, Execute=purple, Approve=cyan, Export=gray), Scope Badge, Active Badge.

**Filters & Search:** Filter by Module, Action, Scope, Is Active. Search by Code, Name, Description. 50 records per page.

**Available Actions:** Export as CSV, Export as JSON, Activate Selected, Deactivate Selected.

**Example — Real-World Use Case**

The permission `attendance.update.batch` allows a teacher to update attendance records for students in their assigned batch. A teacher with `attendance.update.own` can only mark their own attendance. A Super Admin has `attendance.update.global` to modify any attendance record. This granularity ensures teachers cannot modify other batches' attendance.

**Why This Model Exists**

Permissions are the building blocks of RBAC. They define the atomic actions possible in the system. Combined with Roles (which bundle permissions), they create a flexible access control system suitable for organizations with different staff levels and responsibilities.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Super Admin | Review and audit permission definitions | Quarterly |
| IT Admin | Create new permissions when features are added | During development |

---

#### 21.1.7 Role Permissions

**What Is This?**

The many-to-many junction table linking Roles and Permissions. Each record says "Role X has Permission Y".

**Admin List Columns:** Role, Permission, Created Date.

**Filters & Search:** Filter by Role. Search by Role Name, Permission Code, Permission Name. Raw ID fields for Role and Permission for fast lookup.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

To give the "Academic Coordinator" role permission to export test data, the admin creates a RolePermission record linking Role="Academic Coordinator" to Permission="tests.export.tenant". Any admin assigned the "Academic Coordinator" role immediately gains this permission.

**Why This Model Exists**

This is the junction table that makes RBAC work. It's the actual "assignment" of permissions to roles. While most permission management happens through the Role inline, this standalone view is useful for auditing ("show me every role-permission assignment") and bulk management.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Super Admin | Audit permission assignments | During security reviews |
| IT Admin | Bulk assign/remove permissions | As needed |

---

### 21.2 ACADEMICS

The Academics section defines the educational structure — sessions, subjects, chapters, batches, and reference data that other features (classes, tests, attendance) depend on.

---

#### 21.2.1 Academic Sessions

**What Is This?**

Represents an academic year or term (e.g., "2025-2026", "Summer Intensive 2026"). Has start/end dates, an `is_current` flag (green "Current" badge), and status. Only one session should be marked current at a time — it's used as the default context for attendance, batches, and tests.

**Admin List Columns:** Session Name, Current Badge (green dot), Status Badge, Start Date, End Date.

**Filters & Search:** Filter by Is Current, Status.

**Available Actions:** Export as CSV, Export as JSON, Activate Selected, Deactivate Selected.

**Example — Real-World Use Case**

At the start of a new academic year (April 2026), the center manager creates a new session "2026-2027", sets `is_current=True`, and deactivates the previous session "2025-2026". All new batches and attendance records are now linked to the current session.

**Why This Model Exists**

Academic sessions are the top-level time boundary. They allow the system to distinguish data from different years — "How many students were in Session 2024-2025 vs. 2025-2026?" — and prevent mixing of cross-year data in reports.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Center Manager | Create new session, toggle current flag | Annually (April/June) |
| Academic Coordinator | Reference when creating batches | Start of each session |

---

#### 21.2.2 Groups

**What Is This?**

A top-level organizational grouping for academic content. Groups can represent branches, departments, or content divisions (e.g., "Main Campus", "Online Division", "JEE Wing", "NEET Wing").

**Admin List Columns:** Name, Status Badge.

**Available Actions:** Export as CSV, Activate Selected, Deactivate Selected.

**Example — Real-World Use Case**

An institute with two branches creates groups "Main Campus" and "Satellite Center". Categories, subjects, and chapters can be linked to a specific group, ensuring branch-specific content organization.

**Why This Model Exists**

Groups provide a high-level organizational layer. Multi-branch institutes need to segment their academic content by location or division. Groups serve as the parent for Categories and can be linked to Batches and Chapters.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Director | Define organizational groups | During setup |
| Academic Coordinator | Assign groups to batches/content | As needed |

---

#### 21.2.3 Categories

**What Is This?**

Sub-groupings within a Group (e.g., under "JEE Wing" → categories "IIT Toppers", "Foundation Batch", "Dropper Batch"). Has a `show_in_student` flag controlling visibility on the student-facing side.

**Admin List Columns:** Name, Group, Status Badge, Show in Student.

**Filters & Search:** Filter by Status, Show in Student.

**Example — Real-World Use Case**

The academic coordinator creates categories "Foundation" and "Advanced" under the "JEE Wing" group. Foundation-level content and batches are tagged with this category. The `show_in_student=True` setting makes the category visible in the student portal's navigation.

**Why This Model Exists**

Categories provide a second level of content organization under Groups. They help classify batches, content, and scheduling in ways that map to how coaching institutes naturally organize — by student level, program type, or specialization.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Academic Coordinator | Create/manage categories | Start of session |

---

#### 21.2.4 Subjects

**What Is This?**

The subject/course taught at the institute (Physics, Chemistry, Mathematics, Biology). Each has a name, code, type (Theory/Practical/Both), display order, icon URL, and color for frontend display. The Chapters inline on the edit form shows all chapters under the subject.

**Admin List Columns:** Name, Code, Subject Type Badge (Theory=blue, Practical=green, Both=purple), Status Badge.

**Filters & Search:** Filter by Subject Type, Status. Search by Name, Code.

**Inline:** ChapterInline — view and add chapters directly within the Subject edit form.

**Available Actions:** Export as CSV, Export as JSON, Activate Selected, Deactivate Selected.

**Import/Export:** Yes.

**Example — Real-World Use Case**

The academic coordinator creates "Physics" (code: PHY, type: THEORY), "Chemistry" (code: CHM, type: BOTH — theory + practical), and "Biology" (code: BIO, type: THEORY). Each subject gets an icon and color for the student app. Chapters are added inline — Physics gets "Mechanics", "Thermodynamics", "Optics", etc.

**Why This Model Exists**

Subjects are the foundation of all academic content. Every chapter, topic, test, scheduled class, and study material references a subject. Without structured subject records, content would be unlinked and unorganized.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Academic Coordinator | Add subjects, define types | During initial setup |
| Teachers | View subject assignments | As needed |

---

#### 21.2.5 Chapters

**What Is This?**

Divisions within a Subject (e.g., Physics → Mechanics, Thermodynamics, Optics). Each chapter has a name, class level (9/10/11/12), display order, estimated hours, weightage (importance percentage for exam), and links to Session, Group, and Subject. The Topics inline shows all topics within the chapter.

**Admin List Columns:** Name, Subject, Class Level, Display Order, Status Badge.

**Filters & Search:** Filter by Subject, Status. Search by Name.

**Inline:** TopicInline — view and add topics directly within the Chapter edit form.

**Available Actions:** Export as CSV, Activate Selected, Deactivate Selected.

**Example — Real-World Use Case**

Under Physics, the coordinator creates chapters ordered by teaching sequence: "Units & Measurements" (order 1, Class 11, 3 hrs), "Motion in a Straight Line" (order 2, Class 11, 5 hrs), ..., "Optics" (order 15, Class 12, 8 hrs, weightage 8%). This ordering drives the curriculum schedule and helps teachers plan classes in sequence.

**Why This Model Exists**

Chapters break subjects into teachable units. They define what is covered in scheduled classes, what topics tests cover, and how study materials are organized. The weightage field helps prioritize high-value chapters for exam preparation.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Academic Coordinator | Define chapter sequence per subject | Start of session |
| Teacher | Reference when scheduling classes/tests | Before each class |

---

#### 21.2.6 Topics

**What Is This?**

The finest granularity of academic content — subdivisions within a Chapter (e.g., Mechanics → Newton's Laws, Friction, Work-Energy Theorem). Each topic has a name, display order, weightage, and status.

**Admin List Columns:** Name, Chapter, Display Order, Status Badge.

**Filters & Search:** Filter by Status. Search by Name.

**Available Actions:** Export as CSV, Activate Selected, Deactivate Selected.

**Example — Real-World Use Case**

The chapter "Mechanics" has topics: "Newton's First Law" (order 1), "Newton's Second Law" (order 2), "Friction" (order 3), "Work-Energy Theorem" (order 4). When a teacher schedules a class, they can tag it to a specific topic. Test questions are also tagged to topics, enabling topic-level performance analysis.

**Why This Model Exists**

Topics enable fine-grained content mapping. Instead of just knowing "the student scored 60% in Mechanics", the system can show "the student is weak in Friction but strong in Newton's Laws". This powers targeted revision recommendations and question-level analytics.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Academic Coordinator | Define topics per chapter | Start of session |
| Teacher | Tag classes and questions to topics | Per class/test creation |

---

#### 21.2.7 Batches

**What Is This?**

A group of students studying together (e.g., "NEET 2025 Batch A", "JEE Advanced Dropper Batch"). Batches have a code, name, exam target, max student capacity, start/end dates, and status (Active/Inactive/Completed/Archived). The edit form includes BatchStudent and BatchTeacher inlines for managing enrollment and teacher assignments directly.

**Admin List Columns:** Code, Name, Exam Target, Max Students, Student Count (color-coded: green if < 80% full, amber if 80-95%, red if > 95%), Status Badge.

**Filters & Search:** Filter by Status, Exam Target. Search by Code, Name.

**Inlines:** BatchStudent inline (student, is_active, enrolled_at), BatchTeacher inline (teacher, subject, is_primary).

**Available Actions:** Export as CSV, Export as JSON, Activate Selected, Deactivate Selected.

**Import/Export:** Yes.

**Example — Real-World Use Case**

The academic coordinator creates "NEET-2025-A" with max_students=50. Students are enrolled via the BatchStudent inline — the student count display shows "32/50" in green. When enrollment reaches 48/50, the count turns amber. Teachers are assigned with subjects: "Dr. Sharma → Physics (Primary)", "Dr. Patel → Chemistry (Primary)", "Mr. Gupta → Biology".

**Why This Model Exists**

Batches are the operational unit of a coaching institute. Scheduling, attendance, tests, and access control all revolve around batches. A student in "NEET-2025-A" sees only classes, materials, and tests assigned to that batch.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Academic Coordinator | Create batches, manage capacity | Start of session |
| Center Manager | Monitor enrollment (student count vs. capacity) | Weekly |
| Teacher | View their assigned batches and subjects | Daily |

---

#### 21.2.8 Batch Students

**What Is This?**

The enrollment record linking a Student to a Batch. Tracks when the student was enrolled, who enrolled them, whether the enrollment is active, and removal details if applicable.

**Admin List Columns:** Batch, Student, Active Badge, Enrolled At.

**Filters & Search:** Filter by Is Active, Batch. Search by Student Name, Batch Name.

**Available Actions:** Export as CSV, Export as JSON.

**Import/Export:** Yes — bulk enrollment via CSV.

**Example — Real-World Use Case**

After the entrance test results, the coordinator needs to enroll 35 students into "JEE-2025-A". They prepare a CSV with batch code and student code columns, then import via "Import CSV". All 35 enrollments are created with is_active=True and the current timestamp as enrolled_at.

**Why This Model Exists**

Students can be in multiple batches (e.g., main batch + special doubt-clearing batch). The separate enrollment model supports this many-to-many relationship while tracking enrollment date and active status independently for each assignment.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Center Manager | Enroll students, deactivate withdrawn students | During enrollment periods |
| Academic Coordinator | Review batch composition | Monthly |

---

#### 21.2.9 Batch Teachers

**What Is This?**

The assignment record linking a Teacher to a Batch for a specific Subject. The `is_primary` flag indicates the main teacher for that subject in the batch (shown with a star "Primary" badge).

**Admin List Columns:** Batch, Teacher, Subject, Primary Badge (star icon).

**Filters & Search:** Filter by Is Primary.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

For batch "NEET-2025-A": "Dr. Sharma → Physics (Primary)", "Ms. Roy → Physics (substitute, not primary)", "Dr. Patel → Chemistry (Primary)". When scheduling a Physics class for this batch, the system knows Dr. Sharma is the primary teacher. If Dr. Sharma is unavailable, Ms. Roy can be assigned as substitute.

**Why This Model Exists**

Knowing which teacher teaches which subject in which batch is critical for scheduling, attendance assignment, and reporting. The primary flag distinguishes the main teacher from substitutes or assistants.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Academic Coordinator | Assign teachers to batches/subjects | Start of session |
| Center Manager | View teacher load (how many batches per teacher) | Monthly |

---

#### 21.2.10 Languages

**What Is This?**

Reference data for languages (English, Hindi, Tamil, Telugu, etc.). Each has a name and unique code. Used for student medium preferences and content localization.

**Admin List Columns:** Name (via `__str__`).

**Search:** By name.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

The institute adds "Hindi" (code: hi), "English" (code: en), and "Telugu" (code: te). Students whose medium is "Hindi" are shown Hindi-language content where available.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Add languages during setup | One-time |

---

#### 21.2.11 States

**What Is This?**

Indian state reference data (e.g., Telangana, Maharashtra, Karnataka). Used for student addresses, school locations, and teacher addresses.

**Admin List Columns:** Name (via `__str__`).

**Search:** By name.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

Pre-populated with all 28 Indian states and 8 union territories. When adding a student's address, the state dropdown references this table.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Pre-populate during setup | One-time |

---

#### 21.2.12 Cities

**What Is This?**

City reference data linked to a State (e.g., "Hyderabad, Telangana"). Displays as "city_name, state_name".

**Admin List Columns:** Name (via `__str__`, shows "City, State").

**Search:** By name.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

When a student registers from Hyderabad, the city dropdown shows "Hyderabad" under "Telangana". The institute can filter students by city to understand geographic distribution.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Add cities per state | During setup, as needed |

---

#### 21.2.13 Religions

**What Is This?**

Religion reference data. Used for school categorization and optional student demographics.

**Admin List Columns:** Name (via `__str__`).

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

Used to categorize schools by religion affiliation (e.g., government, private, aided by specific religious organizations).

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Pre-populate during setup | One-time |

---

#### 21.2.14 Schools

**What Is This?**

School reference data — the schools students previously attended or are currently enrolled in. Each school has a name, religion, state, city, school type (Government/Private/Aided), and status.

**Admin List Columns:** Name (via `__str__`).

**Search:** By name.

**Available Actions:** Export as CSV, Export as JSON.

**Import/Export:** Yes — bulk import school lists.

**Example — Real-World Use Case**

The institute has partnerships with 50 schools across the city. All schools are imported via CSV. When a student enrolls, their school_name field can reference this list. The director can run a report: "How many students came from Government schools vs. Private schools?" to optimize outreach strategy.

**Why This Model Exists**

School data helps track feeder institutions (where students come from), plan outreach, and segment student demographics. Import/Export support makes it easy to maintain a large school database.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Center Manager | Add new feeder schools | As new partnerships form |
| Marketing Team | Export school lists for outreach campaigns | Quarterly |

---

#### 21.2.15 Subject Sections

**What Is This?**

Subdivisions within a subject (e.g., Physics → "Mechanics Section", "Electrostatics Section"). A lighter grouping than chapters — used for test section organization where a test may cover "Section A: Mechanics" and "Section B: Thermodynamics".

**Admin List Columns:** Name (via `__str__`).

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

A JEE mock test has sections: "Physics Section A", "Physics Section B", "Chemistry Section A". SubjectSections define these divisions at the subject level, and TestSections reference them.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Academic Coordinator | Define subject sections for test organization | During test design |

---

### 21.3 ASSESSMENTS

The Assessments section manages all testing — test creation, question banks, student attempts, scoring, feedback, and offline test records.

---

#### 21.3.1 Tests

**What Is This?**

A complete examination or quiz. Supports 10 test types (Practice, Mock Exam, Chapter Test, Unit Test, Weekly, Monthly, Final, Scholarship, Diagnostic, Custom), multiple exam targets (JEE Mains, JEE Advanced, NEET, Boards, Olympiad), difficulty levels, duration, marking scheme (+4/−1 configurable), result display modes, and proctoring settings (tab switch detection, copy-paste prevention, webcam).

**Admin List Columns:** Test Code, Title, Type Badge (Practice=blue, Mock=purple, Live=red, Assignment=amber, Quiz=green), Exam Target, Status Badge, Total Marks, Duration (hours+minutes format), Start Date/Time.

**Filters & Search:** Filter by Status, Test Type, Exam Target, Difficulty Level. Search by Test Code, Title. Date hierarchy on Start Date/Time.

**Inline:** TestSectionInline — add sections (section name, order, question count, max marks) directly.

**Available Actions:** Export as CSV, Export as JSON, Activate Selected, Deactivate Selected.

**Import/Export:** Yes.

**Example — Real-World Use Case**

The physics teacher creates a weekly test: Test Code "PHY-W-2026-08", Type "WEEKLY", Exam Target "JEE_MAINS", Duration 60 minutes, Total Marks 120, Positive marks +4, Negative marks −1. Two sections are added inline: "Section A: MCQ Single" (20 questions, 80 marks) and "Section B: Numerical" (10 questions, 40 marks). The test is set to "SCHEDULED" status with a start datetime of next Monday 10 AM.

**Why This Model Exists**

Tests are the primary assessment mechanism. The comprehensive configuration (proctoring, marking schemes, result modes, multiple sections) mirrors the complexity of real competitive exams like JEE and NEET, ensuring students get realistic practice.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Teacher | Create tests, configure marking schemes | Weekly |
| Academic Coordinator | Review test schedule, ensure coverage | Weekly |
| Director | View test completion statistics | Monthly |

---

#### 21.3.2 Test Sections

**What Is This?**

Divisions within a test (e.g., "Section A: MCQ" with 30 questions worth 120 marks, "Section B: Numerical" with 10 questions worth 40 marks). Each section can have its own question count, mandatory questions, max marks, optional duration, subject, and instructions.

**Admin List Columns:** Test, Section Name, Section Order, Total Questions, Max Marks.

**Filters & Search:** Filter by Test.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

A NEET mock test has 4 sections matching the real exam: "Physics" (45 questions, 180 marks), "Chemistry" (45 questions, 180 marks), "Botany" (45 questions, 180 marks), "Zoology" (45 questions, 180 marks). Each section has its own timer (45 minutes) and instructions.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Teacher | Define test structure (usually via inline on Test) | Per test creation |

---

#### 21.3.3 Questions

**What Is This?**

Individual test questions with support for 9 question types (MCQ Single, MCQ Multi, Numerical, True/False, Fill Blank, Subjective, Matrix Match, Assertion-Reason, Comprehension). Each question has text (plain + HTML), up to 5 options with optional images, correct answer, explanation, marks (positive/negative/partial), subject/chapter/topic tags, difficulty level, and performance statistics (total attempts, correct attempts, success rate).

**Admin List Columns:** Question Code, Type Badge, Difficulty Badge (Easy=green, Medium=amber, Hard=red), Subject, Test, Active Badge.

**Filters & Search:** Filter by Question Type, Difficulty, Is Active, Subject. Search by Question Code, Question Text. 30 records per page.

**Available Actions:** Export as CSV, Export as JSON, Activate Selected, Deactivate Selected.

**Import/Export:** Yes — bulk import question banks from CSV.

**Example — Real-World Use Case**

The chemistry teacher imports 200 organic chemistry questions from a CSV (question text, options A-D, correct answer, difficulty, chapter). Each question gets auto-tagged to the "Organic Chemistry" chapter. When creating a new weekly test, the coordinator selects questions from this bank. After students attempt the test, each question's success_rate field auto-updates, helping identify questions that are too easy or too hard.

**Why This Model Exists**

A centralized question bank is essential for large-scale test creation. Tagging questions to subjects, chapters, topics, and difficulty levels enables automatic test generation (pick 10 Medium Physics questions from "Optics" chapter). Performance statistics enable question quality analysis.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Teacher | Create/import questions, tag to topics | Weekly |
| Academic Coordinator | Review question bank coverage | Monthly |

---

#### 21.3.4 Test Attempts

**What Is This?**

A student's attempt at a test. Tracks timing (started, submitted, time taken), performance (total/attempted/correct/incorrect/skipped/marked for review), scoring (raw score, percentage, rank, percentile, result), proctoring violations (tab switches, copy-paste attempts), and completion status.

**Admin List Columns:** Test, Student, Attempt Number, Status Badge, Score (bold), Percentage (color-coded: ≥60% green, ≥33% amber, <33% red), Result Badge.

**Filters & Search:** Filter by Status, Result. Search by Student Name, Test Title.

**Available Actions:** Export as CSV, Export as JSON.

**Example — Real-World Use Case**

After a weekly physics test closes, the coordinator opens Test Attempts filtered by that test. They see 45 students attempted, 42 submitted, 3 auto-submitted (time ran out). Average percentage: 56%. Two students flagged with proctoring violations (tab switches > 3) — the coordinator reviews and decides whether to invalidate those attempts.

**Why This Model Exists**

Test attempts are the raw performance data. They enable per-student, per-test analysis. The proctoring fields (tab switch count, copy-paste attempts, auto-terminated flag) help maintain test integrity in online assessments.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Teacher | Review student performance per test | After each test |
| Academic Coordinator | Identify at-risk students (low scores) | Weekly |
| Director | Aggregate pass/fail counts for reporting | Monthly |

---

#### 21.3.5 Test Attempt Answers

**What Is This?**

Individual question-level answers within a test attempt. Each record shows what the student answered, whether it was correct, marks awarded, time spent (seconds), visit count, and answer change count.

**Admin List Columns:** Attempt, Question, Status Badge, Correct Badge, Marks Awarded, Time Spent (seconds).

**Filters & Search:** Filter by Status, Is Correct.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

A teacher wants to understand why a student scored low on "Optics" questions. They open Test Attempt Answers, filter by the student's attempt, and see: Question 15 (Optics, time spent: 180s, answered B, correct A, incorrect). Question 16 (Optics, time spent: 5s, skipped). The high time on Q15 suggests confusion; the skip on Q16 suggests unfamiliarity. This guides targeted revision.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Teacher | Analyze question-level performance | After tests |
| Academic Coordinator | Identify commonly failed topics | Monthly |

---

#### 21.3.6 Test Feedbacks

**What Is This?**

Student feedback about a test — overall rating, difficulty rating, clarity rating, and free-text comments. Linked to the test, student, and optionally the specific attempt.

**Admin List Columns:** Test, Student, Overall Rating, Difficulty Rating.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

After a mock exam, 30 students submit feedback. The coordinator sees the average difficulty rating is 4.5/5 (too hard). Comments mention "not enough time for Section B" and "one question had a wrong answer key". The coordinator uses this feedback to adjust future tests.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Academic Coordinator | Review test quality based on feedback | After each major test |

---

#### 21.3.7 Offline Test Marks

**What Is This?**

Marks from tests conducted outside the platform (pen-and-paper exams, lab practicals). Each record links a student to a test name, date, total marks, marks obtained, percentage, grade, and remarks. Entries are verified by a second party (entered_by + verified_by).

**Admin List Columns:** Student, Test Name, Test Date, Marks Obtained, Total Marks, Percentage (color-coded).

**Available Actions:** Export as CSV, Export as JSON.

**Import/Export:** Yes — bulk import offline marks from CSV.

**Example — Real-World Use Case**

The institute conducts a pen-and-paper monthly test. The teacher enters marks for 50 students: student Naveen scored 78/100 (78%, grade A). The head teacher verifies the entries (verified_by is set). These marks appear in the student's overall performance dashboard alongside online test scores.

**Why This Model Exists**

Not all assessment happens online. Coaching institutes still conduct physical tests, practicals, and viva examinations. Offline test marks ensure the system has a complete picture of student performance across both online and offline assessments.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Teacher | Enter marks after offline tests | After each offline test |
| Head Teacher | Verify entered marks | After each entry batch |

---

### 21.4 ATTENDANCE

The Attendance section tracks daily presence/absence for students and teachers, supports correction workflows, and provides monthly summary statistics.

---

#### 21.4.1 Attendances

**What Is This?**

Individual daily attendance records. Each record tracks: user type (Student/Teacher), user ID, date, status (Present/Absent/Late/Half Day/Leave/Holiday/Excused) with colored icons, source (Manual/Live Class/Biometric/QR Code/Geofence/System), check-in/out times, live class watch data (duration seconds, watch percentage with progress bar), who marked it, and correction history.

**Admin List Columns:** User Type Badge (Student=blue, Teacher=green), User ID (truncated monospace), Date, Status (colored with icon: Present=✅ green, Absent=❌ red, Late=⏰ amber, Leave=🏖 purple), Source Badge (with icons), Batch, Check-in (green time), Check-out (red time), Watch % (progress bar with duration), Corrected Badge (amber with original status tooltip).

**Filters & Search:** Filter by User Type, Status, Source, Is Corrected, Date. Search by User ID. Date hierarchy on Attendance Date. 50 records per page.

**Available Actions:** Export as CSV, Export as JSON, ✅ Mark selected as Present, ❌ Mark selected as Absent, ⏰ Mark selected as Late, 🏖 Mark selected as Leave.

**Form Sections:** Attendance Record (user, batch, date, session) → Status (status, check-in/out, source, remarks) → Live Class Auto-Capture (collapsed, live class link, watch duration/percentage) → Audit Trail (collapsed, marked by/at) → Correction History (collapsed, original status, corrected by, reason).

**Example — Real-World Use Case**

**Scenario 1 — Auto-attendance from live class:** A physics class runs from 10 AM to 11 AM on YouTube. 35 students join. The system auto-marks attendance based on watch percentage: students watching > 70% get "Present" (source: LIVE_CLASS), students watching 30-70% get "Late", and students watching < 30% get "Absent". The attendance record shows the progress bar: "Naveen — 85% (51 min)" in green.

**Scenario 2 — Manual bulk marking:** For a physical doubt-clearing session (no live class), the teacher opens Attendance, selects all 30 students present, and uses Action "✅ Mark selected as Present". Three absent students remain as "Absent".

**Why This Model Exists**

Attendance is a legal and operational requirement for coaching institutes. Parents expect attendance tracking. The model supports multiple sources (manual, live class auto-capture, biometric) to accommodate both online and offline class formats.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Teacher | Mark daily attendance, review auto-captured records | Daily |
| Center Manager | Review attendance trends, handle correction requests | Daily |
| Parent | Views child's attendance (via parent portal) | Weekly |

---

#### 21.4.2 Attendance Correction Requests

**What Is This?**

Requests to change an existing attendance record (e.g., "I was marked Absent but I was present, here's proof"). Each request links to an attendance record, specifies the requested new status, a reason, optional supporting document URL, and review status (Pending/Approved/Rejected).

**Admin List Columns:** Attendance, Requested Status Badge, Reason (truncated to 60 chars), Request Status Badge (Pending=amber, Approved=green, Rejected=red), Created Date.

**Filters & Search:** Filter by Status, Requested Status. Search by Reason.

**Available Actions:** Export as CSV, Approve Corrections (batch approve, auto-updates attendance with audit trail), Reject Corrections (batch reject).

**Example — Real-World Use Case**

A student was marked "Absent" for Monday's class, but they were actually present and have a screenshot of the live class. They submit a correction request with requested_status="PRESENT" and attach the screenshot. The coordinator sees the request, verifies the screenshot, selects the request, and uses Action "Approve Corrections". The original attendance record is updated: status changes to "Present", is_corrected=True, original_status="ABSENT", corrected_by and correction_reason are auto-filled.

**Why This Model Exists**

Automated attendance isn't perfect — network issues, late joins, or system errors can cause incorrect markings. The correction workflow provides an auditable process (request → review → approve/reject) instead of teachers silently editing records.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Student/Teacher | Submit correction requests (via portal) | As needed |
| Center Manager | Review and approve/reject corrections | Daily |

---

#### 21.4.3 Attendance Summaries

**What Is This?**

Pre-calculated monthly attendance statistics per user. Shows total working days, present/absent/late/half-day/leave/holiday counts, and overall percentage with a color-coded progress bar (≥75% green, ≥50% amber, <50% red).

**Admin List Columns:** User Type Badge, User ID (truncated), Month/Year (calendar icon + "Feb 2026"), Working Days, Present (green badge), Absent (red badge), Late (amber badge), Leave (purple badge), Attendance % (progress bar with color).

**Filters & Search:** Filter by User Type, Year, Month. Search by User ID.

**Available Actions:** Export as CSV, Export as JSON.

**Example — Real-World Use Case**

At month-end, the center manager opens Attendance Summaries filtered by Month=February, Year=2026. They sort by attendance percentage ascending to find the lowest-attending students. Student "Amit Shah" shows: 22 working days, 12 present, 7 absent, 3 late → 54.5% (amber bar). The manager contacts Amit's parents about the low attendance.

**Why This Model Exists**

Calculating attendance percentages from daily records on-the-fly is expensive for large datasets. Pre-calculated monthly summaries provide instant access to attendance metrics for reports, parent communication, and compliance (many institutes require minimum 75% attendance).

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Center Manager | Identify low-attendance students | Monthly |
| Director | Institute-wide attendance reports | Monthly |
| Parent | View child's monthly attendance summary | Monthly |

---

### 21.5 CLASSES

The Classes section manages live and recorded YouTube-integrated classes, student access control, and viewing analytics.

---

#### 21.5.1 YouTube Channels

**What Is This?**

YouTube channel registrations for live streaming. Each channel record stores the channel ID, name, URL, OAuth credentials (encrypted), quota tracking (daily limit, used today, reset time), verification status, and optional teacher assignment.

**Admin List Columns:** Channel Name, Channel ID (truncated monospace), Status Badge, Verification Badge (green checkmark or pending), Primary Badge (star).

**Filters & Search:** Filter by Status, Verification Status, Primary Channel. Search by Channel Name, Channel ID.

**Available Actions:** Export as CSV, Activate Selected, Deactivate Selected.

**Example — Real-World Use Case**

The institute has two YouTube channels: "ENF Physics" (primary, verified, daily quota 10,000 units) and "ENF Chemistry" (secondary, verified). Physics classes use the primary channel. When quota_used_today approaches daily_quota_limit, the system warns that additional streams may fail. The IT admin monitors quota usage and distributes classes across channels accordingly.

**Why This Model Exists**

YouTube API has strict daily quota limits. Managing multiple channels with proper OAuth tokens, verification status, and quota tracking ensures live classes aren't disrupted by quota exhaustion. The primary channel flag determines which channel is used by default.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Register channels, manage OAuth tokens | During setup, maintenance |
| Academic Coordinator | Assign channels to class schedules | As needed |

---

#### 21.5.2 Scheduled Classes

**What Is This?**

The core class scheduling model. Each class has a code, title, date, start/end time, subject, teacher, batch, YouTube broadcast details (broadcast ID, stream key, watch URL, recording URL), privacy settings, access control (batch-only, multi-batch, all students, custom), attendance mode (auto/manual/hybrid with configurable thresholds), status (Draft/Scheduled/Live/Completed/Cancelled/Rescheduled), and detailed analytics (peak viewers, unique viewers, average watch duration, chat messages).

**Admin List Columns:** Class Code, Title, Subject, Scheduled Date, Time (start – end), Teacher, Status Badge, Live Link (red YouTube icon linking to watch URL).

**Filters & Search:** Filter by Status, Subject, Scheduled Date. Search by Class Code, Title, Teacher Name. Date hierarchy on Scheduled Date.

**Available Actions:** Export as CSV, Export as JSON, Activate Selected, Deactivate Selected.

**Import/Export:** Yes.

**Example — Real-World Use Case**

Dr. Sharma schedules a physics class: Code "PHY-2026-02-16", Title "Optics — Refraction", Date Feb 16, 10:00-11:00 AM, Batch "NEET-2025-A", YouTube Channel "ENF Physics". The system generates a YouTube broadcast with an unlisted privacy status. Students in the NEET-2025-A batch receive a notification with the join link. During the class, status changes to "LIVE". After the class ends, status becomes "COMPLETED" and the recording URL is auto-populated. Analytics show: 38 peak viewers, 42 unique viewers, average watch duration 48 minutes.

**Why This Model Exists**

Live classes are the primary teaching method in online coaching. This model handles the full lifecycle — scheduling, YouTube integration, access control, live monitoring, recording storage, and attendance auto-capture — in a single, comprehensive record.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Teacher | Schedule and conduct classes | Daily |
| Academic Coordinator | Review schedule, ensure all batches covered | Daily |
| Student | Join live classes, watch recordings | Daily |

---

#### 21.5.3 Class Access Tokens

**What Is This?**

One-time access tokens for students to join a specific class. Each token links a student to a scheduled class, has an expiry time, and tracks whether it was used (used_at, device, IP). Tokens can be revoked with a reason.

**Admin List Columns:** Scheduled Class, Student, Used Badge, Revoked Badge, Expires At.

**Filters & Search:** Filter by Used, Revoked.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

When a class is scheduled with access_type "BATCH_ONLY", the system generates tokens for all students in the batch. Student Naveen receives a token that expires 30 minutes after the class ends. If Naveen's account is compromised, the IT admin can revoke the token (revoked=True, reason="Account security concern").

**Why This Model Exists**

Access tokens prevent unauthorized viewers. Without tokens, anyone with the YouTube link could watch paid classes. The token system ensures only enrolled students can access the stream, and the usage tracking provides a secondary attendance signal.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| System | Auto-generates tokens for batch students | Per class scheduling |
| IT Admin | Revoke tokens for security reasons | As needed |

---

#### 21.5.4 Class Watch Times

**What Is This?**

Detailed viewing analytics for each student's class watch session. Tracks total watch time (seconds), video progress percentage, engagement signals (rewind/forward/pause counts, playback speed, tab switches, idle periods, chat messages, questions asked, polls participated), device/connection quality (average quality, buffering count/duration), completion status, and an engagement score.

**Admin List Columns:** Scheduled Class, Student, Watch Time (formatted minutes/seconds), Completion Badge, Live Badge (red "LIVE" for live viewing, gray "VOD" for recording).

**Filters & Search:** Filter by Completion Status, Is Live Watch.

**Available Actions:** Export as CSV, Export as JSON.

**Example — Real-World Use Case**

The academic coordinator exports watch time data for last week's physics classes. Student Naveen watched 48 of 60 minutes (80% progress, completion: COMPLETED, engagement score: 85). Student Amit watched only 12 minutes (20%, PARTIAL, engagement: 25, tab_switches: 8). Amit's 8 tab switches suggest he wasn't focused. This data feeds into auto-attendance (Naveen gets "Present", Amit gets "Late") and helps identify disengaged students.

**Why This Model Exists**

In online education, simply "joining" a class doesn't mean learning. Watch time data with engagement signals provides a window into actual student participation. Tab switches and idle periods flag multitasking students. Engagement scores help teachers prioritize follow-ups.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Teacher | Review class engagement per student | After each class |
| Academic Coordinator | Export engagement reports | Weekly |
| Parent | View child's class participation (via portal) | As needed |

---

### 21.6 COMMUNICATION

The Communication section handles all messaging — support tickets, announcements, direct messages, and notifications.

---

#### 21.6.1 Support Tickets

**What Is This?**

A helpdesk-style ticketing system. Tickets have a unique number, title, description, category (Technical/Account/Payment/Content/Exam/General/Feedback), priority (Low/Medium/High/Critical), status (Open/In Progress/Waiting/Resolved/Closed/Reopened), assignment tracking, SLA breach flag, satisfaction rating, and a TicketMessage inline for the conversation thread.

**Admin List Columns:** Ticket Number, Title, Category Badge, Priority Badge (Low=green, Medium=blue, High=amber, Critical=red), Status Badge, Created Date.

**Filters & Search:** Filter by Status, Priority, Category. Search by Ticket Number, Title. Date hierarchy on Created Date.

**Inline:** TicketMessageInline — view/add messages in the conversation thread.

**Available Actions:** Export as CSV, Export as JSON, Close Tickets, Resolve Tickets.

**Import/Export:** Yes.

**Example — Real-World Use Case**

A student submits a ticket: "Unable to access today's Physics recording" (Category: TECHNICAL, Priority: HIGH). The support staff sees it in the ticket list, opens it, adds an internal note "Checked YouTube — recording is processing", then replies to the student "The recording will be available in 2 hours". Status is changed to "Waiting". After the recording is available, the ticket is resolved via Action "Resolve Tickets". The student rates satisfaction: 4/5.

**Why This Model Exists**

Students, parents, and teachers need a structured channel to report issues and get help. Email-based support loses context. A ticket system tracks every issue from creation to resolution with full conversation history, priority management, and satisfaction tracking.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Student/Parent/Teacher | Submit tickets (via portal) | As needed |
| Support Staff | Respond to tickets, resolve issues | Daily |
| Center Manager | Monitor open tickets, SLA compliance | Daily |

---

#### 21.6.2 Ticket Messages

**What Is This?**

Individual messages within a support ticket conversation. Each message has a sender name, content, optional attachments, and an `is_internal_note` flag (internal notes are visible only to staff, not the ticket submitter).

**Admin List Columns:** Ticket, Sender Name, Internal Badge ("Internal" amber or "Public" gray), Created Date.

**Filters & Search:** Filter by Is Internal Note.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

A ticket has 4 messages: (1) Student: "My test didn't submit" → (2) Staff [Internal]: "Checked logs — timeout at 59:58, auto-submitted successfully" → (3) Staff [Public]: "Your test was auto-submitted. Score: 67/120." → (4) Student: "Thank you."

The internal note (message 2) is only visible to staff in the admin console, not to the student in their portal.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Support Staff | Add replies and internal notes | Per ticket interaction |

---

#### 21.6.3 Announcements

**What Is This?**

Broadcast messages to students, teachers, or specific batches. Each announcement has a title, content (plain + HTML), type (General/Academic/Exam/Event/Maintenance/Urgent), target audience (All/Students/Teachers/Batch/Custom with specific batch or user IDs), pinned flag, published flag, expiry date, acknowledgement requirement, and view count.

**Admin List Columns:** Title, Type Badge, Target Audience, Published Badge, Pinned Badge (📌 pin icon), Published At.

**Filters & Search:** Filter by Type, Target Audience, Is Published, Is Pinned. Search by Title.

**Available Actions:** Export as CSV, Export as JSON, Activate Selected, Deactivate Selected.

**Import/Export:** Yes.

**Example — Real-World Use Case**

The center manager creates an announcement: Title "Exam Schedule Change", Type "EXAM", Target Audience "STUDENTS", Content "The JEE Mock Test scheduled for Feb 20 has been moved to Feb 22. Same time: 10 AM". Is Pinned = True (sticks to top of student portal), Acknowledgement Required = True (students must click "I've read this"). After publishing, the view count incrementally shows how many students have seen it.

**Why This Model Exists**

Coaching institutes constantly need to communicate schedule changes, exam notifications, events, and maintenance windows. Announcements provide a structured, targetable broadcast system with read tracking and acknowledgement capability.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Center Manager | Create and publish announcements | Several times per week |
| Academic Coordinator | Announce exam schedules, syllabus updates | Weekly |
| IT Admin | Post maintenance window notices | As needed |

---

#### 21.6.4 Announcement Reads

**What Is This?**

Tracks which users have read which announcements. Records the user ID, user type, read timestamp, and whether they acknowledged the announcement.

**Admin List Columns:** Announcement, User ID, Read At, Acknowledgement Badge.

**Filters & Search:** Filter by Acknowledged.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

After publishing the "Exam Schedule Change" announcement with acknowledgement required, the coordinator opens Announcement Reads to track progress. 43 of 50 NEET students have read it, 38 have acknowledged. The coordinator contacts the 7 who haven't read it to ensure they know about the schedule change.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Center Manager | Track read/acknowledgement rates | After important announcements |

---

#### 21.6.5 Direct Messages

**What Is This?**

Private messages between users (teacher-to-student, parent-to-teacher, admin-to-teacher). Each message has sender/recipient details, subject, message body, attachments, read status, threading (parent message + thread ID), and per-user deletion flags.

**Admin List Columns:** Sender Name, Recipient Name, Subject, Read Badge, Created Date.

**Filters & Search:** Filter by Is Read. Search by Sender Name, Recipient Name, Subject.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

A parent sends a direct message to their child's physics teacher: Subject "Extra doubts session?", Message "Can you schedule an extra session for Optics this week? My child is struggling with refraction problems." The teacher reads it (read_at is set) and replies in the same thread with a proposed time.

**Why This Model Exists**

While announcements are broadcast messages, direct messages enable private one-on-one communication. This is essential for parent-teacher communication, individual student guidance, and sensitive topics that shouldn't be public.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Parent | Communicate with teachers | As needed |
| Teacher | Reply to parent/student messages | As needed |
| Admin | Review message logs (moderation) | As needed |

---

#### 21.6.6 Notifications

**What Is This?**

System-generated notifications delivered through multiple channels (In-App, Email, SMS, Push, WhatsApp). Each notification has a type (Info/Warning/Success/Error/Action Required), title, message, action URL, delivery status (delivered_at, delivery_error), and read status.

**Admin List Columns:** User ID, Notification Type, Channel Badge (Email=blue, SMS=green, Push=amber, In-App=purple), Title, Read Badge, Delivered Badge.

**Filters & Search:** Filter by Type, Channel, Is Read, Is Delivered. Search by Title.

**Available Actions:** Export as CSV, Export as JSON.

**Example — Real-World Use Case**

When a teacher schedules a new class, the system auto-creates notifications for every student in the batch: Type "INFO", Channel "PUSH", Title "New Physics Class: Feb 16, 10 AM", Action URL linking to the class join page. The admin can see how many notifications were delivered vs. failed (e.g., push token expired for 3 students).

**Why This Model Exists**

Notifications are the glue between system events and user awareness. Class starts, test results, attendance alerts, and ticket updates all generate notifications. Multi-channel support ensures messages reach users through their preferred medium.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| System | Auto-generates notifications | Continuous |
| IT Admin | Monitor delivery rates, debug failures | Weekly |

---

### 21.7 MATERIALS

The Materials section manages educational content beyond live classes — study materials, photo galleries, scholarships, and student achievements.

---

#### 21.7.1 Study Materials

**What Is This?**

Uploaded learning resources — eBooks, videos, question papers, notes, assignments, reference materials, solutions, training videos, and presentations. Each material has a code, title, type (color-coded badge: PDF=red, Video=blue, Document=amber, Link=purple, Image=green), file details (URL, size, MIME type, hash), video details (embed URL, duration, YouTube ID), subject/chapter/topic tags, target audience, difficulty level, access controls (free, downloadable, requires enrollment, allowed batches), and usage stats (view count, download count, rating).

**Admin List Columns:** Title, Type Badge, Subject, Target Audience, Published Badge, View Count (eye icon + number).

**Filters & Search:** Filter by Material Type, Target Audience, Is Published. Search by Title, Material Code.

**Available Actions:** Export as CSV, Export as JSON, Activate Selected, Deactivate Selected.

**Import/Export:** Yes.

**Example — Real-World Use Case**

The physics teacher uploads study materials for the "Optics" chapter: (1) "Optics Notes" — PDF, 2.4 MB, difficulty: Intermediate, target: STUDENT, (2) "Refraction Video" — Video, YouTube ID "abc123", duration 25 min, (3) "Optics Practice Set" — PDF assignment. After publishing, students in the NEET-2025 batch can access these materials. The view count tracks engagement: 38 views for notes vs. 45 views for the video, suggesting students prefer video content.

**Why This Model Exists**

Live classes are ephemeral — students need supplementary materials for revision. A structured material library with subject tagging, access control, and usage tracking ensures students get the right content at the right time, and teachers can measure which resources are most used.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Teacher | Upload study materials, notes, assignments | Weekly |
| Student | Access materials for revision | Daily |
| Academic Coordinator | Monitor material coverage per chapter | Monthly |

---

#### 21.7.2 Material Accesses

**What Is This?**

Tracks every time a user views, downloads, or bookmarks a study material. Records user ID, action (View/Download/Bookmark), timestamp, duration (how long they viewed), and progress percentage.

**Admin List Columns:** Material, User ID, Action, Accessed At.

**Filters & Search:** Filter by Action.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

The academic coordinator exports material access data for the month. Analysis reveals: "Optics Notes PDF" was viewed 85 times but downloaded only 12 times → students read it online. "JEE Question Paper 2024" was downloaded 50 times → students prefer offline practice. This data helps optimize material format decisions.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Academic Coordinator | Analyze content engagement | Monthly |

---

#### 21.7.3 Photo Galleries

**What Is This?**

Image gallery for the institute's website/app — event photos, campus images, lab photos, achievement ceremonies. Each entry has a category, title, image URL, thumbnail URL, sort order (editable directly in the list!), and active flag. The admin list shows a 40×40 rounded thumbnail preview.

**Admin List Columns:** Title, Category, Active Badge, Sort Order (editable inline in list), Preview (40×40 thumbnail).

**Filters & Search:** Filter by Is Active, Category. Sort order is editable directly in the list.

**Available Actions:** Export as CSV, Activate Selected, Deactivate Selected.

**Import/Export:** Yes.

**Example — Real-World Use Case**

After the annual science fair, the marketing team uploads 20 event photos: Category "Science Fair 2026", each with a title and image URL. Sort order determines the display sequence on the website. Inactive photos are hidden from the public gallery but preserved in the admin for reference.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Marketing Team | Upload event and campus photos | After events |
| IT Admin | Manage gallery sort order | As needed |

---

#### 21.7.4 Scholarships

**What Is This?**

Scholarship programs offered by the institute. Each has a title, description, eligibility criteria, amount (displayed as "Rs.X" in green), discount percentage (displayed as "X%" in amber), apply URL, required documents, validity dates, and active status.

**Admin List Columns:** Title, Amount (green "Rs.X"), Discount % (amber "X%"), Active Badge.

**Available Actions:** Export as CSV, Activate Selected, Deactivate Selected.

**Example — Real-World Use Case**

The institute offers three scholarships: "Merit Scholarship" (100% discount for rank ≤ 100 in entrance test), "Partial Scholarship" (50% discount for economically weaker students), and "Referral Discount" (Rs. 5,000 off). Each has eligibility criteria and required documents listed. Students can apply via the apply_url link.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Center Manager | Create/manage scholarship programs | Annually |
| Marketing Team | Feature scholarships on website | Seasonally |

---

#### 21.7.5 Topper Students

**What Is This?**

Showcase records for students who achieved top ranks in competitive exams. Each record has student name, photo, exam name, year, rank (displayed as gold #1, silver #2, bronze #3), score, testimonial, featured flag (star "Featured"), and sort order.

**Admin List Columns:** Student Name, Exam Name, Year, Rank (gold/silver/bronze display), Featured Badge (star "Featured").

**Filters & Search:** Filter by Year, Is Featured. Search by Student Name, Exam Name.

**Available Actions:** Export as CSV, Export as JSON.

**Import/Export:** Yes.

**Example — Real-World Use Case**

After JEE Mains 2026 results, the institute adds their toppers: "Priya Sharma — JEE Mains 2026, Rank 45, Score 285/300, Featured". This record appears on the institute's website/app in the "Our Toppers" section. The testimonial field stores her feedback: "The structured test series and daily doubt sessions were game-changers." This serves as marketing content and social proof.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Marketing Team | Add new toppers after results | After each major exam |
| Director | Review and feature top achievements | As results come in |

---

### 21.8 SESSIONS TRACKING

The Sessions Tracking section monitors user devices, active sessions, login history, and user activity for security and analytics.

---

#### 21.8.1 User Devices

**What Is This?**

Every device a user has logged in from. Tracks device fingerprint (unique), name, type (Desktop/Mobile/Tablet with Font Awesome icons), OS name/version, browser name/version, screen resolution, trust status, blocked status (red "BLOCKED" badge), session count, and push notification tokens.

**Admin List Columns:** Device Name, Device Type Badge (desktop/mobile/tablet/browser icons), User ID (truncated), Trusted Badge, Blocked Badge, Last Seen.

**Filters & Search:** Filter by Device Type, Is Trusted, Is Blocked. Search by Device Name, User ID.

**Available Actions:** Export as CSV, Export as JSON.

**Example — Real-World Use Case**

A student reports they suspect unauthorized access. The IT admin opens User Devices, searches for the student's user ID, and sees 3 devices: "Chrome on Windows" (trusted, last seen today), "Safari on iPhone" (trusted, last seen yesterday), "Chrome on Android" (unknown, last seen 2 hours ago). The admin blocks the suspicious Android device (is_blocked=True, reason "Potential unauthorized access") and terminates all sessions from that device.

**Why This Model Exists**

Device tracking is essential for security. It enables suspicious device detection, multi-device limiting, and forensic analysis during security incidents. Trust/block status provides granular device-level access control.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Monitor devices, block suspicious ones | As needed |
| Security Team | Investigate security incidents | As needed |

---

#### 21.8.2 User Sessions

**What Is This?**

Active and historical login sessions. Each session has a session token (unique), device link, IP address, geo-location (city/state/country/coordinates), start time, last activity, expiry, status (Active/Expired/Logged Out/Revoked/Force Terminated), total active seconds, and concurrent session checks.

**Admin List Columns:** User ID (truncated), User Type, Status Badge, IP Address (monospace with background), Started At, Last Activity At, Duration (computed hours+minutes).

**Filters & Search:** Filter by Status, User Type. Search by User ID, IP Address. 50 records per page.

**Available Actions:** Export as CSV, Export as JSON.

**Example — Real-World Use Case**

The IT admin notices suspicious activity — a teacher's account shows two active sessions from different cities. Session 1: "Hyderabad, IP 103.x.x.x, Duration 2h 15m". Session 2: "Mumbai, IP 122.x.x.x, Duration 10m". The admin force-terminates Session 2 (status=FORCE_TERMINATED) and contacts the teacher to verify. The geo-location data proves it was a shared-credential incident.

**Why This Model Exists**

Session management is a security cornerstone. It enables viewing all active sessions (like Gmail's "Last account activity"), force-terminating suspicious sessions, enforcing concurrent session limits, and tracking session duration for analytics.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Monitor active sessions, force-terminate | Daily/as needed |
| Security Team | Investigate multi-location logins | As needed |

---

#### 21.8.3 Login History

**What Is This?**

Every login attempt — successful or failed. Records username attempted, result (Success/Failed/Blocked/MFA Required/MFA Failed/Account Locked/Inactive with color-coded badges), IP address, device, geo-location, timestamp, suspicious flag (⚠ "Suspicious" in red), risk score, and risk factors.

**Admin List Columns:** Username Attempted, User Type, Result Badge (Success=green, Failed=red, Blocked=amber, Locked=purple), IP (monospace), Attempted At, Suspicious Badge.

**Filters & Search:** Filter by Result, Is Suspicious, User Type. Search by Username, IP Address. Date hierarchy on Attempted At. 50 records per page.

**Available Actions:** Export as CSV, Export as JSON.

**Example — Real-World Use Case**

The IT admin reviews this morning's login history. They filter by Result "FAILED" and see 15 failed attempts. Most are normal (students mistyping passwords). But one cluster stands out: 8 failed attempts for user "admin@enf.com" from IP 45.x.x.x (geo: Ukraine) in 2 minutes, all flagged as Suspicious with risk score 95. The admin confirms it's a brute-force attempt, adds the IP to the block list, and ensures the admin account has MFA enabled.

**Why This Model Exists**

Login history is a compliance and security requirement. It enables detection of brute-force attacks, credential-stuffing attempts, and unauthorized access patterns. The suspicion flag and risk score automate threat detection.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Review failed logins, suspicious activity | Daily |
| Security Auditor | Audit login patterns for compliance | Quarterly |

---

#### 21.8.4 User Activities

**What Is This?**

A detailed activity log tracking every user action — page views, class joins/leaves, test starts/submissions, material views/downloads, profile updates, settings changes, messages sent, tickets created. Each record has an activity type (12 types), description, resource reference (type + ID + name), page/referrer URLs, IP, duration, and custom data.

**Admin List Columns:** User ID (truncated), Activity Type Badge, Resource Type, Occurred At.

**Filters & Search:** Filter by Activity Type. Search by User ID.

**Available Actions:** Export as CSV, Export as JSON.

**Example — Real-World Use Case**

A teacher reports that their test was modified without authorization. The IT admin filters User Activities for resource_type "Test" and resource_id matching the test. The log shows: 10:00 AM — Teacher A: UPDATE (original change), 11:30 AM — Admin B: UPDATE (unauthorized change). The changed data helps identify what was modified and by whom, providing an evidence trail.

**Why This Model Exists**

User activity logging provides a complete audit trail of who did what, when, and from where. It's essential for security investigations, usage analytics (which features are most used), and compliance auditing.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Investigate incidents, track feature usage | As needed |
| Security Auditor | Review user behavior patterns | Quarterly |

---

### 21.9 AUDIT

The Audit section provides security event logging, data retention policies, and backup management.

---

#### 21.9.1 Audit Logs

**What Is This?**

Comprehensive audit trail for all system actions. Each log entry has an action (Create/Read/Update/Delete/Login/Logout/Login Failed/Password Change/Permission Change/Export/Import/Settings Change/System/API Call) with color-coded badges, resource details (type, ID, name), old/new values (JSON diff), changed fields list, user details (ID, username, IP, user agent, session), severity (Debug/Info/Warning/Error/Critical), and security event flag (🔒 "Security").

**Admin List Columns:** Action Badge (Create=green, Update=blue, Delete=red, Login=purple, Export=amber), Resource Type, Username, IP (monospace), Severity Badge (Low=green, Medium=blue, High=amber, Critical=red), Security Badge, Created Date.

**Filters & Search:** Filter by Action, Severity, Is Security Event, Resource Type. Search by Username, Resource Type, Action Description, IP Address. Date hierarchy on Created Date. 50 records per page.

**Available Actions:** Export as CSV, Export as JSON.

**Example — Real-World Use Case**

During a quarterly security audit, the auditor filters Audit Logs by Severity "CRITICAL" and Is Security Event "Yes". They find: (1) Password reset for admin account at 2 AM (suspicious timing), (2) Permission change granting "Delete All Students" to a new role (needs review), (3) Bulk export of 500 student records (potential data breach). Each entry has old_values and new_values for full before/after comparison.

**Why This Model Exists**

Audit logs are a regulatory and operational necessity. They answer "who changed what, when, and why" with full before/after snapshots. The severity and security-event flags help prioritize investigation of high-risk actions.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Review security events | Weekly |
| Security Auditor | Comprehensive audit review | Quarterly |
| Director | Verify critical changes (fee updates, role changes) | As needed |

---

#### 21.9.2 Audit Purge Policies

**What Is This?**

Data retention policies for audit records. Each policy defines a resource type, retention period (days), action on expiry (Delete/Archive/Anonymize), archive location, and tracks the last purge date and records purged count.

**Admin List Columns:** Resource Type, Retention Days, Action on Expiry, Active Badge.

**Filters & Search:** Filter by Is Active.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

The IT admin sets up policies: "Audit Logs — retain 365 days, then Archive to /backup/audit/", "Login History — retain 180 days, then Delete", "User Activity — retain 90 days, then Anonymize (remove user IDs but keep aggregate data)". This ensures compliance with data retention regulations while preventing database bloat.

**Why This Model Exists**

Without purge policies, audit data grows indefinitely, consuming storage and slowing queries. Configurable retention periods with archive/delete/anonymize options balance compliance requirements with operational efficiency.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Configure retention policies | During setup, annual review |

---

#### 21.9.3 Backup Policies

**What Is This?**

Database backup configuration. Each policy defines a name, backup type (Full/Incremental/WAL Archive/Logical), cron schedule, retention period, hot/cold backup paths, compression/encryption settings, and active status.

**Admin List Columns:** Policy Name, Backup Type, Schedule Cron, Retention Days, Active Badge.

**Filters & Search:** Filter by Is Active, Backup Type.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

The IT admin creates three backup policies: (1) "Daily Full Backup" — Full, cron "0 2 * * *" (2 AM daily), retention 30 days, hot path /backup/hot/, compression enabled. (2) "Hourly WAL Archive" — WAL_ARCHIVE, cron "0 * * * *" (every hour), retention 7 days. (3) "Monthly Cold Backup" — Full, cron "0 3 1 * *" (1st of month at 3 AM), retention 365 days, cold path /backup/cold/, encryption enabled.

**Why This Model Exists**

Backup configuration should be managed through the admin interface, not server config files. This allows non-sysadmin staff to view backup schedules and ensures backup policies are part of the application's auditable configuration.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Configure backup schedules | During setup, reviewed quarterly |

---

#### 21.9.4 Backup History

**What Is This?**

Log of every backup execution. Each entry links to a policy, has status (Running/Completed/Failed/Partial), timestamps, duration, backup size (auto-formatted as B/KB/MB/GB), backup path, checksum, error message (if failed), tables/rows backed up counts, and verification status.

**Admin List Columns:** Policy, Status Badge, Started At, Completed At, Size (auto-formatted).

**Filters & Search:** Filter by Status.

**Available Actions:** Export as CSV, Export as JSON.

**Example — Real-World Use Case**

The IT admin checks Monday morning's backup status. They see: "Daily Full Backup — Completed at 2:15 AM, Size: 2.3 GB, Duration: 15 min, 52 tables, 1.2M rows, Verified ✓". If a backup shows "Failed" with error "Disk space insufficient", the admin is alerted to resolve storage issues before the next backup.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Monitor backup success/failure | Daily |
| Security Auditor | Verify backup compliance | Quarterly |

---

### 21.10 SYSTEM CONFIG

The System Config section manages application-level settings, feature flags, security policies, maintenance windows, institute information, enquiries, AI features, class link integrations, and attendance rules.

---

#### 21.10.1 System Settings

**What Is This?**

Key-value configuration store for application settings. Each setting has a key (e.g., `max_login_attempts`, `default_timezone`), value (string or JSON), value type (String/Integer/Boolean/JSON/Decimal), category, description, secret flag (🔒 — hidden in displays), and editable flag.

**Admin List Columns:** Setting Key, Value Type Badge, Category Badge, Secret Badge (🔒), Editable Badge.

**Filters & Search:** Filter by Value Type, Category, Is Secret. Search by Setting Key.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

The IT admin configures: `max_login_attempts` = 5 (Integer), `default_timezone` = "Asia/Kolkata" (String), `smtp_password` = "***" (String, is_secret=True — not displayed in the admin list), `maintenance_mode` = false (Boolean). Changing `maintenance_mode` to true enables a site-wide maintenance page without code deployment.

**Why This Model Exists**

Application behavior should be configurable without code changes or deployments. System settings provide a database-driven configuration layer that can be changed by admins in real-time.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Modify system behavior | As needed |
| Super Admin | Review configuration for audits | Quarterly |

---

#### 21.10.2 Feature Flags

**What Is This?**

Toggle switches for enabling/disabling features without code deployment. Each flag has a key, name, enabled state (green "● ON" or red "○ OFF" pill), rollout percentage (progress bar with color thresholds), allowed user types and IDs, and start/end dates for time-limited features.

**Admin List Columns:** Flag Key, Flag Name, Enabled Badge (ON/OFF pill), Rollout % (progress bar).

**Filters & Search:** Filter by Is Enabled. Search by Key, Name.

**Available Actions:** Export as CSV, Activate Selected, Deactivate Selected.

**Example — Real-World Use Case**

The development team deploys a new "AI Doubt Solver" feature. The IT admin creates a feature flag: key `ai_doubt_solver`, enabled=True, rollout_percentage=20, allowed_user_types=["STUDENT"]. This means only 20% of students see the feature initially. If it works well, rollout is increased to 50%, then 100%. If bugs appear, the flag is set to enabled=False instantly — no code revert needed.

**Why This Model Exists**

Feature flags enable gradual rollouts, A/B testing, kill switches for buggy features, and time-limited promotions. They decouple feature availability from code deployment, giving the team confidence to ship fast.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Toggle features, adjust rollout | As features are deployed |
| Director | Request specific features on/off | As needed |

---

#### 21.10.3 MFA Policies

**What Is This?**

Multi-Factor Authentication configuration. Each policy defines MFA type (TOTP/SMS/Email), whether it's mandatory (red "Mandatory" or gray "Optional"), OTP length, expiry seconds, max attempts before lockout, lockout duration, resend cooldown, applicable user types, and active status.

**Admin List Columns:** MFA Type, Mandatory Badge, OTP Length, OTP Expiry Seconds, Active Badge.

**Filters & Search:** Filter by Is Active, Is Mandatory.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

The IT admin creates two MFA policies: (1) "Admin MFA" — Type: TOTP, Mandatory: Yes, applies to ["ADMIN"] — all admins must use an authenticator app. (2) "Teacher MFA" — Type: EMAIL, Mandatory: No, OTP length: 6, Expiry: 300 seconds — teachers can optionally enable email-based OTP. Students don't have MFA to keep onboarding simple.

**Why This Model Exists**

Different user types have different security needs. Admin accounts handling sensitive data require mandatory MFA. Student accounts should have optional, low-friction security. Configurable MFA policies allow this granularity.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Configure MFA requirements | During setup, annual review |

---

#### 21.10.4 Maintenance Windows

**What Is This?**

Scheduled maintenance periods. Each window has a title, description, start/end times, scope (Full/Partial/Feature-level), affected features list, active status (⚠ "Active" in amber), and a notification_sent flag.

**Admin List Columns:** Title, Scope, Start Time, End Time, Active Badge (⚠).

**Filters & Search:** Filter by Is Active, Scope.

**Available Actions:** Export as CSV.

**Example — Real-World Use Case**

The IT admin schedules maintenance: Title "Database Migration — v4.1 Upgrade", Start: Feb 20 2:00 AM, End: Feb 20 5:00 AM, Scope: FULL. A notification is auto-generated for all users. The active badge turns amber during the maintenance window, signaling to anyone using the admin that the system may be unstable.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Schedule maintenance windows | Monthly |
| Center Manager | View upcoming maintenance | As notified |

---

#### 21.10.5 Founder Infos

**What Is This?**

Information about the institute's founders, management, and advisors. Each record has a member type (Founder/Management/Advisor), name, designation, photo (shown as 32×32 circular thumbnail in the list), bio, qualifications, contact email, social links, sort order, and active status.

**Admin List Columns:** Name, Member Type, Designation, Active Badge, Photo Preview (circular thumbnail).

**Filters & Search:** Filter by Is Active, Member Type.

**Available Actions:** Export as CSV, Export as JSON, Activate Selected, Deactivate Selected.

**Import/Export:** Yes.

**Example — Real-World Use Case**

The institute displays founder information on the website's "About Us" page. The director adds: "Dr. Rajesh Kumar — Founder & CEO — IIT Delhi Alumnus, 20 years in JEE coaching". The photo thumbnail shows in the admin list for quick identification. Sort order controls the display sequence on the website.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Director | Add/update founder profiles | As needed |
| Marketing Team | Manage "About Us" content | Annually |

---

#### 21.10.6 Enquiry Forms

**What Is This?**

Enquiry/lead management for prospective students. Each enquiry captures name, email, phone, subject, message, source (Website/App/Referral/Walk-in), status (New/Contacted/Converted/Closed), assignment, follow-up date, and notes.

**Admin List Columns:** Name, Email, Phone, Source Badge, Status Badge, Created Date.

**Filters & Search:** Filter by Status, Source. Search by Name, Email, Phone. Date hierarchy on Created Date.

**Available Actions:** Export as CSV, Export as JSON, Activate Selected, Deactivate Selected.

**Import/Export:** Yes.

**Example — Real-World Use Case**

A prospective student fills out the contact form on the website. An enquiry record is automatically created: Source "WEBSITE", Status "NEW". The front desk staff sees the new enquiry in the admin, sets Status "CONTACTED", adds notes "Called, interested in NEET batch, follow up after entrance test on Feb 25", and sets follow_up_date. When the student enrolls, Status is set to "CONVERTED".

**Why This Model Exists**

Lead management is critical for coaching institutes' growth. Tracking enquiries from source to conversion helps measure marketing ROI (which source brings the most enrollments?) and ensures no prospective student falls through the cracks.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Front Desk Staff | Process new enquiries | Daily |
| Center Manager | Monitor follow-ups, track conversion rates | Weekly |
| Marketing Team | Export enquiry data for campaign analysis | Monthly |

---

#### 21.10.7 AI Feature Configs

**What Is This?**

Configuration registry for AI-powered features. Each feature has a key, name, icon (rendered as a gradient icon box in the list), category (Content/Analytics/Assessment/Communication/Automation), scope (Admin/Teacher/Student/All), enabled status (green/red pill), provider, API endpoint/key reference, rate limits (per hour / per user), sort order, and JSON config.

**Admin List Columns:** Feature Icon (gradient box), Feature Name, Category Badge (Content=purple, Analytics=blue, Assessment=amber, Communication=green, Automation=cyan), Scope Badge, Enabled Toggle (ON/OFF pill), Provider (monospace), Rate Info ("X/hr · Y/user"), Updated Date.

**Filters & Search:** Filter by Is Enabled, Category, Scope, Provider. Search by Feature Key, Name, Description.

**Available Actions:** Export as CSV, Export as JSON, ✅ Enable selected features, 🚫 Disable selected features.

**Form Sections:** Feature Identity (key, name, description, icon, sort order) → Control (enabled, category, scope) → Provider & API (collapsed, endpoint, key reference) → Rate Limits (collapsed) → Advanced (collapsed, config JSON).

**Import/Export:** Yes.

**Example — Real-World Use Case**

The institute enables three AI features: (1) "AI Question Generator" — Category: ASSESSMENT, Scope: TEACHER, Provider: OpenAI, Rate: 50/hr. (2) "AI Doubt Solver" — Category: CONTENT, Scope: STUDENT, Provider: Anthropic, Rate: 100/hr, 10/user. (3) "Attendance Analytics" — Category: ANALYTICS, Scope: ADMIN, Provider: internal. The feature list provides a centralized dashboard to enable/disable AI features, manage rate limits, and switch providers — all without code changes.

**Why This Model Exists**

AI features require configuration — API keys, rate limits, scope restrictions, and enable/disable toggles. Rather than hardcoding these in settings files, a database-driven config allows real-time management through the admin console.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Enable/disable AI features, manage rate limits | As needed |
| Director | Review AI feature usage and costs | Monthly |

---

#### 21.10.8 Class Link Configs

**What Is This?**

Configuration for live class link generation across platforms (YouTube, Zoom, Google Meet, MS Teams, Custom). Each config defines the platform (with color-coded icon badges: YouTube=red, Zoom=blue, Meet=green, Teams=purple), API credentials (encrypted), auto-generation settings (minutes before class, default duration, auto-record, auto-admit), webhook URL, and default/active status.

**Admin List Columns:** Platform Badge (icon + color), Tenant, Active Badge, Default Badge (★), Auto-Gen Badge (⚡ "Auto" or "Manual"), Generate Before ("Xm before"), Duration ("Xmin"), Updated Date.

**Filters & Search:** Filter by Platform, Is Active, Is Default, Auto Generate Link. Search by Tenant Name.

**Available Actions:** Export as CSV, Activate Selected, Deactivate Selected.

**Form Sections:** Platform (tenant, platform, active, default) → API Configuration (collapsed, endpoint, keys, OAuth tokens) → Auto-Generation (auto-generate, minutes before, duration, record, admit) → Webhook & Advanced (collapsed, webhook URL, config JSON).

**Example — Real-World Use Case**

The institute uses YouTube as the primary platform and Zoom as backup. Config 1: Platform "YOUTUBE", Active, Default, Auto-generate 15 min before, Duration 60 min, Auto-record On. Config 2: Platform "ZOOM", Active, Not Default, Auto-generate 10 min before. When a teacher schedules a class, the system auto-creates YouTube broadcast/stream 15 minutes before start time. If YouTube is down, the coordinator switches the class to Zoom by changing config defaults.

**Why This Model Exists**

Multi-platform class delivery requires configuration management. Different platforms have different APIs, credentials, and capabilities. A platform-agnostic config model allows the institute to support multiple platforms simultaneously and switch with zero code changes.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| IT Admin | Configure platform integrations | During setup, maintenance |
| Academic Coordinator | View platform defaults | As needed |

---

#### 21.10.9 Attendance Rules

**What Is This?**

Configurable rules governing how attendance is marked. Each rule defines timing thresholds (grace period, late threshold, absent threshold), minimum watch percentage for auto-attendance, auto-mark sources (live class, biometric, geofence), notification triggers (notify absent student, notify parent, notify admin below threshold), teacher attendance requirements, and scope (Student/Teacher/All).

**Admin List Columns:** Rule Name, Applies To Badge (Student=blue, Teacher=green, All=purple), Grace Period ("Xmin" green), Late Threshold ("Xmin" amber), Min Watch %, Auto Live Badge (⚡ "Auto" or "Manual"), Teacher Self Badge ("Required" or "Optional"), Active Badge.

**Filters & Search:** Filter by Is Active, Applies To, Auto Mark from Live Class, Teacher Self Attendance Required. Search by Rule Name.

**Available Actions:** Export as CSV, Activate Selected, Deactivate Selected.

**Form Sections:** Rule Identity (name, description, applies to, active) → Timing Rules (grace minutes, late threshold, absent threshold, min watch %) → Auto-Attendance Sources (live class, biometric, geofence) → Notifications (collapsed, who gets notified and when) → Teacher Attendance (teacher-specific settings).

**Example — Real-World Use Case**

Two attendance rules are configured: (1) "Student Attendance" — Applies to STUDENT, Grace 10 min, Late after 15 min, Absent after 30 min, Min watch 70%, Auto-mark from live class, Notify parent on absent, Alert admin if batch drops below 75%. (2) "Teacher Attendance" — Applies to TEACHER, Teacher self-attendance required, Auto-mark from class start. This means when a physics class starts, the system auto-marks the teacher as present (they started the stream) and marks students based on watch percentage after the class ends.

**Why This Model Exists**

Attendance rules should be configurable, not hardcoded. Different batches, seasons, or institutes may have different thresholds. A rule-based approach allows the center manager to adjust grace periods, thresholds, and notification preferences without developer intervention.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Center Manager | Adjust attendance thresholds | Seasonally |
| IT Admin | Configure auto-attendance sources | During setup |

---

### 21.11 REALTIME

The Realtime section handles server-to-client event delivery for live updates.

---

#### 21.11.1 Realtime Events

**What Is This?**

Events pushed to users in real-time via WebSocket or polling. Each event has a type (Class Started/Ended, Test Published/Result, Announcement, Notification, Attendance Marked, Session Terminated, System Alert, Chat Message, Custom), target channel, payload (JSON), priority (1-10, displayed as Low/Normal/High/Urgent color badges), delivery status, delivery attempts, and expiry.

**Admin List Columns:** Event Type Badge, Target Type, Target Channel, Delivered Badge, Priority Badge (Low=gray, Normal=blue, High=amber, Urgent=red), Created Date.

**Filters & Search:** Filter by Event Type, Is Delivered, Priority. Search by Target Channel. 50 records per page.

**Available Actions:** Export as CSV, Export as JSON.

**Example — Real-World Use Case**

When a teacher starts a live class, the system creates a realtime event: Type "CLASS_STARTED", Target Channel "batch:NEET-2025-A", Payload: `{"class_id": "...", "title": "Physics - Optics", "join_url": "..."}`, Priority: HIGH. This event is pushed to all students in the batch, triggering a popup notification: "Physics class is starting now! Click to join."

**Why This Model Exists**

Real-time events power the live experience: instant class start notifications, live test score updates, chat messages during classes, and session termination alerts. Without a structured event model, these updates would require polling or manual refresh.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| System | Auto-generates events | Continuous |
| IT Admin | Monitor delivery rates, debug failed events | As needed |

---

### 21.12 TENANTS

The Tenants section manages multi-tenant (multi-institute) configuration.

---

#### 21.12.1 Tenants

**What Is This?**

The top-level organizational entity — each tenant represents one coaching institute. Every other record in the system belongs to a tenant. A tenant has identity (code, name, legal name, subdomain, custom domain), branding (logo, favicon, primary/secondary colors, theme config), contact info, YouTube channel credentials, plan details (Starter/Professional/Enterprise/Custom with max students/teachers/storage limits), features enabled, status (Active/Suspended/Trial/Expired), trial/subscription dates, and regional settings (timezone, date format, academic year start).

**Admin List Columns:** Code, Name, Subdomain (monospace with indigo background), Plan Badge (Free=gray, Basic=blue, Pro=purple, Enterprise=amber), Status Badge, Created Date.

**Filters & Search:** Filter by Status, Plan Type. Search by Code, Name, Subdomain, Custom Domain.

**Available Actions:** Export as CSV, Export as JSON, Activate Selected, Deactivate Selected.

**Import/Export:** Yes.

**Example — Real-World Use Case**

A SaaS deployment serves multiple coaching institutes. Tenant "ENF" has subdomain "enf.platform.com", Plan "Enterprise" (max 500 students, 50 teachers, 100 GB storage), branding with purple theme. Tenant "ABC Institute" has subdomain "abc.platform.com", Plan "Professional" (max 200 students), different branding. Each tenant's data is completely isolated — ENF's students never see ABC's data.

**Why This Model Exists**

Multi-tenancy enables the platform to serve multiple independent coaching institutes from a single deployment. Each tenant gets their own branding, data isolation, feature set, and resource limits. This is the foundation that makes the platform scalable from 1 to 100+ institutes.

**Who Uses It?**

| Who | Action | Frequency |
|-----|--------|-----------|
| Super Admin | Create/manage tenant accounts | When onboarding new institutes |
| IT Admin | Manage plan limits, feature flags per tenant | Monthly |

---

*Documentation generated for ENABLE PROGRAM Admin Console v4.0 (Purple Edition)*  
*Last updated: February 16, 2026*
