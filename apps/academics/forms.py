from django import forms
from academics.models import Users, School, State, City, Category


class UsersAdminForm(forms.ModelForm):
    """Custom form for the Students admin — adds dropdown widgets for
    school_id, state_id, city_id, city_name and category."""

    school_id = forms.ModelChoiceField(
        queryset=School.objects.all(),
        required=False,
        label='School',
        empty_label='-- Select School --',
    )
    state_id = forms.ModelChoiceField(
        queryset=State.objects.all(),
        required=False,
        label='State',
        empty_label='-- Select State --',
    )
    city_id = forms.ModelChoiceField(
        queryset=City.objects.all(),
        required=False,
        label='District Name',
        empty_label='-- Select District --',
    )
    city_name = forms.CharField(
        required=False,
        label='City/Village',
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label='Category',
        empty_label='-- Select Category --',
    )

    class Meta:
        model = Users
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance:
            # Pre-select school by matching school.id (stored as int)
            if instance.school_id:
                try:
                    self.initial['school_id'] = School.objects.filter(
                        id=str(instance.school_id) if len(str(instance.school_id)) > 10 else None
                    ).first() or instance.school_id
                except Exception:
                    pass
            # Pre-select state
            if instance.state_id:
                try:
                    self.initial['state_id'] = State.objects.filter(
                        id=str(instance.state_id) if len(str(instance.state_id)) > 10 else None
                    ).first() or instance.state_id
                except Exception:
                    pass

    def clean_school_id(self):
        """Convert School model instance back to an integer for the IntegerField."""
        val = self.cleaned_data.get('school_id')
        if val is None:
            return None
        # Store the school's name for reference; the DB column is int
        # Since legacy uses integer IDs, store the pk representation
        return val.pk if hasattr(val, 'pk') else val

    def clean_state_id(self):
        val = self.cleaned_data.get('state_id')
        if val is None:
            return None
        return val.pk if hasattr(val, 'pk') else val

    def clean_city_id(self):
        val = self.cleaned_data.get('city_id')
        if val is None:
            return None
        return str(val) if val else None

    def clean_city_name(self):
        val = self.cleaned_data.get('city_name')
        return val.strip() if val else None

    def clean_category(self):
        val = self.cleaned_data.get('category')
        if val is None:
            return None
        return str(val) if val else None
