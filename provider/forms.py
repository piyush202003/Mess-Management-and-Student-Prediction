# provider/forms.py
from django import forms
from .models import *
import datetime
from django_select2.forms import Select2MultipleWidget

# class WeeklyMenuForm(forms.ModelForm):
#     # Use a CheckboxSelectMultiple for a better UI
#     menu_items = forms.ModelMultipleChoiceField(
#         queryset=MenuItem.objects.none(), # We will set this in the view
#         widget=forms.CheckboxSelectMultiple,
#         required=False
#     )

#     class Meta:
#         model = WeeklyMenu
#         fields = ['menu_items']
    
    # provider/forms.py
from django import forms
from .models import MenuItem, DailyMenu # Import both models

class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ['dish_name', 'dish_description', 'dish_image','is_special','dish_type'] 
        widgets = {
            'dish_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dish name'}),
            'dish_type': forms.Select(attrs={'class': 'form-control'}),
            'dish_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
            'dish_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_special': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }

from django import forms
from django_select2.forms import Select2MultipleWidget
from .models import MenuItem, DailyMenu
import datetime


class DailyMenuForm(forms.ModelForm):
    menu_items = forms.ModelMultipleChoiceField(
        queryset=MenuItem.objects.none(),
        widget=Select2MultipleWidget,  # <-- Using Select2 for searchable dropdown
        required=True,
        help_text="Search and select multiple dishes for this day's menu."
    )
    
    class Meta:
        model = DailyMenu
        fields = ['date', 'meal_type', 'menu_items']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        provider = kwargs.pop('provider', None)
        super().__init__(*args, **kwargs)
        
        # ✅ Restrict queryset to provider's items
        if provider:
            self.fields['menu_items'].queryset = MenuItem.objects.filter(provider=provider)
        
        # ✅ Display only the dish name (not provider) in Select2 dropdown
        self.fields['menu_items'].label_from_instance = lambda obj: obj.dish_name

        # ✅ Set date defaults (minimum = tomorrow)
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        self.fields['date'].widget.attrs['min'] = tomorrow.strftime('%Y-%m-%d')
        self.fields['date'].initial = tomorrow

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date <= datetime.date.today():
            raise forms.ValidationError(
                "You can only schedule menus for upcoming dates.", 
                code='past_date'
            )
        return date

    
class AddCouponsForm(forms.Form):
    """A simple form for a provider to add more coupons to a student's subscription."""
    coupons_to_add = forms.IntegerField(
        min_value=1,
        label="Number of Coupons to Add",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 30'})
    )