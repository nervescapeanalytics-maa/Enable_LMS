# Live Classes & YouTube — Complete Administrator Guide

> **Audience:** Non-technical administrators (school admins, coaching center managers, training coordinators)
> **Last Updated:** March 2026
> **Version:** 2.0

---

## Table of Contents

1. [Overview — What Is This Section?](#1-overview--what-is-this-section)
2. [Quick Start Checklist](#2-quick-start-checklist)
3. [YouTube Integration Configs](#3-youtube-integration-configs)
4. [Class Link Configurations](#4-class-link-configurations)
5. [YouTube Channels](#5-youtube-channels)
6. [Scheduled Classes](#6-scheduled-classes)
7. [Class Access Tokens](#7-class-access-tokens) ← *detailed with demo & flow diagrams*
8. [Class Watch Times](#8-class-watch-times) ← *detailed with engagement scoring & examples*
9. [Real-World Scenarios](#9-real-world-scenarios)
10. [Troubleshooting & FAQ](#10-troubleshooting--faq)
11. [Glossary](#11-glossary)
12. [Tips & Best Practices](#12-tips--best-practices)
13. [Scheduling YouTube Live Classes — Complete Setup with Demo Values](#13-scheduling-youtube-live-classes--complete-setup-with-demo-values) ← **NEW**

---

## 1. Overview — What Is This Section?

The **Live Classes & YouTube** section in the Admin Panel lets you manage everything related to conducting live video classes for your students. Think of it as the control room for your institution's online classes.

### What You Can Do Here:
- **Connect your YouTube channel** so teachers can broadcast live classes
- **Configure platforms** (YouTube, Zoom, Google Meet, etc.) for video sessions
- **Schedule live classes** and share links with students automatically
- **Track who watched** each class and for how long
- **Manage access** — control which students can join which classes
- **View engagement data** — see if students are paying attention

### The Six Sub-Sections:

| Sub-Section | What It Does | When You Use It |
|---|---|---|
| **YouTube integration configs** | Connects your LMS to YouTube | One-time setup + occasional updates |
| **Class Link Configurations** | Sets up how class links are created | One-time setup per platform |
| **You Tube channels** | Manages YouTube channel credentials | When adding/changing channels |
| **Scheduled classes** | Lists all scheduled/live/past classes | Daily — to schedule and monitor classes |
| **Class access tokens** | Controls student access to classes | When managing individual access |
| **Class watch times** | Shows student viewing analytics | When reviewing attendance/engagement |

---

## 2. Quick Start Checklist

If you're setting up live classes for the first time, follow these steps in order:

- [ ] **Step 1:** Create a YouTube Integration Config (connects your LMS to YouTube)
- [ ] **Step 2:** Add a Class Link Configuration (sets up auto-link generation)
- [ ] **Step 3:** Register your YouTube Channel (optional — for channel-level management)
- [ ] **Step 4:** Create your first Scheduled Class
- [ ] **Step 5:** Verify students can access the class link

> **Time needed:** About 30 minutes for initial setup.

---

## 3. YouTube Integration Configs

### What Is This?

This is where you connect your LMS to your YouTube account. Think of it as linking your school's YouTube channel so the system can:
- Create live streams automatically
- Upload class recordings
- Fetch video information
- Track video views

### Field-by-Field Guide

#### Basic Information

| Field | What It Is | Example | Required? |
|---|---|---|---|
| **Name** | A friendly label for this integration | "ABC Academy YouTube" | Yes |
| **Enabled (is_active)** | Turns the integration on or off | ✅ Checked = active | Yes |
| **Description** | Optional notes for your team | "Used for Class 11 Physics live classes" | No |

> **💡 Tip:** If you manage multiple YouTube channels (e.g., one per department), create a separate integration for each and name them clearly.

> **⚠️ If left blank:** The "Name" field is required. Without it, you cannot save the configuration.

---

#### YouTube Channel Details

| Field | What It Is | How to Find It | Example |
|---|---|---|---|
| **Channel ID** | YouTube's unique identifier for your channel | YouTube Studio → Settings → Channel → Advanced Settings | `UCxxxxxxxxxxxxxxxxxxxxxxxx` |
| **Channel Name** | Your channel's display name | Visible on your YouTube channel page | `ABC Academy Live Classes` |
| **Playlist IDs** | IDs of playlists for organizing recordings | YouTube Studio → Content → Playlists → click a playlist → URL | `PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| **Auto Sync Videos** | Automatically import new videos from YouTube | Toggle on/off | ☐ Unchecked (off by default) |

**How to find your Channel ID:**
1. Open [YouTube Studio](https://studio.youtube.com)
2. Click the **Settings** gear icon (bottom-left)
3. Click **Channel** → **Advanced Settings**
4. Your **Channel ID** is displayed — it starts with `UC`

**How to find Playlist IDs:**
1. In YouTube Studio, go to **Content** → **Playlists**
2. Click on a playlist
3. Look at the URL — the playlist ID is the code after `list=`
4. It starts with `PL` followed by a long string

> **⚠️ If Channel ID is wrong:** The system won't be able to find your channel. Live streaming and video sync will fail. Double-check it starts with "UC".

> **⚠️ If left blank:** The integration will save but won't be able to connect to any specific channel. You'll need to fill this in before live streaming works.

---

#### API Credentials

| Field | What It Is | Where to Get It | Format |
|---|---|---|---|
| **API Key** | A password that lets the system read your YouTube data | Google Cloud Console → APIs & Services → Credentials | Long string of letters and numbers |
| **API Secret** | An additional secret (rarely needed for YouTube) | Same location as API Key | Long encrypted string |
| **API Endpoint** | The URL the system talks to | Pre-filled automatically | `https://www.googleapis.com/youtube/v3` |

**How to get your API Key:**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select or create a project
3. Go to **APIs & Services** → **Credentials**
4. Click **+ Create Credentials** → **API Key**
5. Copy the generated key
6. **Important:** Go to **APIs & Services** → **Library**, search for "YouTube Data API v3", and click **Enable**

> **⚠️ If API Key is wrong:** All YouTube features will stop working. You'll see errors like "Invalid API key" in health checks.

> **⚠️ If API Endpoint is wrong:** The system will try to connect to the wrong server. Always use `https://www.googleapis.com/youtube/v3`.

> **🔒 Security:** Your API Key is stored encrypted. Never share it publicly. If you think it's been compromised, create a new one in Google Cloud Console and delete the old one.

---

#### OAuth Authentication (for Live Streaming)

| Field | What It Is | When It's Needed | Manual Edit? |
|---|---|---|---|
| **OAuth Client ID** | Identifies your app to Google | For live streaming and uploads | Yes — enter from Google Cloud |
| **OAuth Client Secret** | The private password for your app | Always paired with Client ID | Yes — enter from Google Cloud |
| **OAuth Token** | Temporary permission to act on your behalf | Auto-generated during login | ❌ Do not edit manually |
| **OAuth Refresh Token** | Used to get new tokens when they expire | Auto-generated | ❌ Do not edit manually |
| **OAuth Token Expiry** | When the current token stops working | Auto-managed | ❌ Do not edit manually |

**How to get OAuth credentials:**
1. Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
2. Click **+ Create Credentials** → **OAuth 2.0 Client ID**
3. Application type: **Web application**
4. Add your LMS domain to **Authorized redirect URIs**
5. Copy the **Client ID** and **Client Secret**

> **💡 Tip:** You only need OAuth if you want the system to create live streams or upload recordings automatically. If you only want to embed existing YouTube videos, an API Key alone is sufficient.

> **⚠️ If configured incorrectly:** Live stream creation will fail, and you'll see "Authentication error" messages. Verify the Client ID and Secret match what's in Google Cloud Console.

---

#### Rate Limits & Quotas

| Field | What It Is | Default | Recommended |
|---|---|---|---|
| **Max Requests per Hour** | How many API calls the system can make per hour | 100 | 50–100 for small institutions, 200+ for large |
| **Max Requests per User** | How many calls a single user can trigger per hour | 20 | 10–30 |
| **Daily Budget Limit** | Maximum daily spending (for paid APIs) | Blank (free) | Leave blank for YouTube |
| **Monthly Budget Limit** | Maximum monthly spending | Blank (free) | Leave blank for YouTube |

> **⚠️ YouTube's free quota is ~10,000 units per day.** Each API call costs 1–100 units depending on the type. If you exceed the quota, YouTube features will stop working until the next day.

> **💡 Tip:** If you have 500+ students watching live classes daily, consider applying for a [YouTube API quota increase](https://support.google.com/youtube/contact/yt_api_form).

---

#### Connection Health

| Field | What It Means | Action Needed |
|---|---|---|
| **Healthy** 💚 | Everything is working perfectly | None |
| **Degraded** 🟡 | Working but with some issues (slow responses) | Monitor — may resolve on its own |
| **Down** 🔴 | Not working at all | Check API key, internet connection, and YouTube status |
| **Unknown** ⚪ | Status hasn't been checked yet | Wait for the next automatic check, or trigger manually |

> **⚠️ If status is "Down":** Check these things in order:
> 1. Is the **API Key** correct?
> 2. Is the **YouTube Data API v3** enabled in Google Cloud?
> 3. Has the daily **quota** been exceeded?
> 4. Is YouTube itself experiencing an outage? Check [Google Status Dashboard](https://www.google.com/appsstatus)

---

## 4. Class Link Configurations

### What Is This?

This tells the system which video platform to use when teachers create live classes, and how to automatically generate meeting/streaming links. You set this up once per platform.

### Field-by-Field Guide

#### Platform Selection

| Field | What It Is | Options | Recommendation |
|---|---|---|---|
| **Platform** | Which video service to use | YouTube Live, Zoom, Google Meet, Microsoft Teams, Custom URL | YouTube Live for large classes, Zoom for interactive sessions |
| **Active (is_active)** | Whether this platform can be used | ✅ On / ❌ Off | Turn on only platforms you actually use |
| **Default (is_default)** | Pre-selected when teachers create a class | ✅ Yes / ❌ No | Set your most-used platform as default |

**Which platform should you choose?**

| Scenario | Best Platform | Why |
|---|---|---|
| 100+ students, lecture-style | **YouTube Live** | Free, unlimited viewers, automatic recording |
| 10–50 students, interactive Q&A | **Zoom** | Breakout rooms, screen sharing, hand-raise |
| Google Workspace school | **Google Meet** | Already integrated with Google Classroom |
| Microsoft 365 school | **Microsoft Teams** | Built-in with your existing tools |
| Any other platform | **Custom URL** | Paste any link manually |

> **⚠️ Only one platform can be "Default."** If you mark a new one as default, remember to unmark the previous default.

---

#### Class Settings

| Field | What It Is | Default | Good For |
|---|---|---|---|
| **Auto Generate Link** | System creates the link automatically | Off | Saves teachers time when turned on |
| **Generate Minutes Before** | How early to create the link | 15 min | 10–30 min is ideal for most cases |
| **Default Duration** | Assumed class length | 60 min | Common values: 45, 60, 90 minutes |
| **Auto Record** | Automatically start recording | Off | Turn on if you want all classes recorded |
| **Auto Admit Participants** | Students join without waiting room | On | Turn off for private tutoring sessions |

> **💡 Tip for coaching centers:** Set Auto Generate Link = ON and Generate Minutes Before = 15. This means students get their class link automatically 15 minutes before the session starts.

> **💡 Tip for schools:** Set Auto Record = ON so all classes are recorded. Parents can review recordings later, and absent students can catch up.

> **⚠️ If Auto Generate Link is ON but no API credentials are set:** Links won't be created and teachers will see an error. Either add your API credentials or keep this turned OFF and let teachers paste links manually.

> **⚠️ If Generate Minutes Before is too short (e.g., 1 minute):** Students won't have time to click the link before class starts. Recommended: 10–30 minutes.

> **⚠️ If Default Duration is wrong:** For YouTube Live, this affects when the system considers the class "ended." For Zoom/Meet, it sets the meeting's scheduled duration.

---

#### API Credentials (Technical Section)

| Field | What It Is | Example | When Needed |
|---|---|---|---|
| **API Endpoint** | The platform's API URL | `https://www.googleapis.com/youtube/v3` | Only if using auto-generate |
| **API Key Reference** | Name of the System Setting storing your API key | `YOUTUBE_API_KEY` | For auto-generate with YouTube |
| **Client ID** | OAuth Client ID for the platform | `123456-abc.apps.googleusercontent.com` | For creating live streams |
| **Client Secret Reference** | Name of the System Setting storing the secret | `YOUTUBE_CLIENT_SECRET` | Paired with Client ID |
| **OAuth Token Reference** | Name of the System Setting storing the OAuth token | `YOUTUBE_OAUTH_TOKEN` | Auto-generated |

> **💡 Why "Reference" instead of the actual key?** For security, the actual API keys are stored in **System Settings** (a separate, more secure section). Here you only enter the *name* of the setting that holds the key. This way, keys aren't exposed in the Class Link config.

> **⚠️ If using Custom URL platform:** You can skip this entire section. Custom URL means teachers paste their own links.

---

#### Webhook & Advanced Settings

##### What Is a Webhook?

A **webhook** is a way for an external platform (YouTube, Zoom, etc.) to **automatically notify your LMS** when something happens — without the LMS having to constantly check. Think of it like a doorbell: instead of checking the door every minute, the doorbell rings *when someone arrives*.

##### When Would You Need a Webhook?

| Event Example | Without Webhook | With Webhook |
|---|---|---|
| Teacher starts a live stream | LMS checks YouTube every few minutes to detect it | YouTube tells the LMS **instantly** "stream started" |
| Live stream ends | LMS discovers 5–10 minutes later | YouTube notifies LMS **immediately** → attendance marked right away |
| New recording available | LMS finds it during next sync cycle | YouTube pushes notification → recording linked to class automatically |
| Quota exceeded | LMS finds out on next API call attempt | YouTube warns immediately → system shows admin alert |

##### Do I Need To Set This Up?

| Scenario | Do You Need Webhook? | Why |
|---|---|---|
| Small institution (< 500 students) | **No** | The system polls YouTube on a schedule — good enough for most |
| Large institution (1000+ students, many live classes daily) | **Optional** | Faster status updates, near-instant attendance marking |
| Compliance/audit requirements (need exact start/end timestamps) | **Recommended** | Webhooks give second-accurate event timing |
| Just embedding YouTube links manually | **No** | No automation needed |

##### Field Details

| Field | What It Is | Example Value | Who Sets It |
|---|---|---|---|
| **Webhook URL** | The address where YouTube sends notifications | `https://lms.yourschool.com/api/webhooks/youtube/` | Your IT team |
| **Config JSON** | Extra platform-specific settings in key-value format | `{"notify_on_start": true, "notify_on_end": true}` | Your IT team |

##### How Webhook Works — Step by Step

```
1. IT team sets Webhook URL in Class Link Config
2. LMS registers this URL with YouTube (done automatically)
3. When a live stream starts → YouTube sends a message to the URL
4. LMS receives the message → updates class status to "LIVE"
5. When the stream ends → YouTube sends another message
6. LMS marks class as "COMPLETED" and starts attendance calculation
```

##### What If I Set a Wrong Webhook URL?

- Notifications will silently fail (YouTube tries, gets an error, gives up)
- The LMS will still work — it falls back to periodic polling
- No data is lost, but status updates will be delayed by a few minutes
- Fix: correct the URL and save. The next event will work normally.

##### What If I Leave It Blank?

- **Perfectly fine.** The LMS will check YouTube periodically (every 2–5 minutes depending on load)
- Status updates (class started, class ended) will be slightly delayed
- Attendance marking works the same — just triggered later

> **💡 Bottom line:** Leave Webhook URL blank unless your IT team specifically sets one up. Everything works fine without it — just a few minutes slower for status updates.

> **💡 Config JSON:** Only needed for special cases (e.g., custom notification filters). If you don't know what to put here, leave it empty.

---

## 5. YouTube Channels

### What Is This?

This section manages the YouTube channel accounts that your institution uses for live streaming. If your school has one YouTube channel, you'll have one entry here. Larger institutions with department-specific channels will have multiple entries.

### Field-by-Field Guide

#### Channel Information

| Field | What It Is | Example | Required? |
|---|---|---|---|
| **Channel ID** | YouTube's unique ID for the channel | `UCq1Xm2B3C4D5E6F7G8H9` | Yes |
| **Channel Name** | Display name shown to students | `XYZ Academy — Physics Department` | Recommended |
| **Channel URL** | Full URL to the channel page | `https://www.youtube.com/channel/UCq1Xm2B...` | Optional |

#### Channel Status

| Field | What It Means | When to Change |
|---|---|---|
| **Status: Active** | Channel is ready for live streaming | Set when channel is verified and working |
| **Status: Inactive** | Channel exists but is paused | When temporarily not using this channel |
| **Status: Revoked** | Access has been revoked by YouTube/Google | If OAuth credentials were revoked — re-authorize |
| **Status: Quota Exceeded** | Daily YouTube API limit reached | Automatic — resets next day |
| **Verification: Verified** | Channel identity confirmed | After successful verification |
| **Verification: Pending** | Waiting for verification | Immediately after adding a new channel |
| **Verification: Failed** | Verification unsuccessful | Check channel ID and credentials |
| **Primary Channel** | The main channel for your institution | Only one channel should be marked primary |
| **Owned by Tenant** | Whether your institution owns this channel | Usually checked (yes) |

> **💡 Tip:** Mark your main channel as "Primary" so the system uses it by default when teachers create live classes.

#### API Quota

| Field | What It Is | Default |
|---|---|---|
| **Daily Quota Limit** | Maximum API calls per day | 10,000 |
| **Quota Used Today** | How many calls used so far today | 0 (resets daily) |
| **Quota Reset At** | When the quota counter resets | Usually midnight Pacific Time |

> **⚠️ If quota is exceeded:** No new live streams can be created, and video info won't update until the quota resets. This does NOT affect ongoing live streams already broadcasting.

#### OAuth Credentials

These fields store the authentication tokens for this specific channel. They work the same as described in [Section 3: OAuth Authentication](#oauth-authentication-for-live-streaming).

> **🔒 Security Warning:** These fields are collapsed by default because they contain sensitive information. Only expand and edit them if absolutely necessary or instructed by support.

---

## 6. Scheduled Classes

### What Is This?

This is where all live and recorded classes are listed. Each row represents one class session — whether it's upcoming, currently live, completed, or cancelled.

### Class Status Lifecycle

```
DRAFT → SCHEDULED → LIVE → COMPLETED
                  ↘ CANCELLED
                  ↘ RESCHEDULED → (new class created)
```

| Status | What It Means | What Happens |
|---|---|---|
| **Draft** | Class is being set up, not visible to students yet | Only admins/teachers can see it |
| **Scheduled** | Class is confirmed and visible to students | Students receive notification with class link |
| **Live** | Class is currently being broadcast | Students can join using the class link |
| **Completed** | Class session has ended | Recording becomes available (if auto-record is on) |
| **Cancelled** | Class was cancelled | Students are notified of cancellation |
| **Rescheduled** | Moved to a new date/time | A new class is created; old one marked as rescheduled |

### Key Fields

#### Class Details

| Field | What It Is | Example |
|---|---|---|
| **Class Code** | Unique identifier (auto-generated or manual) | `PHY-2026-001` |
| **Title** | What students see as the class name | `Kinematics — Chapter 3 (Live Session)` |
| **Description** | Additional details about the class | `Covering equations of motion and free fall problems` |
| **Teacher** | The teacher conducting this class | Select from registered teachers |
| **Batch** | Which student group this is for | `Class 12A — Morning Batch` |

#### Schedule

| Field | Format | Example |
|---|---|---|
| **Scheduled Date** | YYYY-MM-DD | `2026-03-25` |
| **Start Time** | HH:MM (24-hour) | `14:00` |
| **End Time** | HH:MM (24-hour) | `15:00` |
| **Duration** | Minutes (auto-calculated) | `60` |
| **Timezone** | Timezone identifier | `Asia/Kolkata` |

#### YouTube Streaming

| Field | What It Is | Auto-Filled? |
|---|---|---|
| **YouTube Channel** | Which channel to stream on | Select from registered channels |
| **Privacy Status** | Who can find the video on YouTube | Choose: Private or Unlisted |
| **Broadcast ID** | YouTube's unique ID for the live event | ✅ Yes — auto-generated |
| **Stream ID** | YouTube's ID for the stream | ✅ Yes |
| **Stream Key** | Secret key for OBS/streaming software | ✅ Yes — encrypted |
| **Stream URL** | Where to send the video feed | ✅ Yes |
| **Watch URL** | Link students use to watch | ✅ Yes — shared with students |
| **Embed URL** | For embedding in the LMS dashboard | ✅ Yes |
| **Recording ID** | YouTube video ID of the recording | ✅ Yes — after class ends |
| **Recording URL** | Link to the saved recording | ✅ Yes — after class ends |

> **💡 For most administrators:** You only need to set the **YouTube Channel** and **Privacy Status**. Everything else is handled automatically.

> **💡 Privacy guide:**
> - **Unlisted** = Anyone with the link can watch, but it won't appear in YouTube search. **Recommended** for most classes.
> - **Private** = Only specifically authorized YouTube accounts can watch. More secure but harder to manage.

#### Access Control

| Field | What It Is | When to Use |
|---|---|---|
| **Access Type: Batch Only** | Only students in the assigned batch can watch | Standard classroom setting |
| **Access Type: Multi-Batch** | Students from multiple batches can watch | Combined or revision classes |
| **Access Type: All Students** | All enrolled students can watch | Open lectures, orientation |
| **Access Type: Custom** | Hand-pick specific students | Special sessions, remedial classes |
| **Allowed Batches** | List of batch IDs (for Multi-Batch) | Use when combining batches |
| **Allowed Students** | List of student IDs (for Custom) | Use for selective access |
| **Requires Enrollment Check** | Verify student is enrolled before allowing access | Recommended: ON |

#### Attendance Settings

| Field | What It Is | Default | Recommended |
|---|---|---|---|
| **Attendance Mode: Automatic** | System marks attendance based on watch time | Default | For large classes (50+ students) |
| **Attendance Mode: Manual** | Teacher marks attendance manually | — | For small groups where teacher knows each student |
| **Attendance Mode: Hybrid** | System suggests, teacher confirms | — | Best balance of accuracy and control |
| **Threshold Minutes** | Minutes a student must watch to be marked present | 15 min | 10–20 min for a 60-min class |
| **Min Watch Percent** | Minimum % of class to watch for "Present" | 70% | 60–80% depending on your policy |

> **💡 Example:** For a 60-minute class with 70% threshold, a student must watch at least 42 minutes to be marked as "Present" automatically.

---

## 7. Class Access Tokens

### What Is This?

Access tokens are like **digital tickets** — each one gives one specific student permission to join one specific live class. Think of it like a movie ticket: the ticket has the student's name, the class name, and an expiry time. Without a valid ticket, the student cannot enter.

### How It Works — The Complete Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    TOKEN LIFECYCLE                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Admin/Teacher schedules a class                         │
│       ↓                                                     │
│  2. System checks Access Type:                              │
│       • BATCH_ONLY → generates tokens for all batch students│
│       • MULTI_BATCH → tokens for students in all batches    │
│       • ALL_STUDENTS → tokens for every enrolled student    │
│       • CUSTOM → tokens only for hand-picked students       │
│       ↓                                                     │
│  3. Each student gets a unique encrypted token              │
│       ↓                                                     │
│  4. Student clicks "Join Class" on their dashboard          │
│       ↓                                                     │
│  5. System checks:                                          │
│       ✓ Does a token exist for this student + class?        │
│       ✓ Is the token NOT expired?                           │
│       ✓ Is the token NOT revoked?                           │
│       ↓                                                     │
│  6. If all checks pass → student joins the live stream      │
│     If any check fails → "Access Denied" message            │
│       ↓                                                     │
│  7. Token is marked as "Used" with timestamp, device, IP    │
│       ↓                                                     │
│  8. After class ends → token expires automatically          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Does It Need Configuration?

**No!** Access tokens are **fully automatic**. You do not need to create, configure, or manage them. The system handles everything:

| What Happens | Who Does It | When |
|---|---|---|
| Token generation | **System (automatic)** | When a class is scheduled or students are added to a batch |
| Token distribution | **System (automatic)** | Token is embedded in the student's "Join Class" button |
| Token validation | **System (automatic)** | When student clicks "Join Class" |
| Token expiry | **System (automatic)** | 30 minutes after class end time (configurable) |
| Token revocation | **Admin (manual)** | Only when you need to block a specific student |

### Real-World Example — Step by Step Demo

**Scenario:** Teacher "Mrs. Priya Sharma" schedules a Physics class for Batch "12A Morning"

#### Step 1: Class is Scheduled
```
Class: PHY-2026-042 — Kinematics (Live Session)
Teacher: Mrs. Priya Sharma
Batch: 12A Morning (35 students)
Date: March 27, 2026
Time: 10:00 AM — 11:00 AM
Access Type: BATCH_ONLY
```

#### Step 2: System Auto-Generates 35 Tokens
The system creates one token per student in Batch 12A Morning:

| Student | Token (encrypted) | Expires At | Status |
|---|---|---|---|
| Rahul Sharma | `eyJ0eXAiOiJKV1Q...a4Bf` | Mar 27, 11:30 AM | Active |
| Anita Patel | `eyJ0eXAiOiJKV1Q...x7Kp` | Mar 27, 11:30 AM | Active |
| Vikram Singh | `eyJ0eXAiOiJKV1Q...m2Qs` | Mar 27, 11:30 AM | Active |
| ... (32 more) | ... | ... | Active |

> Notice: Tokens expire 30 minutes **after** the class ends (11:30 AM), giving students time to rejoin if disconnected.

#### Step 3: Student Opens Dashboard at 9:55 AM
Rahul opens his student dashboard and sees:
```
┌─────────────────────────────────────────────┐
│  📚 Upcoming Class                          │
│  Kinematics (Live Session)                  │
│  Mrs. Priya Sharma | 10:00 AM              │
│                                             │
│  [▶ Join Class]  ← button appears 15 min   │
│                     before start time       │
└─────────────────────────────────────────────┘
```

#### Step 4: Rahul Clicks "Join Class" at 10:02 AM
Behind the scenes:
```
✓ Token found for Rahul + PHY-2026-042
✓ Token not expired (expires 11:30 AM, current time 10:02 AM)
✓ Token not revoked
→ ACCESS GRANTED
→ Token marked: used=True, used_at=10:02:15 AM, device=Chrome/Windows, IP=192.168.1.45
→ Rahul is redirected to the YouTube live stream
```

#### Step 5: A Non-Batch Student Tries to Join
Another student "Deepak" from Batch 12B tries to access the same class:
```
✗ No token found for Deepak + PHY-2026-042
→ ACCESS DENIED: "You are not enrolled in this class."
```

#### Step 6: Admin Revokes Rahul's Token (optional)
If needed, an admin can revoke access:
```
Admin navigates to: Class Access Tokens
Searches: "Rahul Sharma"
Finds token for PHY-2026-042
Checks: ☑ Revoked
Enters reason: "Student transferred to Batch 12B"
Saves.
```
Now Rahul's token shows:
```
Revoked: ✅ Yes
Revoked Reason: "Student transferred to Batch 12B"
→ If Rahul tries to join again → "Access has been revoked."
```

### Admin View — What You See in the Panel

The **Class Access Tokens** list shows:

| Class | Student | Used | Status | Expires |
|---|---|---|---|---|
| PHY-2026-042 — Kinematics | Rahul Sharma | ✅ Yes | 🚫 Revoked | Mar 27, 11:30 AM |
| PHY-2026-042 — Kinematics | Anita Patel | ✅ Yes | ✓ Active | Mar 27, 11:30 AM |
| PHY-2026-042 — Kinematics | Vikram Singh | ❌ No | ✓ Active | Mar 27, 11:30 AM |

From this view you can instantly see:
- **Anita** joined the class ✅
- **Vikram** has access but hasn't joined yet (maybe absent?) ⏳
- **Rahul** joined but was later revoked 🚫

### Fields — Detailed

| Field | What It Is | Auto/Manual | Example |
|---|---|---|---|
| **Scheduled Class** | Which class this token is for | Auto-linked | `PHY-2026-042 — Kinematics` |
| **Student** | Which student holds this token | Auto-assigned | `Rahul Sharma (Class 12A)` |
| **Token** | The unique encrypted access code | Auto-generated | `eyJ0eXAiOiJKV1Q...` (never shown to students) |
| **Expires At** | When this token stops working | Auto-set (30 min after class end) | `2026-03-27 11:30:00` |
| **Used** | Has the student clicked "Join"? | Auto-tracked | ✅ Yes / ❌ No |
| **Used At** | Exact time student joined | Auto-tracked | `2026-03-27 10:02:15` |
| **Used Device** | Browser/OS used to join | Auto-detected | `Chrome on Windows 11` |
| **Used IP** | Network address of the student | Auto-logged | `192.168.1.45` |
| **Revoked** | Has admin blocked this student? | **Manual** — admin action | ✅ Revoked / — Active |
| **Revoked Reason** | Why was access blocked? | **Manual** — admin enters reason | `Student transferred to another batch` |

### Troubleshooting Access Issues

| Student's Problem | What to Check | How to Fix |
|---|---|---|
| "I can't see the Join button" | Is the class status **SCHEDULED** or **LIVE**? | Change status from DRAFT to SCHEDULED |
| "Access Denied" error | Does a token exist for this student + class? | Check batch assignment; add student to correct batch |
| "Token expired" error | Has the class already ended? | If class is still live, check the `expires_at` time |
| "Access revoked" error | Was the token revoked by an admin? | Uncheck "Revoked" and save |
| Student joined from wrong device | Check `used_device` and `used_ip` fields | Informational only — no action needed unless suspicious |

---

## 8. Class Watch Times

### What Is This?

Class Watch Times is the **attendance intelligence system** — it tracks exactly how each student watched each class, down to the second. It answers not just "did they watch?" but "how attentively did they watch?" and uses this data to **automatically mark attendance**.

### Does It Need Configuration?

**Mostly no.** Watch time tracking starts automatically when a student joins a live class or watches a recording. However, two settings in the **Scheduled Class** affect how watch data is used:

| Setting | Where to Set It | What It Controls | Default |
|---|---|---|---|
| **Attendance Mode** | Scheduled Class → Attendance | How attendance is calculated from watch data | Automatic |
| **Min Watch Percent** | Scheduled Class → Attendance | What % of the class counts as "Present" | 70% |
| **Grace Period (minutes)** | Scheduled Class → Attendance | How late a student can join and still be "on time" | 15 min |

### How It Works — Complete Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                 WATCH TIME TRACKING FLOW                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Student clicks "Join Class"                                  │
│       ↓                                                          │
│  2. System creates a WatchTime record:                           │
│       • joined_at = current time                                 │
│       • is_live_watch = True (live) or False (recording)         │
│       • watch_session_id = unique ID for this viewing session    │
│       ↓                                                          │
│  3. While watching, the player reports every 30 seconds:         │
│       • total_watch_seconds (incrementing counter)               │
│       • video_progress_percent (how far in the video)            │
│       • rewind/forward/pause counts                              │
│       • tab_switches (student switched to another app/tab)       │
│       • idle_periods (mouse/keyboard inactive for 2+ minutes)    │
│       ↓                                                          │
│  4. Student leaves or class ends                                 │
│       • left_at = current time                                   │
│       • engagement_score = calculated automatically              │
│       • completion_status = COMPLETED / PARTIAL / MINIMAL        │
│       ↓                                                          │
│  5. Attendance auto-calculation (if mode = Automatic):           │
│       • If total_watch_seconds >= min_watch_percent of class     │
│         → Mark PRESENT                                           │
│       • If student joined within grace period                    │
│         → Mark PRESENT (on time)                                 │
│       • If joined after grace period but watched enough          │
│         → Mark LATE                                              │
│       • If did not watch enough → Mark ABSENT                    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Real-World Example — Complete Demo

**Scenario:** 60-minute Physics class (10:00 AM — 11:00 AM), Min Watch Percent = 70%, Grace Period = 15 min

#### Student A: "Anita" — Good Student
```
Joined at:           10:01 AM (1 minute late — within grace period)
Left at:             11:00 AM (stayed till the end)
Total watch:         3,540 seconds (59 minutes)
Progress:            98.3%
Tab switches:        1 (briefly checked a message)
Idle periods:        0
Rewind count:        4 (went back to re-watch a concept — great!)
Forward count:       0 (never skipped)
Pause count:         2 (took notes)
Chat messages:       3 (asked a question, participated in discussion)
Engagement score:    92%
Completion:          ✅ COMPLETED
Attendance result:   ✅ PRESENT (on time)
```

#### Student B: "Vikram" — Distracted Student
```
Joined at:           10:05 AM (5 minutes late — within grace period)
Left at:             10:48 AM (left 12 minutes early)
Total watch:         2,580 seconds (43 minutes)
Progress:            71.7%
Tab switches:        12 (constantly switching between YouTube and other apps)
Idle periods:        5 (went AFK multiple times)
Rewind count:        0 (never went back)
Forward count:       3 (skipped ahead)
Pause count:         0
Chat messages:       0 (no participation)
Engagement score:    38%
Completion:          ✅ COMPLETED (71.7% > 70% threshold — barely passed!)
Attendance result:   ✅ PRESENT (but flagged as "low engagement")
```

#### Student C: "Deepak" — Absent Student
```
Joined at:           10:35 AM (35 minutes late — beyond grace period)
Left at:             10:52 AM (only 17 minutes)
Total watch:         1,020 seconds (17 minutes)
Progress:            28.3%
Tab switches:        8
Idle periods:        3
Engagement score:    15%
Completion:          ❌ MINIMAL (28.3% < 70% threshold)
Attendance result:   ❌ ABSENT
```

#### Student D: "Priya" — Watched Recording Later
```
Joined at:           3:00 PM (same day, watching recording)
Left at:             4:05 PM
Total watch:         3,900 seconds (65 minutes — watched full recording + rewatched parts)
Progress:            100%
is_live_watch:       ❌ No (VOD — recording)
Rewind count:        8 (studied specific sections thoroughly)
Engagement score:    85%
Completion:          ✅ COMPLETED
Attendance result:   Depends on your policy — some mark VOD as "attended", some don't
```

### Admin View — What You See

The **Class Watch Times** list shows a summary:

| Class | Student | Watch Time | Completion | Type | Engagement |
|---|---|---|---|---|---|
| PHY-2026-042 | Anita Patel | 59m 0s | ✅ Completed | ● LIVE | 92% (High) |
| PHY-2026-042 | Vikram Singh | 43m 0s | ✅ Completed | ● LIVE | 38% (Low) |
| PHY-2026-042 | Deepak Kumar | 17m 0s | ❌ Minimal | ● LIVE | 15% (Low) |
| PHY-2026-042 | Priya Verma | 1h 5m | ✅ Completed | 📼 Recording | 85% (High) |

Clicking any row opens the detailed view with timing, playback, and engagement data.

### Understanding the Engagement Score

The **engagement score** (0–100%) is calculated automatically from multiple factors:

```
Engagement Score Formula (simplified):

  Base Score = (total_watch_seconds / class_duration_seconds) × 100

  Bonuses:
    + rewind_count × 2     (rewinding = re-studying = good)
    + chat_messages × 3    (active participation)
    + questions_asked × 5  (asking questions = highly engaged)

  Penalties:
    - tab_switches × 3     (switching away = distracted)
    - idle_periods × 5     (inactive = not watching)
    - forward_count × 2    (skipping = not interested)

  Final Score = clamp(Base + Bonuses - Penalties, 0, 100)
```

| Score Range | Label | What It Means | Admin Action |
|---|---|---|---|
| **80–100%** | 🟢 High | Student was attentive and participative | None needed |
| **50–79%** | 🟡 Medium | Student watched but was somewhat distracted | Monitor over time |
| **20–49%** | 🟠 Low | Student was present but barely engaged | Flag for teacher follow-up |
| **0–19%** | 🔴 Very Low | Student opened the stream but wasn't watching | Investigate — possible "ghost watching" |

### Key Metrics — Detailed

| Metric | What It Measures | Good Value | Red Flag |
|---|---|---|---|
| **Total Watch Seconds** | Total time the student spent watching | Close to class duration | < 50% of class |
| **Video Progress Percent** | How much of the video they've seen | 70%+ for "Completed" | < 30% |
| **Rewind Count** | How many times they went back (good sign!) | Any value — shows engagement | N/A (always good) |
| **Forward Count** | How many times they skipped ahead | Low is better | > 5 (skipping most of class) |
| **Pause Count** | How many times they paused | Normal (note-taking) | > 20 (excessive) |
| **Tab Switches** | How many times they switched to another tab | 0–3 (normal) | > 10 (not watching) |
| **Idle Periods** | Times the student appeared inactive (2+ min no input) | 0–2 | > 5 (left the computer) |
| **Chat Messages Sent** | Messages in live chat | Any value (participation) | N/A |
| **Questions Asked** | Questions submitted during class | Excellent sign of engagement | N/A |
| **Engagement Score** | Overall attention score (0–100%) | 70%+ is good | < 30% |

### Completion Status

| Status | What It Means | Typical Watch Percent | Attendance Impact |
|---|---|---|---|
| **Completed** ✅ | Watched the required portion | 70%+ (or whatever your threshold is) | Usually → PRESENT |
| **Partial** ⚠️ | Watched some but not enough | 30–69% | Usually → ABSENT |
| **Minimal** ❌ | Barely watched | Less than 30% | Always → ABSENT |

### Live vs. Recording (VOD)

| Type | What It Means | When It Happens |
|---|---|---|
| **● LIVE** | Student watched the class in real-time during broadcast | During the scheduled time |
| **📼 Recording (VOD)** | Student watched the saved recording afterward | After the class has ended |

> **💡 Policy Decision:** Your institution decides whether watching a recording counts as attendance. configure this in the attendance rules — some institutions count only live watching, some accept recordings within 24 hours.

### Common Questions

**Q: A student says "I watched the whole class, why am I absent?"**
A: Check their watch time record. Look at:
1. `total_watch_seconds` — did they actually watch 70%+ of the class?
2. `tab_switches` — were they away from the tab most of the time?
3. `is_live_watch` — did they watch live or the recording? Your policy may only count live.

**Q: Can a student cheat by opening the video and walking away?**
A: Partially. The system detects `idle_periods` (no mouse/keyboard activity) and `tab_switches`. These lower the engagement score. Very low scores can be flagged automatically.

**Q: What if the student's internet disconnected and they rejoined?**
A: Each reconnection creates a new watch session. The system adds up total watch seconds across all sessions for the same class.

> **💡 Tip:** When reviewing engagement, focus on the **Engagement Score** for a quick overview. For deeper investigation, look at **Tab Switches** and **Idle Periods** — high numbers suggest the student wasn't paying attention.

---

## 9. Real-World Scenarios

### Scenario 1: Small School (200 students, 10 teachers)

**Setup:**
- 1 YouTube channel (school's official channel)
- Platform: YouTube Live (default)
- Auto Generate Link: ON
- Auto Record: ON
- Auto Admit: ON
- Attendance Mode: Automatic
- Min Watch Percent: 60%

**Workflow:**
1. Admin does one-time setup of YouTube integration
2. Teachers create scheduled classes from their dashboard
3. 15 minutes before class, links are auto-generated and shared
4. Students click the link and join
5. After class, attendance is automatically marked based on watch time
6. Recordings are available for make-up viewing

---

### Scenario 2: Large Coaching Center (5,000+ students, 50 teachers)

**Setup:**
- 3 YouTube channels (one per department: Physics, Chemistry, Maths)
- Platform: YouTube Live for lectures, Zoom for doubt sessions
- Auto Generate Link: ON
- Auto Record: ON
- Access Type: Batch Only
- Attendance Mode: Hybrid

**Workflow:**
1. Admin sets up 3 YouTube integrations (one per department)
2. Admin creates 3 Class Link Configs (one YouTube, one Zoom, one as default)
3. Teachers select the appropriate channel when creating classes
4. Batch-specific access ensures only enrolled students can join
5. Hybrid attendance: system suggests, but teachers verify edge cases
6. Admin reviews engagement scores weekly to identify struggling students

---

### Scenario 3: Online Training Platform (Corporate)

**Setup:**
- 1 YouTube channel (unlisted for privacy)
- Platform: YouTube Live + Custom URL (for internal tools)
- Auto Record: ON (mandatory for compliance)
- Access Type: Custom (per-employee)
- Attendance Mode: Automatic
- Min Watch Percent: 80% (higher threshold for compliance)

**Workflow:**
1. HR creates training sessions as Scheduled Classes
2. Custom access tokens issued to specific employees
3. Employees must watch 80% to be marked "attended"
4. Watch time records serve as compliance documentation
5. Managers review engagement scores for performance tracking

---

### Scenario 4: Tuition Center with Multiple Branches

**Setup:**
- 1 YouTube channel (centralized)
- Teacher creates class → students from all branches can watch
- Access Type: Multi-Batch (students from Branch A, B, C batches)
- Auto Admit: ON
- Auto Record: ON

**Workflow:**
1. A single teacher broadcasts to students across all branches
2. Multi-batch access ensures students from participating branches can join
3. Recordings available for branches in different time zones
4. Centralized watch time data for all branches

---

## 10. Troubleshooting & FAQ

### "Students can't see the class link"

**Check:**
1. Is the class status **SCHEDULED** (not DRAFT)?
2. Is the student in the correct **batch**?
3. Has an **access token** been generated for the student?
4. Has the class link been **auto-generated** (check auto_generate_link setting)?

---

### "YouTube live stream won't start"

**Check:**
1. Is the YouTube integration **active** (is_active = ON)?
2. Is the health status **Healthy**?
3. Has the YouTube channel been **verified**?
4. Is the daily **API quota** exceeded?
5. Are the **OAuth credentials** valid and not expired?

---

### "Attendance is wrong — students watched but marked absent"

**Check:**
1. What is the **Min Watch Percent** threshold? If set to 70%, students must watch 70% of the class.
2. Check the student's actual **watch time** in "Class watch times"
3. Did the student watch the **live** class or the **recording** (VOD)?
4. Are there many **tab switches** or **idle periods** — which might reduce the engagement score?

---

### "Daily quota exceeded" warning

**Solutions:**
1. Wait until the quota resets (usually midnight Pacific Time)
2. Reduce the **Max Requests Per Hour** in your integration config
3. Apply for a [YouTube API quota increase](https://support.google.com/youtube/contact/yt_api_form) for your Google Cloud project
4. Avoid unnecessary video syncing — set **Auto Sync Videos = OFF** if you don't need it

---

### "OAuth token expired"

**Solutions:**
1. The system should refresh tokens automatically using the **Refresh Token**
2. If auto-refresh fails, re-authorize the YouTube account:
   - Go to the integration config
   - The admin or IT team may need to re-run the OAuth authorization flow
3. If the refresh token is also invalid, you'll need to disconnect and reconnect the YouTube account

---

### "Health status shows DOWN"

**Steps to resolve:**
1. Check your internet connection
2. Verify the **API Key** is correct in the integration config
3. Confirm **YouTube Data API v3** is enabled in Google Cloud Console
4. Check [Google Status Dashboard](https://www.google.com/appsstatus) for YouTube outages
5. Try setting health_status back to "Unknown" — the system will re-check automatically

---

## 11. Glossary

| Term | Simple Explanation |
|---|---|
| **API** | Application Programming Interface — a way for two software systems to talk to each other |
| **API Key** | A password that lets your LMS access YouTube's features |
| **OAuth** | A secure way to log in to YouTube without sharing your actual password |
| **Channel ID** | YouTube's unique code for your channel (like a phone number for your channel) |
| **Playlist** | A collection of YouTube videos grouped together (like a folder) |
| **Webhook** | A way for YouTube to automatically notify your LMS when something happens |
| **Quota** | A daily limit on how many times the LMS can ask YouTube for information |
| **Rate Limit** | A per-hour limit to prevent asking YouTube too many times at once |
| **Token** | A temporary digital key that proves you have permission to do something |
| **Refresh Token** | A special token used to get a new access token when the old one expires |
| **Broadcast** | A YouTube live stream event |
| **Stream Key** | A secret code that streaming software uses to connect to YouTube |
| **VOD** | Video on Demand — a recorded video that can be watched anytime |
| **Unlisted** | A YouTube video that can only be found by someone who has the link |
| **Tenant** | Your institution/organization within the LMS (for multi-school setups) |
| **Batch** | A group of students (e.g., "Class 12A Morning Batch") |
| **Engagement Score** | A number (0–100) measuring how actively a student watched a class |

---

## 12. Tips & Best Practices

### Setup

- ✅ **Start with one platform** — get YouTube working before adding Zoom or Meet
- ✅ **Test with a small group** before rolling out to all students
- ✅ **Keep Auto Record ON** — recordings are invaluable for absent students
- ✅ **Use "Unlisted" privacy** — students can access via link but it won't appear in YouTube search
- ✅ **Set reasonable watch thresholds** — 60–70% is fair; 90% is too strict for auto-attendance

### Security

- 🔒 **Never share API keys** in emails, chats, or documents
- 🔒 **Rotate API keys** annually (create new one, update config, delete old one)
- 🔒 **Use OAuth** for live streaming instead of just an API key (more secure)
- 🔒 **Keep OAuth token fields** collapsed and don't edit them manually
- 🔒 **Monitor the health status** weekly to catch issues early

### Common Mistakes

- ❌ **Setting rate limit too high** (>500/hr) — exhausts your daily quota quickly
- ❌ **Forgetting to enable YouTube Data API v3** in Google Cloud Console
- ❌ **Using a Channel ID that doesn't start with "UC"** — it's probably incorrect
- ❌ **Setting Auto Generate Link = ON without API credentials** — links won't be created
- ❌ **Setting Min Watch Percent to 100%** — almost nobody watches 100% of a class without any pause
- ❌ **Creating multiple "Default" platforms** — only one should be marked as default
- ❌ **Leaving the API Endpoint blank** for YouTube — it should be `https://www.googleapis.com/youtube/v3`
- ❌ **Manually editing OAuth tokens** — they should be generated by the authorization flow

### Performance

- ⚡ **Reduce Auto Sync frequency** if you have many videos — it uses API quota
- ⚡ **Monitor Quota Used Today** in YouTube Channels section
- ⚡ **Set Generate Minutes Before to 15** — enough time without wasting resources
- ⚡ **Use Batch Only access** when possible — reduces token generation overhead

---

> **Need more help?** Contact your institution's IT support team or refer to the [YouTube Data API documentation](https://developers.google.com/youtube/v3/getting-started).

---

## 13. Scheduling YouTube Live Classes — Complete Setup with Demo Values

This section walks you through the **entire end-to-end process** of scheduling an automatic YouTube live class, with **real demo values** you can reference when filling in your own.

### What's Needed (Overview)

To schedule a YouTube live class that **automatically creates a stream and shares the link with students**, you need three things configured:

```
┌───────────────────────────────────────────────────────────┐
│               YOUTUBE LIVE CLASS SETUP                     │
│                                                           │
│  Step 1: YouTube Integration Config    (one-time setup)   │
│          → Connects LMS to YouTube API                    │
│                                                           │
│  Step 2: Class Link Configuration      (one-time setup)   │
│          → Tells system to auto-generate links            │
│                                                           │
│  Step 3: YouTube Channel               (one-time setup)   │
│          → Registers your channel for streaming           │
│                                                           │
│  Step 4: Scheduled Class               (per class)        │
│          → Create each class session                      │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

### Step 1: YouTube Integration Config — Demo Values

> **What is this?** This connects your LMS to the YouTube Data API so the system can create live streams, fetch video data, and manage recordings on your behalf.

Navigate to: **Admin Panel → Live Classes & YouTube → YouTube integration configs → Add**

#### Demo Values:

| Field | Demo Value | Explanation | Importance |
|---|---|---|---|
| **Name** | `Bright Academy Main Channel` | A friendly name so you can identify this integration | **Required** — you'll reference this name in reports |
| **Enabled** | ☑ `Checked (Active)` | Turns the integration ON | **Required** — if OFF, no YouTube features work |
| **Description** | `Main YouTube channel for all live classes — Class 11 & 12` | Notes for your team | Optional but helpful |
| **Channel ID** | `UCa1B2c3D4e5F6g7H8i9J0kL` | Your YouTube channel's unique ID (always starts with "UC") | **Critical** — wrong ID = nothing works |
| **Channel Name** | `Bright Academy Live Classes` | Display name students see | Recommended |
| **Playlist IDs** | `PLx1y2z3A4B5C6D7E8F9G0` | Playlist where recordings are saved | Optional — for organizing recordings |
| **Auto Sync Videos** | ☐ `Unchecked (Off)` | Whether to auto-import YouTube videos | Optional — turn ON only if you need it |
| **API Key** | `AIzaSyD-DEMO-xQ4r7s8T9u0V1w2X3y4Z5a6B7c` | Your YouTube API key from Google Cloud Console | **Required** — without this, LMS can't talk to YouTube |

##### OAuth Credentials (expand the collapsed section):

| Field | Demo Value | Explanation | Importance |
|---|---|---|---|
| **OAuth Client ID** | `987654321-abcdefg.apps.googleusercontent.com` | Identifies your app to Google | **Required for live streaming** — without this, you can only read data, not create streams |
| **OAuth Client Secret** | `GOCSPX-DeMoSeCrEtKeY123456` | The private key for your OAuth app | **Required for live streaming** — paired with Client ID |

> **⚠️ OAuth Token and Refresh Token are auto-generated.** You do NOT fill these in manually. They are created when the system completes the OAuth authorization flow with Google.

| Field | Demo Value | How It Gets Set |
|---|---|---|
| **OAuth Token** | `ya29.a0ARrdaM_DEMO_TOKEN...` | **Auto-generated** during OAuth authorization |
| **OAuth Refresh Token** | `1//0eDemo-REFRESH-TOKEN...` | **Auto-generated** — used to renew the access token |
| **OAuth Token Expiry** | `2026-03-27 11:45:00 UTC` | **Auto-set** — tokens expire in ~1 hour, then auto-refresh |

##### Rate Limits (expand the collapsed section):

| Field | Demo Value (Dropdown) | Why This Value |
|---|---|---|
| **API Rate Limit** | `✅ Standard (100/hr)` | Works for most institutions with < 500 students |
| **Per-User Rate Limit** | `20/hr — Standard` | Prevents any single teacher from consuming all quota |

#### What If You Skip This Step?
- ❌ No YouTube features will work at all
- ❌ Teachers cannot create live streams
- ❌ No auto-generated class links
- ❌ No recording import

#### What If the API Key Is Wrong?
- ❌ Health status will show **DOWN** 🔴
- ❌ All API calls will fail with "Invalid API Key"
- ✅ Fix: Replace with the correct key and save

#### What If OAuth Credentials Are Wrong?
- ❌ Can still **read** YouTube data (API Key works for reading)
- ❌ Cannot **create** live streams or upload recordings
- ❌ Authorization will fail with "Authentication error"
- ✅ Fix: Verify Client ID and Secret match Google Cloud Console

---

### Step 2: Class Link Configuration — Demo Values

> **What is this?** This tells the system HOW to create class links — which platform, when to generate them, and default settings.

Navigate to: **Admin Panel → Live Classes & YouTube → Class link configurations → Add**

#### Demo Values:

| Field | Demo Value | Explanation | Importance |
|---|---|---|---|
| **Platform** | `YouTube Live` (dropdown) | Which video platform to use | **Required** — determines which API to call |
| **Active** | ☑ `Checked` | Enable this platform | **Required** — if OFF, teachers can't use YouTube |
| **Default** | ☑ `Checked` | Pre-selected when teachers create a class | Recommended — saves teachers a click |
| **Auto Generate Link** | ☑ `Checked` | System creates YouTube stream automatically | **Key feature** — this is what makes scheduling automatic |
| **Create Link** | `15 minutes before` (dropdown) | When to generate the stream URL | Recommended: 15 min gives time for sharing |
| **Default Class Duration** | `60 minutes` (dropdown) | Standard class length | Used to set stream duration on YouTube |
| **Auto Record** | ☑ `Checked` | Record classes automatically | **Highly recommended** — students can rewatch |
| **Auto Admit Participants** | ☑ `Checked` | Students join without approval | Recommended for large classes |

#### What If Auto Generate Link Is OFF?
- Teachers must manually create a YouTube live stream in YouTube Studio
- Teachers must copy-paste the stream URL into the Scheduled Class
- Students still get the link, but the process is manual and slower

#### What If Default Duration Is Wrong?
- YouTube may end the stream early or keep the "live" placeholder running after class ends
- Teachers can always override per-class, so this is just the default

---

### Step 3: YouTube Channel — Demo Values

> **What is this?** This registers your YouTube channel in the system and manages its credentials and quota separately from the integration config.

Navigate to: **Admin Panel → Live Classes & YouTube → YouTube channels → Add**

#### Demo Values:

| Field | Demo Value | Explanation |
|---|---|---|
| **Channel ID** | `UCa1B2c3D4e5F6g7H8i9J0kL` | Same as in Integration Config — this links them |
| **Channel Name** | `Bright Academy Live Classes` | Name shown in the teacher's channel dropdown |
| **Channel URL** | `https://www.youtube.com/channel/UCa1B2c3D4e5F6g7H8i9J0kL` | Full URL to the channel page |
| **Status** | `Active` | Channel is ready to use |
| **Primary Channel** | ☑ `Checked` | This is the main channel (auto-selected for new classes) |
| **Assigned Teacher** | `Mrs. Priya Sharma` | Optional — who manages this channel |
| **Daily Quota Limit** | `10000` | YouTube's default free tier |

##### OAuth Credentials (collapsed):

| Field | Demo Value | Note |
|---|---|---|
| **Client ID** | `987654321-abcdefg.apps.googleusercontent.com` | Same as Integration Config |
| **Client Secret** | `GOCSPX-DeMoSeCrEtKeY123456` | Same as Integration Config |
| **Access Token** | `ya29.a0ARrdaM_DEMO_TOKEN...` | Auto-generated |
| **Refresh Token** | `1//0eDemo-REFRESH-TOKEN...` | Auto-generated |
| **Token Expires At** | `2026-03-27 11:45:00` | Auto-managed (refreshes before expiry) |

> **💡 Why does the channel also have OAuth credentials?** The Integration Config holds credentials for the *system-level* YouTube API connection. The Channel holds credentials for *channel-specific* operations. If you have only one channel, they'll be the same values. If you have multiple channels (e.g., Physics dept and Chemistry dept), each channel has its own OAuth.

#### What If Status Is "Revoked"?
- YouTube or Google revoked the OAuth access
- The system cannot create live streams on this channel
- Fix: Re-authorize the channel through the OAuth flow, or create new credentials in Google Cloud Console

#### What If Quota Is Exceeded?
- Daily quota (10,000 units) is used up
- No new streams can be created until quota resets (midnight Pacific Time)
- Existing live streams continue to work — only API calls are blocked
- Fix: Wait for reset, or apply for a quota increase from Google

---

### Step 4: Schedule a Live Class — Demo Values

> **What is this?** This is where you (or a teacher) create an actual live class session for students.

Navigate to: **Admin Panel → Live Classes & YouTube → Scheduled classes → Add**

#### Demo Values:

##### Class Details:

| Field | Demo Value | Explanation |
|---|---|---|
| **Class Code** | `PHY-2026-042` | Unique identifier (auto-generated or manual) |
| **Title** | `Kinematics — Equations of Motion (Live Session)` | What students see — make it descriptive! |
| **Description** | `Covering Newton's equations of motion, free fall, and projectile basics. Bring your formula sheet.` | Brief summary |
| **Teacher** | `Mrs. Priya Sharma` | Select from registered teachers |
| **Batch** | `12A — Morning Batch` | Which student group |

##### Schedule:

| Field | Demo Value | Format |
|---|---|---|
| **Scheduled Date** | `2026-03-28` | YYYY-MM-DD |
| **Start Time** | `10:00` | 24-hour format |
| **End Time** | `11:00` | 24-hour format |
| **Duration** | `60` | Auto-calculated from start/end |

##### YouTube Streaming (only 2 fields to fill!):

| Field | Demo Value | Explanation |
|---|---|---|
| **YouTube Channel** | `Bright Academy Live Classes` (dropdown) | Select from registered channels |
| **Privacy Status** | `Unlisted` (dropdown) | Students access via link only — not searchable on YouTube |

> **That's it!** All other streaming fields (broadcast ID, stream key, watch URL, etc.) are **auto-generated** by the system 15 minutes before the class.

##### Access Control:

| Field | Demo Value | Explanation |
|---|---|---|
| **Access Type** | `Batch Only` | Only Batch "12A Morning" students can join |

##### Attendance:

| Field | Demo Value (Dropdown) | Explanation |
|---|---|---|
| **Attendance Mode** | `Automatic` | System marks attendance from watch time |
| **Minimum Watch %** | `70% — Standard (recommended)` | Must watch 42+ minutes of a 60-min class |
| **Grace Period** | `15 minutes (recommended)` | Students can join up to 15 min late |

##### Status:

| Field | Demo Value | Explanation |
|---|---|---|
| **Status** | `Scheduled` | Class is confirmed and visible to students |

---

### What Happens After You Click "Save" — The Automation Timeline

```
📅 March 28, 2026 — Timeline of Events

 9:45 AM  → System generates YouTube live stream automatically
            • Creates broadcast on YouTube via API
            • Gets stream key, watch URL, embed URL
            • Fills in auto-generated fields in Scheduled Class
            • Generates access tokens for all 35 students in Batch 12A

 9:45 AM  → Students receive notification:
            "Your class 'Kinematics — Equations of Motion' starts at 10:00 AM"
            [Join Class] button appears on student dashboard

 9:55 AM  → Stream is ready on YouTube (standby mode)
            Teacher opens YouTube Studio or OBS to start broadcasting

10:00 AM  → Class status changes: SCHEDULED → LIVE
            Teacher starts the broadcast
            Students click "Join Class" → redirected to YouTube stream
            Watch time tracking begins for each student

10:00 AM–11:00 AM → System tracks:
            • Who joined and when
            • Watch duration per student
            • Engagement metrics (tab switches, idle periods, chat)
            • Real-time viewer count (peak viewers)

11:00 AM  → Teacher ends the broadcast
            Class status changes: LIVE → COMPLETED
            Recording is automatically saved to YouTube

11:01 AM  → System runs attendance calculation:
            • Checks each student's total watch time
            • Compares against 70% threshold (42 minutes)
            • Marks each student as PRESENT, LATE, or ABSENT
            • Sends attendance report to teacher

11:30 AM  → Access tokens expire
            Students can still watch the recording (new VOD watch session)
```

---

### Quick Reference — All Parameters at a Glance

| Parameter | Demo Value | Where to Set | One-Time or Per-Class? |
|---|---|---|---|
| Integration Name | `Bright Academy Main Channel` | YouTube Integration Config | One-time |
| Channel ID | `UCa1B2c3D4e5F6g7H8i9J0kL` | YouTube Integration Config + YouTube Channel | One-time |
| Channel Name | `Bright Academy Live Classes` | YouTube Integration Config + YouTube Channel | One-time |
| Channel URL | `https://www.youtube.com/channel/UCa1B2c3D4e5F6g7H8i9J0kL` | YouTube Channel | One-time |
| API Key | `AIzaSyD-DEMO-xQ4r7s8T9u0V1w2X3y4Z5a6B7c` | YouTube Integration Config | One-time |
| OAuth Client ID | `987654321-abcdefg.apps.googleusercontent.com` | Integration Config + YouTube Channel | One-time |
| OAuth Client Secret | `GOCSPX-DeMoSeCrEtKeY123456` | Integration Config + YouTube Channel | One-time |
| OAuth Token | `ya29.a0ARrdaM_DEMO_TOKEN...` | Auto-generated | Auto |
| OAuth Refresh Token | `1//0eDemo-REFRESH-TOKEN...` | Auto-generated | Auto |
| Token Expiry | `2026-03-27 11:45:00 UTC` | Auto-managed | Auto |
| Rate Limit | `100/hr (Standard)` | YouTube Integration Config | One-time |
| Platform | `YouTube Live` | Class Link Config | One-time |
| Auto Generate Link | `ON` | Class Link Config | One-time |
| Create Link Timing | `15 minutes before` | Class Link Config | One-time |
| Duration Default | `60 minutes` | Class Link Config | One-time |
| Auto Record | `ON` | Class Link Config | One-time |
| Class Code | `PHY-2026-042` | Scheduled Class | Per class |
| Title | `Kinematics — Equations of Motion` | Scheduled Class | Per class |
| Teacher | `Mrs. Priya Sharma` | Scheduled Class | Per class |
| Batch | `12A — Morning Batch` | Scheduled Class | Per class |
| Date/Time | `2026-03-28 10:00–11:00` | Scheduled Class | Per class |
| YouTube Channel | `Bright Academy Live Classes` | Scheduled Class (dropdown) | Per class |
| Privacy | `Unlisted` | Scheduled Class (dropdown) | Per class |
| Access Type | `Batch Only` | Scheduled Class | Per class |
| Attendance Mode | `Automatic` | Scheduled Class (dropdown) | Per class |
| Min Watch % | `70%` | Scheduled Class (dropdown) | Per class |
| Grace Period | `15 minutes` | Scheduled Class (dropdown) | Per class |

---

### Where to Get Each Credential — Summary

| Credential | Where to Get It | Direct Link |
|---|---|---|
| **Channel ID** | YouTube Studio → Settings → Channel → Advanced Settings | [studio.youtube.com](https://studio.youtube.com) |
| **API Key** | Google Cloud Console → APIs & Services → Credentials → + Create Credentials → API Key | [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials) |
| **OAuth Client ID** | Google Cloud Console → Credentials → + Create Credentials → OAuth 2.0 Client ID | [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials) |
| **OAuth Client Secret** | Shown when you create the OAuth Client ID (save it immediately!) | Same page as Client ID |
| **Enable YouTube API** | Google Cloud Console → APIs & Services → Library → search "YouTube Data API v3" → Enable | [console.cloud.google.com/apis/library](https://console.cloud.google.com/apis/library) |

> **⚠️ Important:** You must enable **YouTube Data API v3** in Google Cloud Console before any YouTube feature works. Without it, the API key is useless.

---

### Pre-Flight Checklist — Before Your First Live Class

- [ ] **YouTube Data API v3** is enabled in Google Cloud Console
- [ ] **API Key** is created and pasted into YouTube Integration Config
- [ ] **OAuth Client ID + Secret** are created (for auto stream creation)
- [ ] **Channel ID** starts with "UC" and matches your YouTube channel
- [ ] **YouTube Integration Config** is marked **Active** ✅
- [ ] **Class Link Config** has platform = YouTube Live, Auto Generate = ON
- [ ] **YouTube Channel** is registered with status = Active
- [ ] **Test class** is created and set to SCHEDULED status
- [ ] Teacher has access to YouTube Studio or OBS for broadcasting
- [ ] At least one student is in the assigned batch to verify access
- [ ] Health status shows **Healthy** 💚 (if not, check credentials)

---

### What If Something Goes Wrong?

| Problem | Likely Cause | Fix |
|---|---|---|
| Health status is 🔴 DOWN | API Key is wrong or YouTube API not enabled | Verify API Key; enable YouTube Data API v3 |
| "Authentication error" on stream creation | OAuth Client ID/Secret are wrong | Re-check credentials in Google Cloud Console |
| Stream created but students can't join | Access tokens not generated (class is DRAFT not SCHEDULED) | Change status to SCHEDULED |
| No watch URL appeared in class details | Auto Generate Link is OFF, or generation failed | Check Class Link Config; check API quota |
| Quota exceeded warning | Used > 10,000 API units today | Wait until midnight Pacific, or request quota increase |
| Token expired errors | OAuth token expired and refresh failed | Re-run OAuth authorization flow |
| Students see "Access Denied" | Student not in the assigned batch | Add student to correct batch; check access type |
| Recording not available after class | Auto Record is OFF | Enable Auto Record in Class Link Config |
| Class still shows LIVE after teacher stopped | Webhook not configured, system hasn't polled yet | Wait 2–5 minutes; or set status to COMPLETED manually |
