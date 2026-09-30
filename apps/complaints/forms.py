"""
Forms for Complaint app.
"""
from django import forms
from django.utils import timezone
from .models import Complaint, ComplaintCategory, ComplaintProof
from apps.users.models import Jurisdiction


class MultipleFileInput(forms.ClearableFileInput):
    """File input widget that supports selecting multiple files."""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """File field that returns a list of uploaded files.

    Follows the official Django pattern for multi-file uploads
    (https://docs.djangoproject.com/en/stable/topics/http/file-uploads/):
    each file is validated through FileField.clean(data, initial).
    NOTE: never call ``super(forms.FileField, self).clean(f, initial)`` --
    that skips FileField.clean and hits Field.clean(value), which raises
    ``TypeError: Field.clean() takes 2 positional arguments but 3 were given``.
    """
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if self.required and not data:
            raise forms.ValidationError(self.error_messages['required'])
        single_file_clean = super().clean  # bound to FileField.clean(data, initial)
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(f, initial) for f in data]
        else:
            result = [single_file_clean(data, initial)]
        return result


class ComplaintStep1Form(forms.ModelForm):
    """Form for step 1: Basic complaint information."""
    
    class Meta:
        model = Complaint
        fields = ['category', 'title', 'description']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Brief title for your complaint'}),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Detailed description of the issue...',
                'rows': 5
            }),
        }
        labels = {
            'category': 'Complaint Category',
            'title': 'Title',
            'description': 'Description',
        }
        help_texts = {
            'category': 'Select the category that best fits your complaint',
            'title': 'Give your complaint a short, descriptive title',
            'description': 'Provide as much detail as possible about the issue',
        }


class ComplaintStep2Form(forms.Form):
    """Form for step 2: Location and proof."""
    
    location_address = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter location address',
            'id': 'location-address'
        }),
        label='Location Address',
        help_text='Enter the exact location of the issue'
    )
    
    latitude = forms.DecimalField(
        widget=forms.HiddenInput(attrs={'id': 'latitude'}),
        required=False,
        label='Latitude'
    )
    
    longitude = forms.DecimalField(
        widget=forms.HiddenInput(attrs={'id': 'longitude'}),
        required=False,
        label='Longitude'
    )
    
    jurisdiction = forms.ModelChoiceField(
        queryset=Jurisdiction.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        label='Jurisdiction',
        help_text='Select the jurisdiction (optional, will be auto-detected if possible)'
    )
    
    proofs = MultipleFileField(
        widget=MultipleFileInput(attrs={
            'class': 'form-input',
            'accept': 'image/*,video/*,application/pdf'
        }),
        label='Proof/Evidence',
        help_text='Upload photos, videos, or documents to support your complaint (max 10MB each)',
        required=False
    )


class ComplaintStep3Form(forms.Form):
    """Form for step 3: Review and submit."""
    
    is_terms_accepted = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        label='I agree to the terms and conditions',
        required=True,
        help_text='You must accept the terms to submit your complaint'
    )
    
    is_accuracy_confirmed = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        label='I confirm that the information provided is accurate',
        required=True,
        help_text='Please confirm the accuracy of your complaint'
    )


class ComplaintForm(forms.ModelForm):
    """Complete complaint form."""
    
    class Meta:
        model = Complaint
        fields = [
            'category', 'title', 'description', 'location_address',
            'latitude', 'longitude', 'jurisdiction'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 5}),
            'location_address': forms.TextInput(attrs={'class': 'form-input'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'jurisdiction': forms.Select(attrs={'class': 'form-select'}),
        }


class ComplaintProofForm(forms.ModelForm):
    """Form for uploading proof."""
    
    class Meta:
        model = ComplaintProof
        fields = ['proof_type', 'file']
        widgets = {
            'proof_type': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-input',
                'accept': 'image/*,video/*,application/pdf'
            }),
        }


class ComplaintStatusUpdateForm(forms.ModelForm):
    """Form for updating complaint status."""
    
    class Meta:
        model = Complaint
        fields = ['status', 'priority', 'priority_score']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'priority_score': forms.NumberInput(attrs={'class': 'form-input', 'min': 1, 'max': 10}),
        }


class ComplaintAssignmentForm(forms.ModelForm):
    """Form for assigning complaint to official."""
    
    class Meta:
        model = Complaint
        fields = ['assigned_official', 'assigned_department']
        widgets = {
            'assigned_official': forms.Select(attrs={'class': 'form-select'}),
            'assigned_department': forms.Select(attrs={'class': 'form-select'}),
        }


class ComplaintCommitmentForm(forms.ModelForm):
    """Form for official to commit to resolve complaint."""
    
    class Meta:
        model = Complaint
        fields = ['commitment_date', 'commitment_visible']
        widgets = {
            'commitment_date': forms.DateTimeInput(attrs={
                'class': 'form-input',
                'type': 'datetime-local'
            }),
            'commitment_visible': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class ComplaintRatingForm(forms.ModelForm):
    """Form for citizen to rate complaint resolution."""
    
    class Meta:
        model = Complaint
        fields = ['citizen_ratings', 'citizen_comments']
        widgets = {
            'citizen_ratings': forms.Select(attrs={'class': 'form-select'}),
            'citizen_comments': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }
        labels = {
            'citizen_ratings': 'Rating (1-5)',
            'citizen_comments': 'Comments',
        }
