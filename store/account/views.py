from django.shortcuts import render, redirect
from django.views import View
from . import forms
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model


User = get_user_model()

class SignupView(View):
    # to show empty form to user
    def get(self, request):
        form = forms.SignupForm()
        return render(request, 'account/signup.html', {'form': form})

    # to get form data from user
    def post(self, request):
        form = forms.SignupForm(request.POST)
        if form.is_valid():
            # obj = form.save()  # creates obj & saves it to db
            user = form.save(commit=False)  # creates obj but don't save it to db
            user.is_active = False  # Require email confirmation to login
            user.save()  # save to db

            # Generate activation link
            current_site = get_current_site(request)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            activation_link = f"https://{current_site.domain}/account/activate/{uid}/{token}/"

            email_subject = "Please activate your account"
            email_to = [user.email]  # list of user emails
            email_body = render_to_string('account/signup_email.html',
                                    {'user':user,
                                            'activation_link': activation_link,
                                            })

            email = EmailMessage(
                subject = email_subject,
                body = email_body,
                to=email_to)

            email.content_subtype = "html"  # Enable HTML
            email.send()

            # to tell user activation link is sent
            return render(request, 'account/signup_done.html', {'user': user})

        # form was not valid so we return form (with entered data) to user again
        return render(request, 'account/signup.html', {'form': form})


class ActivateAccountView(View):
    def get(self, request, uidb64, token):
        try:
            # Decode the user ID
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        # Check if user exists and token is valid
        if user is not None and default_token_generator.check_token(user, token):
            # Activate the user
            user.is_active = True
            user.save()
            return render(request, 'account/activation_success.html')
        else:
            return render(request, 'account/activation_invalid.html')