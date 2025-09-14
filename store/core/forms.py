from django import forms
from . import models

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = models.Invoice
        fields = ['address', 'description']


class SearchForm(forms.Form):
    query = forms.CharField(max_length=255)