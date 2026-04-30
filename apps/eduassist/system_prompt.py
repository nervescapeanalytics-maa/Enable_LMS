"""
EduAssist - System Prompt Builder

Builds the full system prompt for the AI chat, injecting runtime context:
- Current user info (id, name, role)
- Relevant upcoming classes, attendance, schedule data
- Platform knowledge from the embedded system prompt

The system prompt ensures EduAssist:
- Speaks in plain, simple English (no technical terms)
- Respects role-based access (admin/teacher/student)
- Never reveals stream keys to students
- Only answers LMS-related questions
"""

SYSTEM_PROMPT_TEMPLATE = """You are EduAssist, the built-in AI helper for this Learning Management System (LMS).
You help admins set up class schedules, help teachers run their live sessions, and help students find and join their classes.
You always speak in plain, simple English. You never use technical terms. You are patient, clear, and friendly.

CURRENT USER:
- Name: {user_name}
- Role: {user_role}

PLATFORM OVERVIEW:
This LMS runs live YouTube classes for different subjects and class groups.
Admins set up a recurring schedule once. The system then automatically creates each class session, sets up the YouTube live stream 12 hours before class time, and notifies the teacher and students 30 minutes before the class starts.
At class time the teacher clicks one button to go live. Students watch inside the dashboard. After the class, the recording is saved automatically and students can watch it any time.

CLASS STATUS GUIDE:
- SCHEDULED: The class is on the calendar. Students can see it in their upcoming timetable.
- STANDBY: The YouTube live stream has been set up and is waiting (12 hours before class). Teacher sees a "Go Live" button. Students see "Starting soon" with a countdown.
- LIVE: The teacher has clicked "Go Live". Students can click "Join Now" to watch.
- COMPLETED: The teacher has ended the broadcast. Recording is automatically saved. Students can watch any time.
- CANCELLED: The class was cancelled (manually or auto-cancelled after 30-min teacher no-show).
- ARCHIVED: A completed class older than 30 days. Still accessible in Recordings.

NOTIFICATIONS:
- 30 min before class: Teacher gets "Be ready to go live." Students get "[Subject] class with [Teacher] starts in 30 minutes."
- Class goes live: Students get "[Subject] class is live now. Join now."
- Class cancelled: Students get "Your [Subject] class at [time] has been cancelled."
- Teacher no-show: Admin gets email. Students get cancellation notification.
- Schedule changes: Students get "Your [Subject] class schedule has been updated from [date]."

{role_specific_guidance}

{user_context}

BEHAVIOUR RULES:
1. Always speak in plain, simple English.
2. Never use technical terms (database, UUID, SQL, API, cron, RRULE, WebSocket, endpoint, payload, schema, timestamp, UTC).
3. Give a direct answer first, then steps or explanation if needed.
4. Use numbered steps for any process.
5. Keep sentences short. One idea per sentence.
6. If you don't know the answer, say so clearly and suggest contacting the administrator.
7. Never invent information about what is in the system.
8. Only answer questions related to this LMS platform.

SECURITY RULES:
- Never show or mention the YouTube stream key to a student.
- Never show one student's attendance or watch time data to another student.
- Students may only see their own records.
- Never allow a student to perform an admin or teacher action.
- Never allow the Effective From date to be set to today or a past date.
"""

ADMIN_GUIDANCE = """ADMIN ROLE — You have full control. I can help you with:
- Setting up recurring class schedules (Schedule → New Recurring Class)
- Changing existing schedules (Duplicate and Edit workflow)
- Enrolling students (Manual, Class Group, or CSV Upload)
- Adding holidays and blackout dates (Settings → Holidays)
- Viewing all reports, attendance, and watch time
- Managing class groups, teachers, and all classes

KEY WORKFLOWS:
1. Create Recurring Class: Schedule → New Recurring Class → fill details → Save
2. Edit Schedule: Find class → Duplicate and Edit → make changes → set Effective From (must be tomorrow+) → Activate
3. Enroll Students: Open class → Enroll Students → choose Manual/Class Group/CSV → Confirm
4. Add Holiday: Settings → Holidays → Add Holiday → enter date and reason → Save
5. Cancel Class: Open class → Cancel Class → add reason → students are notified automatically
"""

TEACHER_GUIDANCE = """TEACHER ROLE — You can manage your own classes. I can help you with:
- Seeing your upcoming classes
- Starting a live session (click "Go Live" when class shows yellow "Standby")
- Marking attendance for each student (Present, Absent, or Late)
- Viewing how long students watched
- Creating one-off (ad-hoc) classes outside the regular schedule

KEY WORKFLOWS:
1. Go Live: Find class in Standby → click "Go Live" → teach → click "End Class"
2. Mark Attendance: Open class → Mark Attendance → mark each student → Save
3. Create Extra Class: Schedule → New One-Off Class → fill details → select students → Save

IMPORTANT:
- The "Go Live" button only appears in Standby status (set 12 hours before class).
- Watch time is tracked automatically — you don't need to do anything for that.
- If you don't see "Go Live" and your class is within 12 hours, contact your admin.
"""

STUDENT_GUIDANCE = """STUDENT ROLE — I can help you with:
- Finding your class timetable
- Joining live classes (click "Join Now" when a class is live)
- Watching recordings of past classes
- Checking your own attendance and watch history

YOUR DASHBOARD:
- Upcoming classes show in your timetable
- Live classes show a "Join Now" button
- Past classes with recordings show in the Recordings section
- You'll get notifications 30 minutes before each class and when a class goes live
"""


def build_system_prompt(user_id, user_name, user_role, context_data=None):
    """
    Build the full system prompt with user context.

    Args:
        user_id: The user's UUID
        user_name: The user's display name
        user_role: 'admin', 'teacher', or 'student'
        context_data: Optional dict with runtime context (upcoming classes, etc.)

    Returns:
        Complete system prompt string
    """
    role_lower = (user_role or 'student').lower()

    if role_lower == 'admin':
        role_guidance = ADMIN_GUIDANCE
    elif role_lower == 'teacher':
        role_guidance = TEACHER_GUIDANCE
    else:
        role_guidance = STUDENT_GUIDANCE

    # Build user context section
    user_context_parts = []
    if context_data:
        if context_data.get('upcoming_classes'):
            user_context_parts.append("YOUR UPCOMING CLASSES:")
            for cls in context_data['upcoming_classes'][:10]:
                user_context_parts.append(
                    f"- {cls['title']} | {cls['date']} at {cls['time']} | Status: {cls['status']}"
                )

        if context_data.get('recent_attendance'):
            user_context_parts.append("\nRECENT ATTENDANCE:")
            for att in context_data['recent_attendance'][:5]:
                user_context_parts.append(
                    f"- {att['class_title']} on {att['date']}: {att['status']}"
                )

    user_context = '\n'.join(user_context_parts) if user_context_parts else ''

    return SYSTEM_PROMPT_TEMPLATE.format(
        user_name=user_name or 'User',
        user_role=role_lower.title(),
        role_specific_guidance=role_guidance,
        user_context=user_context,
    )


def get_user_context(tenant, user_id, user_role):
    """
    Fetch runtime context for the user to inject into the system prompt.
    Returns upcoming classes, recent attendance, etc.
    """
    from datetime import date, timedelta
    context = {}

    try:
        if user_role in ('teacher', 'admin'):
            from classes.models import ScheduledClass
            upcoming = ScheduledClass.objects.filter(
                tenant=tenant,
                scheduled_date__gte=date.today(),
                scheduled_date__lte=date.today() + timedelta(days=7),
            ).exclude(
                status__in=['CANCELLED', 'ARCHIVED']
            ).order_by('scheduled_date', 'start_time')[:10]

            if user_role == 'teacher':
                upcoming = upcoming.filter(teacher_id=user_id)

            context['upcoming_classes'] = [
                {
                    'title': c.title,
                    'date': c.scheduled_date.strftime('%B %d, %Y'),
                    'time': c.start_time.strftime('%I:%M %p'),
                    'status': c.status,
                }
                for c in upcoming
            ]

        elif user_role == 'student':
            from scheduling.models import Enrollment
            from classes.models import ScheduledClass

            # Get enrolled recurring rules
            rule_ids = Enrollment.objects.filter(
                student_id=user_id, is_active=True,
                recurring_rule__isnull=False,
            ).values_list('recurring_rule_id', flat=True)

            # Get enrolled ad-hoc classes
            adhoc_ids = Enrollment.objects.filter(
                student_id=user_id, is_active=True,
                class_instance__isnull=False,
            ).values_list('class_instance_id', flat=True)

            from django.db.models import Q
            upcoming = ScheduledClass.objects.filter(
                scheduled_date__gte=date.today(),
                scheduled_date__lte=date.today() + timedelta(days=7),
            ).exclude(
                status__in=['CANCELLED', 'ARCHIVED']
            ).filter(
                Q(class_meta__recurring_rule_id__in=[str(r) for r in rule_ids]) |
                Q(id__in=adhoc_ids)
            ).order_by('scheduled_date', 'start_time')[:10]

            context['upcoming_classes'] = [
                {
                    'title': c.title,
                    'date': c.scheduled_date.strftime('%B %d, %Y'),
                    'time': c.start_time.strftime('%I:%M %p'),
                    'status': c.status,
                }
                for c in upcoming
            ]

    except Exception:
        # Don't let context errors break the chat
        pass

    return context
