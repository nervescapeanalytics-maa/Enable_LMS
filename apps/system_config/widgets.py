"""
Friendly JSON Widgets for Django Admin
=======================================
Replace raw JSON textareas with user-friendly visual editors.
"""
import json
from django import forms
from django.utils.safestring import mark_safe


class FriendlyJSONMixin:
    """Base mixin for all friendly JSON widgets."""

    def format_value(self, value):
        if value is None:
            return self.get_empty_value()
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return self.get_empty_value()
        return value

    def get_empty_value(self):
        return {}

    def value_from_datadict(self, data, files, name):
        """Override in subclass to reconstruct JSON from form data."""
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════
# TAG LIST WIDGET — for simple string lists
# e.g. columns_json, group_by, sort_by, affected_features,
#      allowed_user_types, playlist_ids
# ═══════════════════════════════════════════════════════════════════
class TagListWidget(FriendlyJSONMixin, forms.Widget):
    """Renders a list of strings as tag-style chips with add/remove."""
    template_name = 'admin/widgets/tag_list.html'

    def __init__(self, attrs=None, placeholder='Type and press Enter…',
                 suggestions=None):
        super().__init__(attrs)
        self.placeholder = placeholder
        self.suggestions = suggestions or []

    def get_empty_value(self):
        return []

    def get_context(self, name, value, attrs):
        value = self.format_value(value)
        if not isinstance(value, list):
            value = []
        context = super().get_context(name, value, attrs)
        context['widget'].update({
            'items': value,
            'placeholder': self.placeholder,
            'suggestions': json.dumps(self.suggestions),
        })
        return context

    def value_from_datadict(self, data, files, name):
        # Items are sent as hidden fields with name="<name>_items"
        items = data.getlist(f'{name}_items')
        # Filter out empty strings
        return json.dumps([i.strip() for i in items if i.strip()])


# ═══════════════════════════════════════════════════════════════════
# EMAIL LIST WIDGET — for email lists with validation display
# e.g. recipients_email
# ═══════════════════════════════════════════════════════════════════
class EmailListWidget(FriendlyJSONMixin, forms.Widget):
    """Renders a list of emails as tag chips with email validation."""
    template_name = 'admin/widgets/email_list.html'

    def get_empty_value(self):
        return []

    def get_context(self, name, value, attrs):
        value = self.format_value(value)
        if not isinstance(value, list):
            value = []
        context = super().get_context(name, value, attrs)
        context['widget'].update({
            'emails': value,
        })
        return context

    def value_from_datadict(self, data, files, name):
        items = data.getlist(f'{name}_items')
        return json.dumps([i.strip() for i in items if i.strip()])


# ═══════════════════════════════════════════════════════════════════
# KEY-VALUE WIDGET — for flat dicts
# e.g. config_json, usage_stats, setting_json, filters_json
# ═══════════════════════════════════════════════════════════════════
class KeyValueWidget(FriendlyJSONMixin, forms.Widget):
    """Renders a dict as key/value rows with add/remove."""
    template_name = 'admin/widgets/key_value.html'

    def __init__(self, attrs=None, key_placeholder='Key',
                 value_placeholder='Value'):
        super().__init__(attrs)
        self.key_placeholder = key_placeholder
        self.value_placeholder = value_placeholder

    def get_empty_value(self):
        return {}

    def get_context(self, name, value, attrs):
        value = self.format_value(value)
        if not isinstance(value, dict):
            value = {}
        pairs = list(value.items())
        context = super().get_context(name, value, attrs)
        context['widget'].update({
            'pairs': pairs,
            'key_placeholder': self.key_placeholder,
            'value_placeholder': self.value_placeholder,
        })
        return context

    def value_from_datadict(self, data, files, name):
        keys = data.getlist(f'{name}_keys')
        vals = data.getlist(f'{name}_vals')
        result = {}
        for k, v in zip(keys, vals):
            k = k.strip()
            if k:
                # Try to auto-convert numbers and booleans
                if v.lower() in ('true', 'false'):
                    result[k] = v.lower() == 'true'
                else:
                    try:
                        result[k] = int(v)
                    except ValueError:
                        try:
                            result[k] = float(v)
                        except ValueError:
                            result[k] = v
        return json.dumps(result)


# ═══════════════════════════════════════════════════════════════════
# SOCIAL LINKS WIDGET — for social media dicts
# e.g. social_links, social_links_json
# ═══════════════════════════════════════════════════════════════════
class SocialLinksWidget(FriendlyJSONMixin, forms.Widget):
    """Renders social media links as labeled icon rows."""
    template_name = 'admin/widgets/social_links.html'

    PLATFORMS = [
        ('facebook', 'fab fa-facebook', '#1877f2', 'Facebook URL'),
        ('twitter', 'fab fa-x-twitter', '#000000', 'Twitter / X URL'),
        ('instagram', 'fab fa-instagram', '#e4405f', 'Instagram URL'),
        ('youtube', 'fab fa-youtube', '#ff0000', 'YouTube URL'),
        ('linkedin', 'fab fa-linkedin', '#0a66c2', 'LinkedIn URL'),
        ('whatsapp', 'fab fa-whatsapp', '#25d366', 'WhatsApp URL'),
        ('telegram', 'fab fa-telegram', '#0088cc', 'Telegram URL'),
    ]

    def get_empty_value(self):
        return {}

    def get_context(self, name, value, attrs):
        value = self.format_value(value)
        if not isinstance(value, dict):
            value = {}
        platforms = []
        for key, icon, color, placeholder in self.PLATFORMS:
            platforms.append({
                'key': key,
                'icon': icon,
                'color': color,
                'placeholder': placeholder,
                'value': value.get(key, ''),
            })
        context = super().get_context(name, value, attrs)
        context['widget'].update({
            'platforms': platforms,
        })
        return context

    def value_from_datadict(self, data, files, name):
        result = {}
        for key, _, _, _ in self.PLATFORMS:
            val = data.get(f'{name}_{key}', '').strip()
            if val:
                result[key] = val
        return json.dumps(result)


# ═══════════════════════════════════════════════════════════════════
# LINKS LIST WIDGET — for footer links [{label, url, icon?}]
# e.g. links_json
# ═══════════════════════════════════════════════════════════════════
class LinksListWidget(FriendlyJSONMixin, forms.Widget):
    """Renders a list of {label, url, icon?} as a dynamic table."""
    template_name = 'admin/widgets/links_list.html'

    def get_empty_value(self):
        return []

    def get_context(self, name, value, attrs):
        value = self.format_value(value)
        if not isinstance(value, list):
            value = []
        context = super().get_context(name, value, attrs)
        context['widget'].update({
            'links': value,
        })
        return context

    def value_from_datadict(self, data, files, name):
        labels = data.getlist(f'{name}_labels')
        urls = data.getlist(f'{name}_urls')
        icons = data.getlist(f'{name}_icons')
        result = []
        for i in range(len(labels)):
            label = labels[i].strip() if i < len(labels) else ''
            url = urls[i].strip() if i < len(urls) else ''
            icon = icons[i].strip() if i < len(icons) else ''
            if label and url:
                item = {'label': label, 'url': url}
                if icon:
                    item['icon'] = icon
                result.append(item)
        return json.dumps(result)


# ═══════════════════════════════════════════════════════════════════
# FILTERS WIDGET — for report filter conditions (dict)
# Now renders as an Excel-like filter builder with field/operator/value
# ═══════════════════════════════════════════════════════════════════
class FiltersWidget(FriendlyJSONMixin, forms.Widget):
    """Excel-like filter condition builder for reports."""
    template_name = 'admin/widgets/report_filters.html'

    FIELD_GROUPS = [
        ('Student Info', [
            ('student_name', 'Student Name'),
            ('roll_number', 'Roll Number'),
            ('email', 'Email'),
            ('phone', 'Phone'),
            ('status', 'Status'),
        ]),
        ('Class & Batch', [
            ('class_name', 'Class'),
            ('section', 'Section'),
            ('batch', 'Batch'),
            ('center', 'Center / Branch'),
        ]),
        ('Academics', [
            ('subject', 'Subject'),
            ('exam_name', 'Exam / Test Name'),
            ('grade', 'Grade'),
            ('percentage', 'Percentage'),
            ('rank', 'Rank'),
        ]),
        ('Attendance', [
            ('attendance_percentage', 'Attendance %'),
            ('present_count', 'Days Present'),
            ('absent_count', 'Days Absent'),
        ]),
        ('Date Range', [
            ('date_from', 'From Date'),
            ('date_to', 'To Date'),
            ('academic_year', 'Academic Year'),
            ('semester', 'Semester'),
        ]),
        ('Financial', [
            ('fee_amount', 'Fee Amount'),
            ('paid_amount', 'Paid Amount'),
            ('due_amount', 'Due Amount'),
            ('payment_status', 'Payment Status'),
        ]),
        ('Teacher Info', [
            ('teacher_name', 'Teacher Name'),
            ('department', 'Department'),
        ]),
    ]

    OPERATORS = [
        ('equals', 'Is Equal To'),
        ('not_equals', 'Is Not Equal To'),
        ('contains', 'Contains'),
        ('not_contains', 'Does Not Contain'),
        ('starts_with', 'Starts With'),
        ('greater_than', 'Greater Than'),
        ('less_than', 'Less Than'),
        ('greater_equal', 'Greater Than or Equal'),
        ('less_equal', 'Less Than or Equal'),
        ('is_empty', 'Is Empty'),
        ('is_not_empty', 'Is Not Empty'),
    ]

    def get_empty_value(self):
        return {}

    def get_context(self, name, value, attrs):
        value = self.format_value(value)
        if not isinstance(value, dict):
            value = {}

        # Convert stored dict to list of conditions for the template
        conditions = []
        if isinstance(value, dict) and 'conditions' in value:
            conditions = value['conditions']
        elif isinstance(value, dict):
            # Legacy format: plain key-value pairs → convert
            for k, v in value.items():
                conditions.append({
                    'field': k,
                    'operator': 'equals',
                    'value': str(v) if v is not None else '',
                })

        context = super().get_context(name, value, attrs)
        context['widget'].update({
            'conditions': conditions,
            'field_groups': self.FIELD_GROUPS,
            'field_groups_json': json.dumps(
                [[grp, fields] for grp, fields in self.FIELD_GROUPS]
            ),
            'operators': self.OPERATORS,
            'operators_json': json.dumps(self.OPERATORS),
        })
        return context

    def value_from_datadict(self, data, files, name):
        fields = data.getlist(f'{name}_field')
        operators = data.getlist(f'{name}_operator')
        values = data.getlist(f'{name}_value')
        conditions = []
        for i in range(len(fields)):
            field = fields[i].strip() if i < len(fields) else ''
            operator = operators[i].strip() if i < len(operators) else 'equals'
            val = values[i].strip() if i < len(values) else ''
            if field:
                conditions.append({
                    'field': field,
                    'operator': operator,
                    'value': val,
                })
        return json.dumps({'conditions': conditions})


# ═══════════════════════════════════════════════════════════════════
# SCHEDULE PICKER WIDGET — user-friendly cron replacement
# ═══════════════════════════════════════════════════════════════════
class SchedulePickerWidget(forms.Widget):
    """Visual recurring schedule picker — replaces raw cron expressions."""
    template_name = 'admin/widgets/schedule_picker.html'

    DAY_CHOICES = [
        ('1', 'Monday', 'Mon'),
        ('2', 'Tuesday', 'Tue'),
        ('3', 'Wednesday', 'Wed'),
        ('4', 'Thursday', 'Thu'),
        ('5', 'Friday', 'Fri'),
        ('6', 'Saturday', 'Sat'),
        ('0', 'Sunday', 'Sun'),
    ]

    def _parse_cron(self, cron_str):
        """Parse a cron string into frequency, time, days, monthday."""
        frequency = 'daily'
        time_value = '09:00'
        selected_days = ['1']
        selected_monthday = '1'

        if not cron_str or not isinstance(cron_str, str):
            return frequency, time_value, selected_days, selected_monthday

        parts = cron_str.strip().split()
        if len(parts) < 5:
            return frequency, time_value, selected_days, selected_monthday

        minute, hour, dom, _, dow = parts[0], parts[1], parts[2], parts[3], parts[4]

        # Time
        try:
            h = int(hour)
            m = int(minute)
            time_value = f'{h:02d}:{m:02d}'
        except (ValueError, TypeError):
            pass

        # Determine frequency
        if dow != '*':
            frequency = 'weekly'
            selected_days = [d.strip() for d in dow.split(',') if d.strip()]
        elif dom != '*':
            frequency = 'monthly'
            selected_monthday = dom

        return frequency, time_value, selected_days, selected_monthday

    def _build_preview(self, frequency, time_value, selected_days, selected_monthday):
        """Build a human-readable preview string."""
        day_short = {'1': 'Mon', '2': 'Tue', '3': 'Wed', '4': 'Thu', '5': 'Fri', '6': 'Sat', '0': 'Sun'}
        try:
            parts = time_value.split(':')
            h = int(parts[0])
            m = int(parts[1])
            ampm = 'PM' if h >= 12 else 'AM'
            dh = h % 12 or 12
            time_display = f'{dh}:{m:02d} {ampm}'
        except (ValueError, IndexError):
            time_display = '9:00 AM'

        if frequency == 'daily':
            return f'Runs every day at {time_display}'
        elif frequency == 'weekly':
            day_names = [day_short.get(d, d) for d in selected_days]
            return f'Runs every {", ".join(day_names)} at {time_display}'
        elif frequency == 'monthly':
            if selected_monthday == 'L':
                return f'Runs on the last day of every month at {time_display}'
            md = int(selected_monthday) if selected_monthday.isdigit() else 1
            suffix = 'th'
            if md in (1, 21, 31):
                suffix = 'st'
            elif md in (2, 22):
                suffix = 'nd'
            elif md in (3, 23):
                suffix = 'rd'
            return f'Runs on the {md}{suffix} of every month at {time_display}'
        return ''

    def get_context(self, name, value, attrs):
        cron_str = value or ''
        frequency, time_value, selected_days, selected_monthday = self._parse_cron(cron_str)
        preview_text = self._build_preview(frequency, time_value, selected_days, selected_monthday)

        context = super().get_context(name, value, attrs)
        context['widget'].update({
            'cron_value': cron_str,
            'frequency': frequency,
            'time_value': time_value,
            'selected_days': selected_days,
            'selected_monthday': selected_monthday,
            'day_choices': self.DAY_CHOICES,
            'month_days': list(range(1, 29)),
            'preview_text': preview_text,
        })
        return context

    def value_from_datadict(self, data, files, name):
        return data.get(name, '')
