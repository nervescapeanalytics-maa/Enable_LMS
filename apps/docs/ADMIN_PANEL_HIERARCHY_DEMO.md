# ENABLE PROGRAM — Admin Panel Hierarchy & Demo Guide

**For Demo Presentation & Explanation**
**Version:** 4.0 (Purple Edition)
**Date:** February 16, 2026

---

## Table of Contents

1. [How the Admin Panel Works — The Big Picture](#1-the-big-picture)
2. [Layer 1: Tenant (Multi-Tenant Root)](#2-layer-1-tenant)
3. [Layer 2: RBAC — Roles & Permissions](#3-layer-2-rbac)
4. [Layer 3: User Types & Their Mapping](#4-layer-3-user-types)
5. [Layer 4: Academic Structure](#5-layer-4-academic-structure)
6. [Layer 5: Operational Modules](#6-layer-5-operational-modules)
7. [How Everything Maps Together — Complete Flow](#7-complete-mapping)
8. [Demo Walkthrough Script](#8-demo-walkthrough)
9. [Admin Panel Sidebar → Model Mapping](#9-sidebar-mapping)
10. [Entity Relationship Reference](#10-entity-relationships)
11. [Interactive Demo Page](#11-interactive-demo)

---

## 1. The Big Picture

The ENF Admin Panel is built as a **5-layer hierarchical system**. Each layer depends on the one above it:

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: TENANT                                            │
│  The root container. Everything lives inside a tenant.      │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: RBAC (Roles & Permissions)                        │
│  Who can do what. Defines access control rules.             │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3: USERS (Admin, Teacher, Student, Parent)           │
│  The people who use the system. Each gets a role.           │
├─────────────────────────────────────────────────────────────┤
│  LAYER 4: ACADEMIC STRUCTURE                                │
│  Sessions, Groups, Subjects, Chapters, Batches              │
│  The "what" and "when" of education.                        │
├─────────────────────────────────────────────────────────────┤
│  LAYER 5: OPERATIONS                                        │
│  Classes, Tests, Attendance, Materials, Communication       │
│  The daily activities that reference everything above.      │
└─────────────────────────────────────────────────────────────┘
```

**Key Principle:** Data flows **top-down**. A Tenant contains Users. Users are assigned Roles with Permissions. Users operate within Academic Structures (Batches). Operations (Classes, Tests) reference Users + Academic entities.

---

## 2. Layer 1: Tenant

### What Is a Tenant?

A **Tenant** is an independent coaching institute. The system supports **multi-tenancy** — multiple institutes can share the same infrastructure while keeping their data completely isolated.

```
┌──────────────────────────────────────────────┐
│  Tenant: "ABC Coaching Institute"            │
│  ─────────────────────────────────────       │
│  Code: ABC                                   │
│  Subdomain: abc.enfclass.com                 │
│  Plan: PREMIUM                               │
│  Status: ACTIVE                              │
│                                              │
│  ┌─ Students ────────── 156 ─┐               │
│  ├─ Teachers ────────── 12  ─┤               │
│  ├─ Admins ─────────── 5   ─┤  All isolated  │
│  ├─ Batches ────────── 8   ─┤  within this   │
│  ├─ Tests ──────────── 45  ─┤  tenant        │
│  └─ Every other model ──────┘               │
└──────────────────────────────────────────────┘
```

### Tenant Fields

| Field | Purpose |
|-------|---------|
| `code` | Unique identifier (e.g., ABC) |
| `name` | Display name |
| `subdomain` | URL prefix (abc.enfclass.com) |
| `custom_domain` | Optional custom domain |
| `plan_type` | FREE / BASIC / PREMIUM / ENTERPRISE |
| `youtube_api_key` | YouTube integration for live classes |
| `status` | ACTIVE / INACTIVE / SUSPENDED |

### Why Multi-Tenancy Matters

Without multi-tenancy, each institute would need a separate server. With it:
- **1 server** serves 100+ institutes
- Data is **completely isolated** — ABC Institute cannot see XYZ Institute's students
- **Shared infrastructure** reduces cost per institute

### Admin Panel Location

**Sidebar → TENANTS → Tenants**

---

## 3. Layer 2: RBAC — Roles & Permissions

### The RBAC Model

RBAC = **Role-Based Access Control**. Instead of assigning permissions to every user individually, you:

1. Define **Permissions** (atomic actions like "read students in batch")
2. Bundle permissions into **Roles** (like "Academic Coordinator")
3. Assign **Roles** to users (Admin gets "Academic Coordinator" role)

### Three RBAC Components

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  PERMISSION                    ROLE              USER       │
│  ───────────                   ────              ────       │
│  students.read.batch    ──┐                                 │
│  tests.create.own       ──┤    Academic      ──→   Kavya    │
│  attendance.read.batch  ──┼──→ Coordinator       (Admin)    │
│  materials.create.own   ──┤    Level: 70                    │
│  students.export.tenant ──┘                                 │
│                                                             │
│  system.execute.global  ──┐                                 │
│  audit.read.global      ──┤    Super Admin   ──→   Root     │
│  *.*.global             ──┼──→ Level: 100        (Admin)    │
│  tenants.manage.global  ──┘                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Permission Code Format

Every permission follows the pattern: **`module.action.scope`**

| Component | Values | Example |
|-----------|--------|---------|
| **Module** | students, teachers, tests, attendance, classes, materials, system, audit | `students` |
| **Action** | CREATE, READ, UPDATE, DELETE, EXECUTE, APPROVE, EXPORT | `.read` |
| **Scope** | OWN, BATCH, BRANCH, TENANT, GLOBAL | `.batch` |

**Full example:** `students.read.batch` → "Can read student records within assigned batch"

### Permission Scope Escalation

Scopes form a hierarchy — higher scope includes all lower scopes:

```
GLOBAL ─── Can access ALL records across ALL tenants
  │
TENANT ─── Can access ALL records within own tenant
  │
BRANCH ─── Can access records in managed branches only
  │
BATCH ──── Can access records in assigned batches only
  │
OWN ────── Can access only records they personally own/created
```

### Role Types

| Type | Meaning | Example |
|------|---------|---------|
| **SYSTEM** | Built-in, cannot be deleted | "Super Admin", "Default Teacher" |
| **TENANT_DEFAULT** | Default for tenant, can be modified | "Branch Manager" |
| **CUSTOM** | Created by tenant admin | "Chemistry HOD" |

### Role Inheritance (parent_role)

Roles can **inherit** from a parent role. The child gets ALL parent permissions plus its own:

```
Teacher Role (Level 30)
├── classes.read.own
├── attendance.read.batch
└── students.read.batch

    ↓ inherits ↓

Head Teacher Role (Level 80, parent: Teacher)
├── ✓ classes.read.own        ← inherited
├── ✓ attendance.read.batch   ← inherited
├── ✓ students.read.batch     ← inherited
├── + attendance.update.batch ← own permission
├── + students.export.tenant  ← own permission
└── + tests.approve.batch     ← own permission
     Total: 3 inherited + 3 own = 6 permissions
```

### `applies_to` Filter

Each role specifies which user type(s) it can be assigned to:

| Value | Who Can Use |
|-------|-------------|
| `ADMIN` | Admin users only |
| `TEACHER` | Teacher users only |
| `STUDENT` | Student users only |
| `PARENT` | Parent users only |
| `ALL` | Any user type |

### Admin Panel Location

**Sidebar → ACCOUNTS → Roles** — Create/edit roles with inline permission assignment
**Sidebar → ACCOUNTS → Permissions** — View/create individual permissions
**Sidebar → ACCOUNTS → Role permissions** — Audit the role↔permission junction table

---

## 4. Layer 3: User Types & Their Mapping

### The Four User Types

All users extend a common `BaseUser` with shared fields (email, phone, MFA, status). Each user type adds domain-specific fields:

```
                    BaseUser (abstract)
                    ├── id (UUID)
                    ├── tenant (FK → Tenant)
                    ├── email, phone, password_hash
                    ├── first_name, last_name
                    ├── status: ACTIVE/INACTIVE/SUSPENDED/PENDING
                    ├── MFA settings
                    └── created_at, updated_at
                         │
          ┌──────────────┼──────────────┬──────────────┐
          ▼              ▼              ▼              ▼
       Admin          Teacher        Student         Parent
```

### 4.1 Admin — The System Operators

**Admin Types (Hierarchy):**

| Admin Type | Access Level | Example Person |
|------------|-------------|----------------|
| 🔴 **SUPER_ADMIN** | Everything. All tenants, all settings, all data | Platform Owner |
| 🟠 **TENANT_ADMIN** | Everything within their tenant | Institute Director |
| 🔵 **BRANCH_ADMIN** | Only `managed_branches[]` within tenant | Campus Head |
| 🟢 **ACADEMIC_ADMIN** | Academic modules (subjects, batches, tests) | Academic Coordinator |
| 🟣 **FINANCE_ADMIN** | Financial modules (fees, scholarships) | Accounts Manager |
| 🩵 **SUPPORT_ADMIN** | Support modules (tickets, communication) | Help Desk Lead |

**How Admin Access Works:**

```
Admin User "Kavya"
├── admin_type: ACADEMIC_ADMIN     ← defines module access
├── role: "Academic Coordinator"   ← FK to Role → gets all role's permissions
├── permissions_override: [...]    ← JSON array of extra permission codes (bypass role)
├── managed_branches: ["Main"]     ← limits scope to specific branches
├── session_timeout: 240 min       ← auto-logout after 4 hours
└── allowed_ips: ["192.168.1.*"]   ← IP whitelist (if require_ip_whitelist=True)
```

**Admin Panel Location:** Sidebar → ACCOUNTS → Admins

---

### 4.2 Teacher — The Content Creators

Teachers are the bridge between academic content and students. They:
- Conduct live classes via YouTube
- Create and grade tests
- Upload study materials
- Mark attendance

**Key Relationships:**

```
Teacher "Dr. Sharma"
├── subjects: ["Physics", "Applied Physics"]     ← JSON — what they teach
├── employment_type: FULL_TIME                   ← HR categorization
├── reporting_to → Teacher "Prof. Verma"         ← self-FK hierarchy
│
├── BatchTeacher assignments:
│   ├── Batch: NEET-2025-A, Subject: Physics     ← teaches Physics in this batch
│   └── Batch: JEE-A, Subject: Physics           ← also teaches in JEE batch
│
├── YouTube Integration:
│   ├── youtube_channel_id: UC...                 ← linked YouTube channel
│   ├── youtube_channel_verified: True            ← admin verified
│   └── can_create_streams: True                  ← permission to go live
│
└── Inline Permissions (not role-based):
    ├── can_edit_student_profile: True
    ├── can_override_attendance: True
    └── can_override_scores: True
```

**Admin Panel Location:** Sidebar → ACCOUNTS → Teachers

---

### 4.3 Student — The Primary Users

Students are the core records. Every operational feature ultimately serves students.

**Key Relationships:**

```
Student "Naveen Reddy" (STU2026001)
├── batch → Batch "NEET-2025-A"                  ← FK — primary batch assignment
├── student_class: 12                             ← Class level
├── exam_target: NEET                             ← Exam being prepared for
├── stream: PCB                                   ← Physics/Chemistry/Biology
├── fee_status: PAID                              ← Financial status
│
├── BatchStudent records (can be in multiple batches):
│   ├── Batch: NEET-2025-A (primary)
│   └── Batch: Foundation-Biology (additional)
│
├── parent_links → ParentStudent (M2M):
│   ├── Parent: Mr. Reddy (Father)
│   └── Parent: Mrs. Reddy (Mother)
│
├── Operational data linked:
│   ├── Attendance records
│   ├── Test attempts & scores
│   ├── Class watch times
│   ├── Material access logs
│   └── Support tickets
│
└── Notification preferences:
    ├── notification_email: True
    ├── notification_sms: True
    ├── notification_push: True
    └── notification_whatsapp: True
```

**Admin Panel Location:** Sidebar → ACCOUNTS → Students

---

### 4.4 Parent — The Observers

Parents have **read-only access** to their children's data, controlled by toggle flags:

```
Parent "Mr. Reddy"
├── primary_student → Student "Naveen Reddy"     ← FK — main child
├── relationship: FATHER
│
├── Access Controls (per parent):
│   ├── can_view_attendance: True     ← sees child's attendance
│   ├── can_view_results: True        ← sees test scores
│   ├── can_view_fee_details: True    ← sees fee status
│   ├── can_communicate_teacher: True ← can send messages to teachers
│   └── receive_notifications: True   ← gets SMS/email alerts
│
└── student_links → ParentStudent (M2M for multiple children):
    ├── Student: Naveen Reddy
    └── Student: Priya Reddy (sister)
```

**Admin Panel Location:** Sidebar → ACCOUNTS → Parents

---

### User Type Comparison

| Feature | Admin | Teacher | Student | Parent |
|---------|-------|---------|---------|--------|
| **Login to Admin Panel** | ✅ Yes | ❌ No (API only) | ❌ No (API only) | ❌ No (API only) |
| **Role Assignment** | ✅ FK to Role | ❌ Inline perms | ❌ No | ❌ Toggle flags |
| **RBAC Permissions** | ✅ Full RBAC | ⚠️ Field-level | ❌ No | ⚠️ can_view_* flags |
| **Multi-tenant** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **MFA Support** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Import/Export** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |

---

## 5. Layer 4: Academic Structure

The academic layer defines **what** is taught, **when** it's taught, and **who** teaches whom.

### Hierarchy

```
Academic Session (2025-2026)
│
├── Group ("Main Campus")
│   ├── Category ("JEE Wing")
│   └── Category ("NEET Wing")
│
├── Subject ("Physics")
│   ├── SubjectSection ("Mechanics Section")
│   ├── Chapter ("Mechanics")
│   │   ├── Topic ("Newton's First Law")
│   │   ├── Topic ("Newton's Second Law")
│   │   └── Topic ("Newton's Third Law")
│   ├── Chapter ("Thermodynamics")
│   │   └── Topic (...)
│   └── Chapter ("Optics")
│       └── Topic (...)
│
├── Batch ("NEET-2025-A")
│   ├── session → Academic Session (2025-2026)
│   ├── group → Group ("Main Campus")
│   │
│   ├── BatchStudent (enrollments):
│   │   ├── Student: Naveen Reddy
│   │   ├── Student: Kavya Saxena
│   │   └── Student: Amit Gupta
│   │
│   └── BatchTeacher (assignments):
│       ├── Teacher: Dr. Sharma → Subject: Physics
│       ├── Teacher: Ms. Iyer → Subject: Chemistry
│       └── Teacher: Mr. Jain → Subject: Biology
│
└── Reference Data (standalone lookup tables):
    ├── Language (English, Hindi)
    ├── State (Maharashtra, Karnataka)
    ├── City (Mumbai, Bangalore) → belongs to State
    ├── Religion (Hindu, Muslim, Christian)
    └── School (ABC School) → has State, City, Religion
```

### How It Maps

```
Session ──────→ Batch ──────→ BatchStudent ──────→ Student
   │              │                                    │
   │              ├──────→ BatchTeacher ──────→ Teacher
   │              │                              │
   │              │                              ├──→ ScheduledClass
   │              │                              └──→ Test
   │              │
   └──→ Chapter ──┼──→ ScheduledClass (what's taught in class)
         │        ├──→ Test (what's tested)
         │        └──→ StudyMaterial (what to study)
         │
         └──→ Topic ──→ Question (exam questions)
```

### Admin Panel Locations

| Model | Sidebar Path | Key Features |
|-------|-------------|--------------|
| Academic Sessions | ACADEMICS → Academic sessions | `is_current` toggle, status badge |
| Groups | ACADEMICS → Groups | Status badge |
| Categories | ACADEMICS → Categories | Group FK, show_in_student flag |
| Subjects | ACADEMICS → Subjects | **Chapter inline**, type badge |
| Chapters | ACADEMICS → Chapters | **Topic inline**, session/group/subject FKs |
| Topics | ACADEMICS → Topics | Chapter FK, duration, complexity |
| Batches | ACADEMICS → Batches | Session/Group FKs, capacity, M2M teachers |
| Batch Students | ACADEMICS → Batch students | Batch + Student FKs, enrollment date |
| Batch Teachers | ACADEMICS → Batch teachers | Batch + Teacher + Subject FKs |

---

## 6. Layer 5: Operational Modules

These are the **daily-use features** that reference Layer 3 (Users) and Layer 4 (Academics):

### 6.1 Classes (Live/Recorded)

```
ScheduledClass
├── teacher → Teacher (who teaches)
├── batch → Batch (who attends)
├── chapter → Chapter (what's taught)
├── topic → Topic (specific topic)
├── youtube_channel → YouTubeChannel (where it streams)
├── scheduled_date + start/end time
├── class_type: LIVE / RECORDED / HYBRID
├── status: SCHEDULED / LIVE / COMPLETED / CANCELLED
│
├── ClassAccessToken (per student):
│   ├── student → Student
│   └── token + expiry (controls access)
│
└── ClassWatchTime (analytics):
    ├── student → Student
    ├── watch_duration_seconds
    └── device → UserDevice
```

### 6.2 Assessments (Tests)

```
Test
├── subject → Subject
├── chapter → Chapter
├── batch → Batch (target audience)
├── teacher → Teacher (creator)
├── test_type: ONLINE / OFFLINE / PRACTICE / MOCK
├── total_marks, duration_minutes, passing_percentage
│
├── TestSection (grouping):
│   └── subject → Subject (section-level subject)
│
├── Question:
│   ├── subject → Subject
│   ├── chapter → Chapter
│   ├── topic → Topic
│   ├── question_type: MCQ / MSQ / NUMERICAL / SUBJECTIVE
│   ├── difficulty: EASY / MEDIUM / HARD
│   └── parent_question → Question (for sub-questions)
│
├── TestAttempt (student takes the test):
│   ├── student → Student
│   ├── score, percentage, status
│   └── TestAttemptAnswer (per question):
│       ├── question → Question
│       └── selected_option, is_correct, marks_obtained
│
└── TestFeedback:
    ├── student → Student
    ├── rating (1-5), feedback text
    └── attempt → TestAttempt
```

### 6.3 Attendance

```
Attendance
├── user_id (UUID — polymorphic, can be Student or Teacher)
├── user_type: STUDENT / TEACHER
├── batch → Batch
├── academic_session → AcademicSession
├── live_class → ScheduledClass (optional — class-linked attendance)
├── date, check_in_time, check_out_time
├── status: PRESENT / ABSENT / LATE / ON_LEAVE / HALF_DAY
│
├── AttendanceCorrectionRequest:
│   ├── attendance → Attendance
│   ├── requested correction + reason
│   └── approval_status: PENDING / APPROVED / REJECTED
│
└── AttendanceSummary (aggregated):
    ├── user_id, batch, academic_session
    ├── month/year
    └── present_days, absent_days, late_days, attendance_percentage
```

### 6.4 Communication

```
SupportTicket → TicketMessage (thread)
Announcement → AnnouncementRead (tracking)
DirectMessage (self-referencing thread via parent_message)
Notification (push/email/sms queue)
```

### 6.5 Materials

```
StudyMaterial (PDF/Video/Notes)
├── subject → Subject
├── chapter → Chapter
├── topic → Topic
├── batch → Batch
└── MaterialAccess (download/view tracking)

PhotoGallery (event photos)
Scholarship (financial aid records)
TopperStudent → Student (achievement showcase)
```

### 6.6 Sessions Tracking

```
UserDevice (browser/app fingerprint)
├── UserSession (active login sessions)
│   └── UserActivity (page views, actions)
└── LoginHistory (every login attempt — success/fail)
```

### 6.7 Audit & Compliance

```
AuditLog (auto-captured by middleware):
├── Every POST/PUT/PATCH/DELETE request
├── user_id, user_type, action, IP, user_agent
├── request_body (passwords redacted)
└── response_status

AuditPurgePolicy (auto-cleanup rules)
BackupPolicy → BackupHistory (database backup tracking)
```

### 6.8 System Configuration

```
SystemSetting (key-value runtime settings)
FeatureFlag (toggle features on/off)
MFAPolicy (MFA enforcement rules per tenant)
MaintenanceWindow (scheduled downtime)
FounderInfo (about the institute)
EnquiryForm (student inquiry submissions)
AIFeatureConfig (AI feature toggles)
ClassLinkConfig (class URL configuration)
AttendanceRule (attendance business rules)
```

---

## 7. Complete Mapping — How Everything Connects

### The Golden Path: From Tenant to Test Score

```
1. TENANT created         → "ABC Coaching Institute"
2. ADMIN created          → Kavya (ACADEMIC_ADMIN, Role: "Academic Coordinator")
3. ROLE assigned          → "Academic Coordinator" role has 12 permissions
4. SESSION created        → "2025-2026" (is_current: True)
5. GROUP created          → "Main Campus"
6. SUBJECT created        → "Physics" (type: THEORY)
7. CHAPTER created        → "Mechanics" (under Physics, class 11)
8. TOPIC created          → "Newton's Laws" (under Mechanics)
9. BATCH created          → "NEET-2025-A" (session: 2025-2026, group: Main Campus)
10. TEACHER created       → Dr. Sharma (youtube_channel_verified: True)
11. BATCH_TEACHER created → Dr. Sharma → NEET-2025-A → Physics
12. STUDENT created       → Naveen Reddy (exam_target: NEET, class: 12)
13. BATCH_STUDENT created → Naveen → NEET-2025-A (enrolled)
14. PARENT created        → Mr. Reddy (primary_student: Naveen, relationship: FATHER)
15. CLASS scheduled       → Physics class by Dr. Sharma for NEET-2025-A, Chapter: Mechanics
16. ATTENDANCE marked     → Naveen: PRESENT in NEET-2025-A on 2026-02-16
17. TEST created          → "Mechanics Unit Test" for NEET-2025-A, Subject: Physics
18. QUESTION added        → MCQ on Newton's 2nd Law, Chapter: Mechanics, Topic: Newton's Laws
19. TEST_ATTEMPT created  → Naveen attempts the test, scores 85/100
20. PARENT views          → Mr. Reddy sees Naveen's test score (can_view_results: True)
```

### Cross-App Reference Map

| This Model... | References These... | From These Apps... |
|---------------|--------------------|--------------------|
| **ScheduledClass** | Teacher, Batch, Chapter, Topic, YouTubeChannel | accounts, academics, classes |
| **Test** | Teacher, Batch, Subject, Chapter | accounts, academics |
| **Question** | Subject, Chapter, Topic, Test, TestSection | academics, assessments |
| **Attendance** | Batch, AcademicSession, ScheduledClass | academics, classes |
| **StudyMaterial** | Subject, Chapter, Topic, Batch | academics |
| **TestAttempt** | Student, Test | accounts, assessments |
| **BatchStudent** | Student, Batch | accounts, academics |
| **BatchTeacher** | Teacher, Batch, Subject | accounts, academics |

---

## 8. Demo Walkthrough Script

Use this script when presenting the admin panel in a demo:

### Opening (Dashboard — 2 minutes)

> "This is the ENABLE PROGRAM Admin Console. When you log in, the first thing you see is the **dashboard** with live statistics — total students, teachers, active batches, and today's attendance. These numbers update in real-time."

**Show:** Dashboard stat cards with animated counters.

### Sidebar Navigation (1 minute)

> "On the left, the sidebar organizes all 62 models across 12 app sections. Each section is collapsible — click ACADEMICS to collapse it, click again to expand. There's a search bar at the top to quickly find any model."

**Show:** Collapse/expand ACADEMICS, type "batch" in sidebar search.

### RBAC Demo (3 minutes)

> "Let's start with how access control works. Go to **ACCOUNTS → Roles**."

> "Each role has a **type** (System, Tenant Default, Custom), an **applies to** scope (Admin, Teacher, Student, Parent), and a **level** number — higher means more authority."

> "Click on a role to see its permissions. Permissions follow the format `module.action.scope` — for example, `students.read.batch` means 'can read student records in their assigned batch'. Scope goes from OWN (only own records) up to GLOBAL (everything)."

> "Roles can **inherit** from a parent role — the Head Teacher inherits all Teacher permissions plus additional ones."

**Show:** Roles list → click a role → show RolePermission inline → point out permission codes.

### User Types Demo (3 minutes)

> "Now let's see the users. **ACCOUNTS → Admins** — each admin has an admin_type that determines their access level. Super Admin has full access, Academic Admin only sees academic modules."

> "**ACCOUNTS → Teachers** — note the YouTube integration fields and inline permissions (can override attendance, can edit student profiles)."

> "**ACCOUNTS → Students** — the core users. Filter by Exam Target: NEET to see all NEET students. Export them as CSV with one click."

**Show:** Admins list (colored admin_type badges) → Teachers → Students → use column filter on Exam Target.

### Academic Structure Demo (3 minutes)

> "The academic hierarchy flows: Session → Group → Subject → Chapter → Topic. Let's see it."

> "Open **Subjects** — click Physics — you'll see the Chapters inline. Each chapter has topics nested inside."

> "Open **Batches** — this is where students and teachers are assigned. A batch like 'NEET-2025-A' links to a Session and Group. BatchStudents and BatchTeachers connect people to batches."

**Show:** Subjects → click Physics → show Chapter inline → back → Batches → Batch Students.

### Operations Demo (3 minutes)

> "With the structure in place, daily operations happen here:"

> "**Scheduled Classes** — each class links a teacher, batch, chapter, and YouTube channel."

> "**Attendance** — mark present/absent/late for each student. Color-coded status badges make scanning easy."

> "**Tests** — create a test linked to a subject and batch. Add questions inline."

**Show:** Scheduled Classes list → Attendance list → Tests list → click a test to show Question inline.

### Import/Export Demo (1 minute)

> "22 models support CSV import/export. Click the purple 'Import CSV' button, upload a file, and records are created instantly. Use 'Export All CSV' for bulk data download."

**Show:** Students list → click Import CSV → show the dialog.

### Column Filtering Demo (1 minute)

> "Every column has a filter icon. Click it to see all unique values with checkboxes. Select multiple values across multiple columns — it's instant, no page reload."

**Show:** Batch Students → filter by Batch → filter by Status → show badge counts.

### Theme & UI Demo (1 minute)

> "The admin supports Light, Dark, and System themes. Click your profile in the top-right → switch to Dark mode. Everything adapts instantly."

**Show:** Profile dropdown → switch theme → show dark mode.

---

## 9. Sidebar → Model Mapping

This shows exactly what each sidebar item maps to in the database:

### ACCOUNTS (7 models)

| Sidebar Item | DB Table | Primary Purpose |
|-------------|----------|-----------------|
| Students | `students` | Student user records |
| Teachers | `teachers` | Teacher user records |
| Admins | `admins` | Admin user records |
| Parents | `parents` | Parent user records |
| Roles | `roles` | RBAC role definitions |
| Permissions | `permissions` | Atomic permission definitions |
| Role permissions | `role_permissions` | Role ↔ Permission junction |

### ACADEMICS (15 models)

| Sidebar Item | DB Table | Primary Purpose |
|-------------|----------|-----------------|
| Academic sessions | `academic_sessions` | Year/term boundaries |
| Groups | `groups` | Branch/division grouping |
| Categories | `categories` | Sub-grouping within Group |
| Subjects | `subjects` | Courses taught |
| Subject sections | `subject_sections` | Sections within Subject |
| Chapters | `chapters` | Units within Subject |
| Topics | `topics` | Lessons within Chapter |
| Batches | `batches` | Student groups (NEET-A, JEE-B) |
| Batch students | `batch_students` | Student ↔ Batch enrollment |
| Batch teachers | `batch_teachers` | Teacher ↔ Batch ↔ Subject assignment |
| Languages | `languages` | Reference: instruction languages |
| States | `states` | Reference: Indian states |
| Cities | `cities` | Reference: cities (FK → State) |
| Religions | `religions` | Reference: religions |
| Schools | `schools` | Reference: schools (FK → State, City) |

### ASSESSMENTS (7 models)

| Sidebar Item | DB Table | Primary Purpose |
|-------------|----------|-----------------|
| Tests | `tests` | Exam/quiz definitions |
| Test sections | `test_sections` | Sections within Test |
| Questions | `questions` | Individual test questions |
| Test attempts | `test_attempts` | Student taking a test |
| Test attempt answers | `test_attempt_answers` | Per-question answer records |
| Test feedbacks | `test_feedbacks` | Student rating/feedback on test |
| Offline test marks | `offline_test_marks` | Manual marks for non-digital tests |

### ATTENDANCE (3 models)

| Sidebar Item | DB Table | Primary Purpose |
|-------------|----------|-----------------|
| Attendances | `attendances` | Daily attendance records |
| Attendance correction requests | `attendance_correction_requests` | Edit requests |
| Attendance summaries | `attendance_summaries` | Monthly aggregations |

### CLASSES (4 models)

| Sidebar Item | DB Table | Primary Purpose |
|-------------|----------|-----------------|
| YouTube channels | `youtube_channels` | Linked YouTube channels |
| Scheduled classes | `scheduled_classes` | Live/recorded class schedule |
| Class access tokens | `class_access_tokens` | Per-student class access |
| Class watch times | `class_watch_times` | Video viewing analytics |

### COMMUNICATION (6 models)

| Sidebar Item | DB Table | Primary Purpose |
|-------------|----------|-----------------|
| Support tickets | `support_tickets` | Help desk tickets |
| Ticket messages | `ticket_messages` | Thread replies on tickets |
| Announcements | `announcements` | Institute-wide messages |
| Announcement reads | `announcement_reads` | Who read which announcement |
| Direct messages | `direct_messages` | 1-to-1 messaging |
| Notifications | `notifications` | Push/email/SMS queue |

### MATERIALS (5 models)

| Sidebar Item | DB Table | Primary Purpose |
|-------------|----------|-----------------|
| Study materials | `study_materials` | PDFs, videos, notes |
| Material accesses | `material_accesses` | Download/view tracking |
| Photo galleries | `photo_galleries` | Event/institute photos |
| Scholarships | `scholarships` | Financial aid records |
| Topper students | `topper_students` | Achievement showcase |

### SESSIONS TRACKING (4 models)

| Sidebar Item | DB Table | Primary Purpose |
|-------------|----------|-----------------|
| User devices | `user_devices` | Browser/device fingerprints |
| User sessions | `user_sessions` | Active login sessions |
| Login history | `login_history` | Login attempt audit trail |
| User activities | `user_activities` | In-app action tracking |

### AUDIT (4 models)

| Sidebar Item | DB Table | Primary Purpose |
|-------------|----------|-----------------|
| Audit logs | `audit_logs` | API request audit trail |
| Audit purge policies | `audit_purge_policies` | Auto-cleanup rules |
| Backup policies | `backup_policies` | Database backup configuration |
| Backup history | `backup_history` | Backup execution records |

### SYSTEM CONFIG (9 models)

| Sidebar Item | DB Table | Primary Purpose |
|-------------|----------|-----------------|
| System settings | `system_settings` | Key-value runtime config |
| Feature flags | `feature_flags` | Feature toggles |
| MFA policies | `mfa_policies` | MFA enforcement rules |
| Maintenance windows | `maintenance_windows` | Scheduled downtime |
| Founder infos | `founder_infos` | About the institute |
| Enquiry forms | `enquiry_forms` | Student inquiry submissions |
| AI feature configs | `ai_feature_configs` | AI feature configuration |
| Class link configs | `class_link_configs` | Class URL setup |
| Attendance rules | `attendance_rules` | Attendance business rules |

### REALTIME (1 model)

| Sidebar Item | DB Table | Primary Purpose |
|-------------|----------|-----------------|
| Realtime events | `realtime_events` | WebSocket event tracking |

### TENANTS (1 model)

| Sidebar Item | DB Table | Primary Purpose |
|-------------|----------|-----------------|
| Tenants | `tenants` | Multi-tenant institute records |

---

## 10. Entity Relationships — Complete FK Map

### Primary Relationships (Non-Tenant)

```
Student.batch ──────────────→ Batch
Teacher.reporting_to ───────→ Teacher (self)
Admin.role ─────────────────→ Role
Parent.primary_student ─────→ Student
ParentStudent.parent ───────→ Parent
ParentStudent.student ──────→ Student

Category.group ─────────────→ Group
Chapter.session ────────────→ AcademicSession
Chapter.group ──────────────→ Group
Chapter.subject ────────────→ Subject
Topic.chapter ──────────────→ Chapter
SubjectSection.subject ─────→ Subject
Batch.session ──────────────→ AcademicSession
Batch.group ────────────────→ Group
BatchStudent.batch ─────────→ Batch
BatchStudent.student ───────→ Student
BatchTeacher.batch ─────────→ Batch
BatchTeacher.teacher ───────→ Teacher
BatchTeacher.subject ───────→ Subject
City.state ─────────────────→ State
School.state ───────────────→ State
School.city ────────────────→ City
School.religion ────────────→ Religion

RolePermission.role ────────→ Role
RolePermission.permission ──→ Permission
Role.parent_role ───────────→ Role (self)

ScheduledClass.teacher ─────→ Teacher
ScheduledClass.batch ───────→ Batch
ScheduledClass.chapter ─────→ Chapter
ScheduledClass.topic ───────→ Topic
ScheduledClass.youtube_channel → YouTubeChannel
YouTubeChannel.assigned_teacher → Teacher
ClassAccessToken.scheduled_class → ScheduledClass
ClassAccessToken.student ───→ Student
ClassWatchTime.scheduled_class → ScheduledClass
ClassWatchTime.student ─────→ Student

Test.subject ───────────────→ Subject
Test.chapter ───────────────→ Chapter
Test.batch ─────────────────→ Batch
Test.teacher ───────────────→ Teacher
TestSection.test ───────────→ Test
Question.test ──────────────→ Test
Question.section ───────────→ TestSection
Question.subject ───────────→ Subject
Question.chapter ───────────→ Chapter
Question.topic ─────────────→ Topic
Question.parent_question ───→ Question (self)
TestAttempt.test ───────────→ Test
TestAttempt.student ────────→ Student
TestAttemptAnswer.attempt ──→ TestAttempt
TestAttemptAnswer.question ─→ Question
TestFeedback.test ──────────→ Test
TestFeedback.student ───────→ Student
OfflineTestMarks.student ───→ Student
OfflineTestMarks.subject ───→ Subject

Attendance.batch ───────────→ Batch
Attendance.academic_session → AcademicSession
Attendance.live_class ──────→ ScheduledClass
AttendanceCorrectionRequest.attendance → Attendance
AttendanceSummary.batch ────→ Batch
AttendanceSummary.academic_session → AcademicSession

StudyMaterial.subject ──────→ Subject
StudyMaterial.chapter ──────→ Chapter
StudyMaterial.topic ────────→ Topic
StudyMaterial.batch ────────→ Batch
MaterialAccess.material ────→ StudyMaterial
TopperStudent.student ──────→ Student

TicketMessage.ticket ───────→ SupportTicket
AnnouncementRead.announcement → Announcement
DirectMessage.parent_message → DirectMessage (self)

UserSession.device ─────────→ UserDevice
LoginHistory.device ────────→ UserDevice
UserActivity.session ───────→ UserSession

BackupHistory.policy ───────→ BackupPolicy
```

---

## 11. Interactive Demo Page

An interactive HTML page is available at:

**`/u01/app/django/apps/docs/admin_hierarchy_interactive.html`**

Open this file in a browser to explore:
- Clickable hierarchy tree
- Animated flow diagrams
- Role/permission explorer
- User type comparison
- Hover tooltips with field details

---

*Document generated for ENABLE PROGRAM Admin Console v4.0 Demo*
*Last updated: February 16, 2026*
