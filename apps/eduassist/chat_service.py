"""
EduAssist - Chat Service

Handles the AI chat logic:
1. Receives user message
2. Builds system prompt with user context
3. Constructs conversation history
4. Generates response (using configured AI provider or rule-based fallback)
5. Saves messages to database
"""
import logging
import re
from django.conf import settings

from .models import ChatConversation, ChatMessage
from .system_prompt import build_system_prompt, get_user_context

logger = logging.getLogger('lms')


# ---------------------------------------------------------------------------
# FAQ Knowledge Base (rule-based fallback when no AI provider configured)
# ---------------------------------------------------------------------------
FAQ_PATTERNS = [
    {
        'patterns': [r'go\s*live', r'go-live', r'start.*live', r'begin.*class', r'start.*broadcast'],
        'role': ['teacher', 'admin'],
        'response': (
            "To start your live class:\n\n"
            "1. Log into your teacher dashboard at class time.\n"
            "2. Find the class showing the yellow 'Standby' status.\n"
            "3. Click 'Go Live'. The class starts broadcasting immediately.\n"
            "4. Students will receive a notification and can join from their dashboard.\n"
            "5. When you are done, click 'End Class'.\n"
            "6. The recording is automatically saved.\n\n"
            "**Important:** The 'Go Live' button only appears when the class is in Standby status. "
            "Standby is set automatically 12 hours before class time."
        ),
    },
    {
        'patterns': [r'can.?t\s*see\s*go\s*live', r'no\s*go\s*live', r'where.*go\s*live', r'go\s*live.*button'],
        'role': ['teacher'],
        'response': (
            "The 'Go Live' button only appears when your class is in **Standby** status.\n\n"
            "Standby is set automatically 12 hours before your class time.\n\n"
            "- If your class is still more than 12 hours away, please wait — it will appear.\n"
            "- If it is past the 12-hour mark and you still do not see it, please contact your admin."
        ),
    },
    {
        'patterns': [r'change.*time', r'change.*day', r'change.*schedule', r'edit.*schedule', r'modify.*schedule'],
        'role': ['admin', 'teacher'],
        'response': (
            "You cannot edit a running schedule directly. Here's how to change it:\n\n"
            "1. Find the recurring class in the Schedule list.\n"
            "2. Click 'Duplicate and Edit'.\n"
            "3. Make your changes (time, days, teacher, etc.).\n"
            "4. Set the 'Effective From' date — this **must be tomorrow or later**, never today.\n"
            "5. Click 'Activate'.\n\n"
            "The old schedule stops the day before your effective date. "
            "All enrolled students are automatically transferred to the new schedule. "
            "Would you like me to walk you through it step by step?"
        ),
    },
    {
        'patterns': [r'enroll', r'add\s*student', r'register.*class'],
        'role': ['admin'],
        'response': (
            "There are three ways to enroll students:\n\n"
            "1. **Manual** — Search for students by name or email and add them one at a time.\n"
            "2. **Class Group** — Pick a group (e.g. 'Class 12A') and all students are enrolled at once.\n"
            "3. **CSV Upload** — Upload a spreadsheet with student email addresses.\n\n"
            "Steps:\n"
            "1. Open the recurring class or one-off session.\n"
            "2. Click 'Enroll Students'.\n"
            "3. Choose Manual, Class Group, or CSV Upload.\n"
            "4. Confirm. Students immediately see the class in their dashboard.\n\n"
            "If a student is already enrolled, adding them again does nothing — the system prevents duplicates automatically."
        ),
    },
    {
        'patterns': [r'mark.*attendance', r'take.*attendance'],
        'role': ['teacher'],
        'response': (
            "To mark attendance:\n\n"
            "1. During or after class, open the class in your dashboard.\n"
            "2. Click 'Mark Attendance'.\n"
            "3. You will see the full list of enrolled students.\n"
            "4. Mark each student as Present, Absent, or Late.\n"
            "5. Click Save.\n\n"
            "**Note:** Watch time (how long students actually watched) is tracked automatically "
            "by the system. Attendance is what you mark manually here."
        ),
    },
    {
        'patterns': [r'watch\s*time', r'how\s*long.*watch', r'viewing.*time'],
        'role': ['teacher', 'admin'],
        'response': (
            "Yes! Go to the completed class and open the **Attendance and Watch Time** report.\n\n"
            "You will see:\n"
            "- Each student's name\n"
            "- Whether you marked them present or absent\n"
            "- How many minutes they actually watched the live stream\n\n"
            "Watch time is tracked automatically by the system every 30 seconds."
        ),
    },
    {
        'patterns': [r'recording', r'past\s*class', r'watch.*again', r'replay'],
        'role': ['student', 'teacher', 'admin'],
        'response': (
            "To find recordings of past classes:\n\n"
            "Go to your dashboard and scroll to **Recent Recordings**. "
            "Click 'Watch' next to the class you want.\n\n"
            "Recordings are saved automatically after each class ends. "
            "You can also see how much of the recording you have already watched."
        ),
    },
    {
        'patterns': [r'cancel.*class', r'cancel.*session'],
        'role': ['admin', 'teacher'],
        'response': (
            "To cancel a class:\n\n"
            "1. Open the class from the Schedule page.\n"
            "2. Click 'Cancel Class'.\n"
            "3. Add a reason.\n"
            "4. Enrolled students will receive a notification immediately.\n\n"
            "If the class already has a YouTube stream set up, it will be removed automatically."
        ),
    },
    {
        'patterns': [r'holiday', r'blackout', r'closure', r'skip.*class'],
        'role': ['admin'],
        'response': (
            "To add a holiday or closure day:\n\n"
            "1. Go to **Settings → Holidays and Blackout Dates**.\n"
            "2. Click 'Add Holiday'.\n"
            "3. Enter the date and a reason (e.g. 'Diwali Holiday').\n"
            "4. Save.\n\n"
            "Any recurring class falling on this date will be automatically skipped.\n\n"
            "**Important:** Add the holiday before midnight. If a class was already created "
            "for that date, you will need to cancel it manually from the Schedule page."
        ),
    },
    {
        'patterns': [r'attendance.*vs.*watch', r'difference.*attendance.*watch', r'watch.*vs.*attend'],
        'role': ['student', 'teacher', 'admin'],
        'response': (
            "**Attendance** is what the teacher marks manually — Present, Absent, or Late.\n\n"
            "**Watch time** is tracked automatically by the system and shows exactly how many "
            "minutes each student had the live class open on their screen.\n\n"
            "Both are visible on the class report."
        ),
    },
    {
        'patterns': [r'student.*can.?t\s*see', r'student.*not\s*see', r'student.*missing'],
        'role': ['admin', 'teacher'],
        'response': (
            "The student is most likely not enrolled.\n\n"
            "To fix this:\n"
            "1. Go to the class schedule.\n"
            "2. Click 'Enroll Students'.\n"
            "3. Search for the student and add them.\n\n"
            "They will see the class immediately after you save."
        ),
    },
    {
        'patterns': [r'create.*extra', r'one.?off', r'ad.?hoc', r'makeup.*class', r'doubt.*class'],
        'role': ['teacher', 'admin'],
        'response': (
            "To create a one-off (extra) class:\n\n"
            "1. Go to **Schedule → New One-Off Class**.\n"
            "2. Fill in: subject, teacher, title, date, time, and duration.\n"
            "3. Select which students to invite.\n"
            "4. Click Save.\n\n"
            "If the class is within 12 hours, it goes to Standby right away. "
            "Teacher and students are notified immediately."
        ),
    },
    {
        'patterns': [r'my\s*schedule', r'my\s*timetable', r'upcoming.*class', r'next.*class'],
        'role': ['student'],
        'response': (
            "You can see your class timetable on your **Dashboard** page.\n\n"
            "Your upcoming classes are listed with the date, time, subject, and teacher.\n"
            "- **Scheduled** classes are on the calendar but not yet ready.\n"
            "- **Starting soon** means the class is in Standby — it will start shortly.\n"
            "- **Live** means the class is happening right now — click 'Join Now'!\n\n"
            "You'll also get a notification 30 minutes before each class."
        ),
    },
    {
        'patterns': [r'join.*class', r'watch.*live', r'how.*join'],
        'role': ['student'],
        'response': (
            "To join a live class:\n\n"
            "1. Go to your dashboard.\n"
            "2. Look for a class showing 'Live' status.\n"
            "3. Click 'Join Now'.\n"
            "4. The class will play right inside your dashboard.\n\n"
            "You'll also receive a notification when the class goes live."
        ),
    },
    {
        'patterns': [r'teacher.*no.?show', r'teacher.*absent', r'teacher.*didn.?t.*come'],
        'role': ['admin'],
        'response': (
            "When a teacher doesn't show up:\n\n"
            "1. The system waits 30 minutes after the scheduled time.\n"
            "2. If the teacher hasn't gone live, the class is automatically cancelled.\n"
            "3. The reason is recorded as 'Teacher no-show'.\n"
            "4. Students receive a notification that the class is cancelled.\n"
            "5. You (admin) receive an email with the class name, time, and teacher name.\n\n"
            "No manual action is needed — the system handles it automatically."
        ),
    },
]


def _match_faq(message, user_role):
    """Try to match the message against known FAQ patterns."""
    message_lower = message.lower()
    for faq in FAQ_PATTERNS:
        if user_role not in faq['role']:
            continue
        for pattern in faq['patterns']:
            if re.search(pattern, message_lower):
                return faq['response']
    return None


def _generate_ai_response(system_prompt, conversation_history, user_message):
    """
    Generate AI response using configured provider.
    Falls back to FAQ pattern matching if no AI provider is configured.

    In production, this would call OpenAI, Anthropic, or another LLM API.
    Configure via EDUASSIST_AI_PROVIDER in settings.
    """
    ai_provider = getattr(settings, 'EDUASSIST_AI_PROVIDER', None)

    if ai_provider == 'openai':
        return _call_openai(system_prompt, conversation_history, user_message)
    elif ai_provider == 'anthropic':
        return _call_anthropic(system_prompt, conversation_history, user_message)
    else:
        # No AI provider configured — use FAQ fallback
        return None


def _call_openai(system_prompt, conversation_history, user_message):
    """Call OpenAI API (requires openai package and OPENAI_API_KEY setting)."""
    try:
        import openai
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        messages = [{'role': 'system', 'content': system_prompt}]
        for msg in conversation_history:
            messages.append({'role': msg['role'], 'content': msg['content']})
        messages.append({'role': 'user', 'content': user_message})

        response = client.chat.completions.create(
            model=getattr(settings, 'EDUASSIST_MODEL', 'gpt-4o-mini'),
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return None


def _call_anthropic(system_prompt, conversation_history, user_message):
    """Call Anthropic API (requires anthropic package and ANTHROPIC_API_KEY setting)."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        messages = []
        for msg in conversation_history:
            messages.append({'role': msg['role'], 'content': msg['content']})
        messages.append({'role': 'user', 'content': user_message})

        response = client.messages.create(
            model=getattr(settings, 'EDUASSIST_MODEL', 'claude-sonnet-4-20250514'),
            system=system_prompt,
            messages=messages,
            max_tokens=1000,
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Anthropic API error: {e}")
        return None


# ---------------------------------------------------------------------------
# Main Chat Handler
# ---------------------------------------------------------------------------
def handle_chat_message(tenant, user_id, user_name, user_role, message, conversation_id=None):
    """
    Main entry point for processing a user message.

    Returns:
        dict with 'conversation_id', 'response', and 'conversation_title'
    """
    user_role_lower = (user_role or 'student').lower()

    # Get or create conversation
    if conversation_id:
        try:
            conversation = ChatConversation.objects.get(
                id=conversation_id, user_id=user_id, is_active=True
            )
        except ChatConversation.DoesNotExist:
            conversation = None

    if not conversation_id or not conversation:
        conversation = ChatConversation.objects.create(
            tenant=tenant,
            user_id=user_id,
            user_type=user_role_lower.upper(),
            user_name=user_name,
            title=message[:100] if message else 'New Conversation',
        )

    # Save user message
    ChatMessage.objects.create(
        conversation=conversation,
        role=ChatMessage.Role.USER,
        content=message,
    )

    # Build system prompt with context
    context_data = get_user_context(tenant, user_id, user_role_lower)
    system_prompt = build_system_prompt(user_id, user_name, user_role_lower, context_data)

    # Get conversation history
    history = list(
        ChatMessage.objects.filter(conversation=conversation)
        .order_by('created_at')
        .values('role', 'content')
    )
    # Keep last 20 messages for context window
    history = history[-20:]

    # Try AI provider first
    response_text = _generate_ai_response(system_prompt, history[:-1], message)

    # Fall back to FAQ pattern matching
    if not response_text:
        response_text = _match_faq(message, user_role_lower)

    # Final fallback
    if not response_text:
        if user_role_lower == 'student':
            response_text = (
                "I understand you have a question. Here are some things I can help you with:\n\n"
                "- **View your schedule** — check your upcoming classes\n"
                "- **Join a live class** — find and join classes that are streaming now\n"
                "- **Watch recordings** — replay past classes\n"
                "- **Check attendance** — see your attendance history\n\n"
                "Could you tell me more about what you need? "
                "If I can't help, please contact your teacher or admin."
            )
        elif user_role_lower == 'teacher':
            response_text = (
                "I'm here to help with your classes! I can assist with:\n\n"
                "- **Going live** — starting your class broadcast\n"
                "- **Marking attendance** — recording who attended\n"
                "- **Viewing watch time** — seeing how long students watched\n"
                "- **Creating extra classes** — setting up one-off sessions\n"
                "- **Your schedule** — checking upcoming classes\n\n"
                "What would you like help with?"
            )
        else:
            response_text = (
                "I can help you manage the platform! I can assist with:\n\n"
                "- **Class schedules** — creating and managing recurring classes\n"
                "- **Enrollments** — adding students to classes\n"
                "- **Holidays** — setting up blackout dates\n"
                "- **Reports** — attendance and watch time\n"
                "- **Teacher no-shows** — understanding the auto-cancel system\n\n"
                "What would you like to do?"
            )

    # Save assistant response
    ChatMessage.objects.create(
        conversation=conversation,
        role=ChatMessage.Role.ASSISTANT,
        content=response_text,
        context_summary={
            'has_ai_provider': bool(getattr(settings, 'EDUASSIST_AI_PROVIDER', None)),
            'matched_faq': response_text == _match_faq(message, user_role_lower),
            'user_context_keys': list(context_data.keys()) if context_data else [],
        }
    )

    # Update conversation title from first message
    if conversation.messages.count() <= 2:
        conversation.title = message[:100]
        conversation.save(update_fields=['title', 'updated_at'])

    return {
        'conversation_id': str(conversation.id),
        'response': response_text,
        'conversation_title': conversation.title,
    }
