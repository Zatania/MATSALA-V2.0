from django.urls import path
from django.contrib.auth.views import LogoutView
from .kiosk.views import KioskView
from .donate.views import DonateView
from .donate.coin.views import CoinView
from .donate.gcash.views import GcashView
from .assistance.views import AssistanceView
from .register.views import RegisterView
from .login.views import LoginView
from .forgot_password.views import ForgetPasswordView
from .reset_password.views import ResetPasswordView
from .verify_email.views import  VerifyEmailTokenView , VerifyEmailView, SendVerificationView
from .web import views
from .web.views import WebView
from django.views.generic import RedirectView

urlpatterns = [
    path(
        "web/",
        WebView.as_view(),
        name="web",
    ),
    path(
        "",
        RedirectView.as_view(url="/web/", permanent=False)
    ),
    path(
        "kiosk/",
        KioskView.as_view(),
        name="kiosk",
    ),
    path(
        "donate/",
        DonateView.as_view(template_name="auth/donate/donate.html"),
        name="donate",
    ),
    path(
        "coin/",
        CoinView.as_view(template_name="auth/donate/coin.html"),
        name="coin",
    ),
    path(
        "gcash/",
        GcashView.as_view(template_name="auth/donate/gcash.html"),
        name="gcash",
    ),
    path(
        "assistance/",
        AssistanceView.as_view(template_name="auth/assistance/assistance.html"),
        name="assistance",
    ),
    path(
        "login/",
        LoginView.as_view(template_name="auth/login.html"),
        name="login",
    ),

    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),

    path(
        "register/",
        RegisterView.as_view(template_name="auth/register.html"),
        name="register",
    ),

    path(
        "verify_email/",
        VerifyEmailView.as_view(template_name="auth/verify_email.html"),
        name="verify-email-page",
    ),

    path(
        "verify/email/<str:token>/",
        VerifyEmailTokenView.as_view(),
        name="verify-email",
    ),

    path(
        "send_verification/",
        SendVerificationView.as_view(),
        name="send-verification",
    ),

    path(
        "forgot_password/",
        ForgetPasswordView.as_view(template_name="auth/forgot_password.html"),
        name="forgot-password",
    ),

    path(
        "reset_password/<str:token>/",
        ResetPasswordView.as_view(template_name="auth/reset_password.html"),
        name="reset-password",
    ),

]
