# core/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # 1. DONOR KIOSK (render page + POST endpoints)
    # -------------------------------------------------------------------------
    path(
        "kiosk/donor/",
        views.KioskDonorView.as_view(),
        name="kiosk_donor"
    ),
    path(
        "kiosk/donor/coin-donate/",
        views.coin_donate,
        name="kiosk_coin_donate"
    ),
    path(
        "kiosk/donor/gcash-donate/",
        views.gcash_donate,
        name="kiosk_gcash_donate"
    ),

    # -------------------------------------------------------------------------
    # 2. DONOR WEB PORTAL
    # -------------------------------------------------------------------------
    path(
        "web/donor/choice/",
        views.DonorWebChoiceView.as_view(),
        name="web_donor_choice"
    ),
    path(
        "web/donor/register/",
        views.DonorWebRegisterView.as_view(),
        name="web_donor_register"
    ),
    path(
        "web/donor/login/",
        views.DonorWebLoginView.as_view(),
        name="web_donor_login"
    ),
    path(
        "web/donor/logout/",
        views.donor_web_logout,
        name="web_donor_logout"
    ),
    path(
        "web/donor/donate/",
        views.DonorWebDonateView.as_view(),
        name="web_donor_donate"
    ),
    path(
        "web/donor/thank-you/<int:donation_id>/",
        views.DonorWebThankYouView.as_view(),
        name="web_donor_thank_you"
    ),

    # -------------------------------------------------------------------------
    # 3. BENEFICIARY KIOSK
    # -------------------------------------------------------------------------
    path(
        "kiosk/beneficiary/",
        views.KioskBeneficiaryWelcomeView.as_view(),
        name="kiosk_beneficiary_welcome"
    ),
    path(
        "kiosk/beneficiary/auth/",
        views.KioskBeneficiaryAuthView.as_view(),
        name="kiosk_beneficiary_auth"
    ),
    path(
        "kiosk/beneficiary/facial-recog/",
        views.KioskBeneficiaryFacialRecogView.as_view(),
        name="kiosk_beneficiary_facial_recog"
    ),
    path(
        "kiosk/beneficiary/login/",
        views.KioskBeneficiaryLoginView.as_view(),
        name="kiosk_beneficiary_login"
    ),
    path(
        "kiosk/beneficiary/need-selection/",
        views.KioskBeneficiaryNeedSelectionView.as_view(),
        name="kiosk_beneficiary_need_selection"
    ),
    path(
        "kiosk/beneficiary/request-details/",
        views.KioskBeneficiaryRequestDetailsView.as_view(),
        name="kiosk_beneficiary_request_details"
    ),
    path(
        "kiosk/beneficiary/processing/",
        views.KioskBeneficiaryProcessingView.as_view(),
        name="kiosk_beneficiary_processing"
    ),
    path(
        "kiosk/beneficiary/pending/",
        views.KioskBeneficiaryPendingView.as_view(),
        name="kiosk_beneficiary_pending"
    ),
    path(
        "kiosk/beneficiary/auto-paid/",
        views.KioskBeneficiaryAutoPaidView.as_view(),
        name="kiosk_beneficiary_auto_paid"
    ),

    # -------------------------------------------------------------------------
    # 4. BENEFICIARY WEB PORTAL
    # -------------------------------------------------------------------------
    path(
        "web/beneficiary/register/",
        views.BeneficiaryWebRegisterView.as_view(),
        name="web_beneficiary_register"
    ),
    path(
        "web/beneficiary/login/",
        views.BeneficiaryWebLoginView.as_view(),
        name="web_beneficiary_login"
    ),
    path(
        "web/beneficiary/logout/",
        views.beneficiary_web_logout,
        name="web_beneficiary_logout"
    ),
    path(
        "web/beneficiary/dashboard/",
        views.BeneficiaryWebDashboardView.as_view(),
        name="web_beneficiary_dashboard"
    ),
    path(
        "web/beneficiary/new-request/",
        views.BeneficiaryWebNewRequestView.as_view(),
        name="web_beneficiary_new_request"
    ),

    # -------------------------------------------------------------------------
    # 5. ADMIN DASHBOARD
    # -------------------------------------------------------------------------
    path(
        "web/admin/login/",
        views.AdminLoginView.as_view(),
        name="admin_login"
    ),
    path(
        "web/admin/logout/",
        views.admin_logout,
        name="admin_logout"
    ),
    path(
        "web/admin/dashboard/",
        views.admin_dashboard,
        name="admin_dashboard"
    ),
    path(
        "web/admin/donors/",
        views.admin_donors_page,
        name="admin_donors"
    ),
    path(
        "web/admin/beneficiaries/",
        views.admin_beneficiaries_page,
        name="admin_beneficiaries"
    ),
    path(
        "web/admin/donations/",
        views.admin_donations_log,
        name="admin_donations_log"
    ),
    path(
        "web/admin/donations/<int:donation_id>/action/",
        views.admin_donation_action,
        name="admin_donation_action"
    ),
    path(
        "web/admin/claims/",
        views.admin_claims_log,
        name="admin_claims_log"
    ),
    path(
        "web/admin/donors/<int:donor_id>/update/",
        views.admin_donor_update,
        name="admin_donor_update"
    ),
    path(
        "web/admin/donors/<int:donor_id>/delete/",
        views.admin_donor_delete,
        name="admin_donor_delete"
    ),
    path(
        "web/admin/beneficiaries/<int:beneficiaryId>/update/",
        views.admin_beneficiaries_update,
        name="admin_beneficiaries_update"
    ),
    path(
        "web/admin/beneficiaries/<int:beneficiaryId>/delete/",
        views.admin_beneficiaries_delete,
        name="admin_beneficiaries_delete"
    ),
    path(
        "web/admin/claims/<int:claim_id>/action/",
        views.admin_claim_action,
        name="admin_claim_action"
    ),
    path(
        "web/admin/coin-box/",
        views.admin_coin_box_page,
        name="admin_coin_box"
    ),
    path(
        "web/admin/coin-box/reset/",
        views.admin_coin_box_reset,
        name="admin_coin_box_reset"
    ),
    path(
        "web/admin/reports/",
        views.admin_reports_page,
        name="admin_reports"
    ),
    path(
        "web/admin/settings/",
        views.admin_settings_page,
        name="admin_settings"
    ),
    path(
        "web/admin/audit-logs/",
        views.admin_audit_logs_page,
        name="admin_audit_logs"
    ),
]
