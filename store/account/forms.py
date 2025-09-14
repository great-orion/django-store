from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from phonenumber_field.formfields import PhoneNumberField
from . import models
from django.contrib.auth.forms import UserCreationForm


# using model
class SignupForm(UserCreationForm):
    class Meta:
        model = models.User
        # fields that we don't want to have in form:
        exclude = ['is_staff', 'is_active', 'is_superuser', 'date_joined',
                   'last_login', 'user_permissions', 'groups', 'address', 'avatar', 'password']


# custom form
# class SignupForm(forms.Form):
#     name = forms.CharField(max_length=255)
#     lastName = forms.CharField(max_length=255)
#     email = forms.EmailField()
#     password1 = forms.CharField(max_length=255, widget=forms.PasswordInput())
#     password2 = forms.CharField(max_length=255, widget=forms.PasswordInput())
#     # phone = forms.CharField(max_length=15, validators=[validators.RegexValidator(r'^(\+98|09|9)?9\d{9}$'),
#     #                                                     validators.MinLengthValidator(5),
#     #                                                     validators.MaxLengthValidator(20)])
#
#     phone = PhoneNumberField()
#
#     def clean_name(self):
#         if self.cleaned_data['name'] == self.data['password1']:   # we can cot use cleaned_data on pawword1 here
#             raise ValidationError("name & password must not be the same.")
#
#         return self.cleaned_data['name']


