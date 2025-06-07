# core/views.py

import json

from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages

from .crud import (
    create_donor,
    create_coin_donation,
    create_gcash_donation,
    verify_donation_facial,
    create_beneficiary,
    create_claim,
    update_claim_status,
    update_donation_status,
    get_coin_box_status,
    reset_coin_box,
    list_all_donations,
    list_all_claims,
    list_all_donors,
    list_all_beneficiaries,
    list_all_admins,
    list_audit_logs,
)
from .models import Donation, Claim, User

menu_file_path =  settings.BASE_DIR / "templates" / "layout" / "partials" / "menu" / "vertical" / "json" / "vertical_menu.json"


# -----------------------------------------------------------------------------
# 1. DONOR KIOSK: single view + two POST endpoints
# -----------------------------------------------------------------------------

class KioskDonorView(View):
    """
    Renders the Donor Kiosk page with two modals:
     - Coin Slot Modal
     - GCash QR Modal
    The JavaScript in js/kiosk/donate/donate.js will handle showing/hiding modals,
    tracking coin‐tally, fetching the QR image, and sending POSTs to the endpoints below.
    """
    def get(self, request):
        return render(request, "kiosk/donor/donate.html", {
          "layout_path" : "layout/layout_blank.html"
        })


def coin_donate(request):
    """
    Handles POST from the Coin Slot modal. Expects JSON or form data:
      - donation_type: "Anonymous" or "Named"
      - coin_count: integer (number of ₱1 coins inserted)
      - first_name, last_name, username (only if donation_type == "Named")
    Returns JSON {"success": true} or {"error": "..."}.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method")

    data = request.POST or json.loads(request.body.decode("utf-8"))
    donation_type = data.get("donation_type")
    coin_count_str = data.get("coin_count")

    # Validate coin_count
    try:
        coin_count = int(coin_count_str)
        if coin_count <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid coin count."}, status=400)

    # Determine user (if Named)
    user = None
    if donation_type == "Named":
        username = data.get("username", "").strip()
        if username:
            try:
                user = User.objects.get(username=username, role="donor")
            except User.DoesNotExist:
                # Create a new donor record with given first/last/email = blank
                first_name = data.get("first_name", "").strip()
                last_name = data.get("last_name", "").strip()
                # We need at least a username/password. Generate a random password.
                random_pw = User.objects.make_random_password()
                user = create_donor(
                    username=username,
                    password=random_pw,
                    email="",
                    first_name=first_name,
                    last_name=last_name,
                    phone="",
                    face_photo_file=None,
                )
        else:
            # Named but no username → error
            return JsonResponse({"error": "Username required for Named donation."}, status=400)

    # Create the coin donation (guest if user=None)
    try:
        donation = create_coin_donation(
            user_id=user.id if user else None,
            coin_count=coin_count
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"success": True})


def gcash_donate(request):
    """
    Handles POST from the GCash QR modal. Expects JSON or form data:
      - donation_type: "Anonymous" or "Named"
      - amount: integer (₱5, ₱10, etc.)
      - first_name, last_name, username (only if donation_type == "Named")
      - reference_number: string (entered after user scans QR & pays)
    Returns JSON {"success": true} or {"error": "..."}.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method")

    data = request.POST or json.loads(request.body.decode("utf-8"))
    donation_type = data.get("donation_type")
    amount_str = data.get("amount")
    reference_number = data.get("reference_number", "").strip()

    # Validate amount
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid amount."}, status=400)

    # Validate reference number
    if not reference_number:
        return JsonResponse({"error": "Reference number is required."}, status=400)

    # Determine user (if Named)
    user = None
    if donation_type == "Named":
        username = data.get("username", "").strip()
        if username:
            try:
                user = User.objects.get(username=username, role="donor")
            except User.DoesNotExist:
                # Create a new donor record
                first_name = data.get("first_name", "").strip()
                last_name = data.get("last_name", "").strip()
                random_pw = User.objects.make_random_password()
                user = create_donor(
                    username=username,
                    password=random_pw,
                    email="",
                    first_name=first_name,
                    last_name=last_name,
                    phone="",
                    face_photo_file=None,
                )
        else:
            return JsonResponse({"error": "Username required for Named donation."}, status=400)

    # Create the GCash donation
    try:
        donation = create_gcash_donation(
            user_id=user.id if user else None,
            amount=amount,
            gcash_ref_number=reference_number
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"success": True})


# -----------------------------------------------------------------------------
# 2. DONOR WEB PORTAL VIEWS (unchanged)
# -----------------------------------------------------------------------------
class DonorWebChoiceView(View):
    def get(self, request):
        return render(request, "web/donor/choice.html", {
          "layout_path": "layout/layout_blank.html"
        })

class DonorWebRegisterView(View):
    def get(self, request):
        return render(request, "web/donor/register.html", {
          "layout_path": "layout/layout_blank.html"
        })

    def post(self, request):
        data = request.POST
        username = data.get("username")
        password = data.get("password")
        confirm_pw = data.get("confirm_password")
        email = data.get("email")
        phone = data.get("phone", "")
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        face_photo = request.FILES.get("face_photo")

        if password != confirm_pw:
            messages.error(request, "Passwords do not match.")
            return redirect(reverse("web_donor_register"))

        donor = create_donor(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            face_photo_file=face_photo,
        )
        login(request, donor)
        return redirect(reverse("web_donor_donate"))


class DonorWebLoginView(View):
    def get(self, request):
        return render(request, "web/donor/login.html", {
          "layout_path": "layout/layout_blank.html"
        })

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is None or user.role != "donor":
          messages.error(request, "Invalid donor credentials.")
          return redirect(reverse("web_donor_login"))
        login(request, user)
        return redirect(reverse("web_donor_donate"))


@login_required
def donor_web_logout(request):
    logout(request)
    return redirect(reverse("web"))


class DonorWebDonateView(View):
    def get(self, request):
        return render(request, "web/donor/donate.html")

    def post(self, request):
        try:
            amount = float(request.POST.get("amount_paid", "0"))
            ref_num = request.POST.get("gcash_ref_number", "").strip()
            if amount <= 0 or not ref_num:
                raise ValueError
        except ValueError:
            return HttpResponseBadRequest("Invalid input.")

        user = request.user if request.user.role == "donor" else None
        create_gcash_donation(
            user_id=user.id if user else None,
            amount=amount,
            gcash_ref_number=ref_num
        )
        return redirect(reverse("web_donor_thank_you", kwargs={"donation_id": Donation.objects.latest("id").id}))


class DonorWebThankYouView(View):
    def get(self, request, donation_id: int):
        donation = get_object_or_404(Donation, id=donation_id)
        return render(request, "web/donor/thank_you.html", {"donation": donation})


# -----------------------------------------------------------------------------
# 3. BENEFICIARY KIOSK VIEWS (unchanged)
# -----------------------------------------------------------------------------

class KioskBeneficiaryWelcomeView(View):
    def get(self, request):
        return render(request, "kiosk/beneficiary/welcome.html")


class KioskBeneficiaryAuthView(View):
    def get(self, request):
        return render(request, "kiosk/beneficiary/auth.html")

    def post(self, request):
        action = request.POST.get("action")
        if action == "scan_face":
            return redirect(reverse("kiosk_beneficiary_facial_recog"))
        elif action == "login":
            return redirect(reverse("kiosk_beneficiary_login"))
        else:
            return redirect(reverse("kiosk_beneficiary_welcome"))


class KioskBeneficiaryFacialRecogView(View):
    def get(self, request):
        return render(request, "kiosk/beneficiary/facial_recog.html")

    def post(self, request):
        verification_photo = request.FILES.get("photo")
        if not verification_photo:
            return HttpResponseBadRequest("No photo uploaded.")

        beneficiary = User.objects.filter(role="beneficiary").first()
        if beneficiary:
            login(request, beneficiary)
            return redirect(reverse("kiosk_beneficiary_need_selection"))
        else:
            return HttpResponseBadRequest("No matching beneficiary found.")


class KioskBeneficiaryLoginView(View):
    def get(self, request):
        return render(request, "kiosk/beneficiary/login.html")

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is None or user.role != "beneficiary":
            return HttpResponseBadRequest("Invalid beneficiary credentials.")
        login(request, user)
        return redirect(reverse("kiosk_beneficiary_need_selection"))


@method_decorator(login_required, name="dispatch")
class KioskBeneficiaryNeedSelectionView(View):
    def get(self, request):
        if request.user.role != "beneficiary":
            return redirect(reverse("kiosk_beneficiary_auth"))
        return render(request, "kiosk/beneficiary/need_selection.html", {
            "first_name": request.user.first_name
        })

    def post(self, request):
        need_type = request.POST.get("need_type")
        if need_type not in dict(Claim.NEED_CHOICES).keys():
            return HttpResponseBadRequest("Invalid need type.")
        request.session["selected_need"] = need_type
        return redirect(reverse("kiosk_beneficiary_request_details"))


@method_decorator(login_required, name="dispatch")
class KioskBeneficiaryRequestDetailsView(View):
    def get(self, request):
        need_type = request.session.get("selected_need")
        return render(request, "kiosk/beneficiary/request_details.html", {
            "need_type": need_type
        })

    def post(self, request):
        need_type = request.session.get("selected_need")
        try:
            amount = float(request.POST.get("requested_amount", "0"))
            if amount <= 0:
                raise ValueError
        except ValueError:
            return HttpResponseBadRequest("Invalid amount.")

        claim = create_claim(user_id=request.user.id, need_type=need_type, requested_amount=amount)
        request.session["latest_claim_id"] = claim.id
        return redirect(reverse("kiosk_beneficiary_processing"))


@method_decorator(login_required, name="dispatch")
class KioskBeneficiaryProcessingView(View):
    def get(self, request):
        return render(request, "kiosk/beneficiary/processing.html")

    def post(self, request):
        return redirect(reverse("kiosk_beneficiary_pending"))


@method_decorator(login_required, name="dispatch")
class KioskBeneficiaryPendingView(View):
    def get(self, request):
        return render(request, "kiosk/beneficiary/pending.html")


@method_decorator(login_required, name="dispatch")
class KioskBeneficiaryAutoPaidView(View):
    def get(self, request):
        return render(request, "kiosk/beneficiary/auto_paid.html")


# -----------------------------------------------------------------------------
# 4. BENEFICIARY WEB PORTAL VIEWS (unchanged)
# -----------------------------------------------------------------------------
class BeneficiaryWebRegisterView(View):
    def get(self, request):
        return render(request, "web/beneficiary/register.html", {
          "layout_path": "layout/layout_blank.html"
        })

    def post(self, request):
        data = request.POST
        username = data.get("username")
        password = data.get("password")
        confirm_pw = data.get("confirm_password")
        email = data.get("email")
        phone = data.get("phone", "")
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        face_photo = request.FILES.get("face_photo")

        if password != confirm_pw:
            messages.error(request, "Passwords do not match.")
            return redirect(reverse("web_beneficiary_register"))

        beneficiary = create_beneficiary(
            username=username,
            password=password,
            email=email,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            face_photo_file=face_photo,
        )
        login(request, beneficiary)
        return redirect(reverse("web_beneficiary_dashboard"))


class BeneficiaryWebLoginView(View):
    def get(self, request):
        return render(request, "web/beneficiary/login.html", {
          "layout_path": "layout/layout_blank.html"
        })

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is None or user.role != "beneficiary":
          messages.error(request, "Invalid beneficiary credentials.")
          return redirect(reverse("web_beneficiary_login"))
        login(request, user)
        return redirect(reverse("web_beneficiary_dashboard"))

@login_required
def beneficiary_web_logout(request):
    logout(request)
    return redirect(reverse("web"))


@method_decorator(login_required, name="dispatch")
class BeneficiaryWebDashboardView(View):
    def get(self, request):
        if request.user.role != "beneficiary":
            return redirect(reverse("web_beneficiary_login"))

        beneficiary = request.user
        claims = list_all_claims().filter(user=beneficiary)
        return render(request, "web/beneficiary/dashboard.html", {
            "balance": beneficiary.current_balance,
            "claims": claims,
        })


@method_decorator(login_required, name="dispatch")
class BeneficiaryWebNewRequestView(View):
    def get(self, request):
        return render(request, "web/beneficiary/new_request.html")

    def post(self, request):
        try:
            need_type = request.POST.get("need_type")
            amount = float(request.POST.get("requested_amount", "0"))
            if amount <= 0 or need_type not in dict(Claim.NEED_CHOICES).keys():
                raise ValueError
        except ValueError:
            return HttpResponseBadRequest("Invalid data.")

        create_claim(user_id=request.user.id, need_type=need_type, requested_amount=amount)
        return redirect(reverse("web_beneficiary_dashboard"))


# -----------------------------------------------------------------------------
# 5. ADMIN DASHBOARD VIEWS (unchanged)
# -----------------------------------------------------------------------------

def is_admin(user):
    return user.is_authenticated and user.role == "admin"


class AdminLoginView(View):
  def get(self, request):
    if request.user.is_authenticated and getattr(request.user, "role", None) == "admin":
      return redirect(reverse("admin_dashboard"))
    return render(request, "admin/login.html", {
      "layout_path": "layout/layout_blank.html"
    })

  def post(self, request):
    username = request.POST.get("email-username")
    password = request.POST.get("password")
    user = authenticate(request, username=username, password=password)

    if user is None or getattr(user, "role", None) != "admin":
      messages.error(request, "Invalid admin credentials.")
      return redirect(reverse("admin_login"))

    login(request, user)
    return redirect(reverse("admin_dashboard"))


@login_required
@user_passes_test(is_admin)
def admin_logout(request):
    logout(request)
    return redirect(reverse("web"))


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    today = timezone.now().date()
    total_today = sum(d.amount for d in Donation.objects.filter(created_at__date=today))
    week_start = today - timezone.timedelta(days=7)
    total_week = sum(d.amount for d in Donation.objects.filter(created_at__gte=week_start))
    month_start = today.replace(day=1)
    total_month = sum(d.amount for d in Donation.objects.filter(created_at__gte=month_start))

    coin_total = sum(d.amount for d in Donation.objects.filter(method="coin"))
    gcash_total = sum(d.amount for d in Donation.objects.filter(method="gcash"))

    pending_claims_count = Claim.objects.filter(status="pending").count()
    coin_box = get_coin_box_status()

    menu_data = json.load(menu_file_path.open()) if menu_file_path.exists() else []

    return render(request, "admin/dashboard.html", {
        "total_today": total_today,
        "total_week": total_week,
        "total_month": total_month,
        "coin_total": coin_total,
        "gcash_total": gcash_total,
        "pending_claims_count": pending_claims_count,
        "coin_box": coin_box,
        "is_flex": True,
        "content_navbar": True,
        "is_navbar": True,
        "is_menu": True,
        "is_footer": True,
        "navbar_detached": True,
        "menu_data": menu_data,
        "layout_path" : "layout/layout_vertical.html"
    })


@login_required
@user_passes_test(is_admin)
def admin_donors_page(request):
    donors = list_all_donors()

    menu_data = json.load(menu_file_path.open()) if menu_file_path.exists() else []

    return render(request, "admin/donors.html", {
      "donors": donors,
      "is_flex": True,
      "content_navbar": True,
      "is_navbar": True,
      "is_menu": True,
      "is_footer": True,
      "navbar_detached": True,
      "menu_data": menu_data,
      "layout_path": "layout/layout_vertical.html"
    })

@login_required
@user_passes_test(is_admin)
def admin_donor_update(request, donor_id):
    """
    GET: Return JSON with the donor's current data (first_name, last_name, email, phone).
    POST: Update those fields. Return {"success": true} on success.
    """
    donor = get_object_or_404(User, id=donor_id, role="donor")

    if request.method == "GET":
        data = {
            "first_name": donor.first_name,
            "last_name": donor.last_name,
            "email": donor.email,
            "phone": donor.phone or "",
        }
        return JsonResponse(data)

    elif request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()

        # Basic validation (you can extend as needed)
        if not email:
            return JsonResponse({"error": "Email is required."}, status=400)
        if not first_name:
            return JsonResponse({"error": "First name is required."}, status=400)
        if not last_name:
            return JsonResponse({"error": "Last name is required."}, status=400)

        donor.first_name = first_name
        donor.last_name = last_name
        donor.email = email
        donor.phone = phone
        donor.save()

        return JsonResponse({"success": True})

    else:
        return HttpResponseBadRequest("Invalid method.")


@login_required
@user_passes_test(is_admin)
def admin_donor_delete(request, donor_id):
    """
    POST: Deletes the donor. Return {"success": true} on success.
    """
    donor = get_object_or_404(User, id=donor_id, role="donor")

    if request.method == "POST":
        donor.delete()
        return JsonResponse({"success": True})
    else:
        return HttpResponseBadRequest("Invalid method.")


@login_required
@user_passes_test(is_admin)
def admin_beneficiaries_page(request):
    beneficiaries = list_all_beneficiaries()

    menu_data = json.load(menu_file_path.open()) if menu_file_path.exists() else []

    return render(request, "admin/beneficiaries.html", {
      "beneficiaries": beneficiaries,
      "is_flex": True,
      "content_navbar": True,
      "is_navbar": True,
      "is_menu": True,
      "is_footer": True,
      "navbar_detached": True,
      "menu_data": menu_data,
      "layout_path": "layout/layout_vertical.html"
    })



@login_required
@user_passes_test(is_admin)
def admin_beneficiaries_update(request, beneficiaryId):
    """
    GET: Return JSON with the donor's current data (first_name, last_name, email, phone).
    POST: Update those fields. Return {"success": true} on success.
    """
    donor = get_object_or_404(User, id=beneficiaryId, role="beneficiary")

    if request.method == "GET":
        data = {
            "first_name": donor.first_name,
            "last_name": donor.last_name,
            "email": donor.email,
            "phone": donor.phone or "",
        }
        return JsonResponse(data)

    elif request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password")
        confirm_pw = request.POST.get("confirm_password")

        # Basic validation (you can extend as needed)
        if not email:
            return JsonResponse({"error": "Email is required."}, status=400)
        if not first_name:
            return JsonResponse({"error": "First name is required."}, status=400)
        if not last_name:
            return JsonResponse({"error": "Last name is required."}, status=400)

        donor.first_name = first_name
        donor.last_name = last_name
        donor.email = email
        donor.phone = phone
        if password:
          if password != confirm_pw:
            return JsonResponse({"error": "Passwords do not match."}, status=400)
          donor.set_password(password)
        donor.save()

        return JsonResponse({"success": True})

    else:
        return HttpResponseBadRequest("Invalid method.")

@login_required
@user_passes_test(is_admin)
def admin_beneficiaries_delete(request, beneficiaryId):
    """
    POST: Deletes the donor. Return {"success": true} on success.
    """
    donor = get_object_or_404(User, id=beneficiaryId, role="beneficiary")

    if request.method == "POST":
        donor.delete()
        return JsonResponse({"success": True})
    else:
        return HttpResponseBadRequest("Invalid method.")


@login_required
@user_passes_test(is_admin)
def admin_donations_log(request):
    method = request.GET.get("method")
    status = request.GET.get("status")
    donations = list_all_donations(method=method, status=status)
    return render(request, "admin/donations_log.html", {"donations": donations})


@login_required
@user_passes_test(is_admin)
def admin_donation_action(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id)
    if donation.status != "pending":
        return HttpResponseBadRequest("Donation not pending.")

    action = request.POST.get("action")
    reason = request.POST.get("reason", "").strip()
    if action == "approve":
        update_donation_status(donation_id=donation_id, new_status="confirmed", admin_user_id=request.user.id)
    elif action == "reject":
        update_donation_status(donation_id=donation_id, new_status="pending", admin_user_id=request.user.id, notes=reason)
    else:
        return HttpResponseBadRequest("Invalid action.")
    return JsonResponse({"success": True})


@login_required
@user_passes_test(is_admin)
def admin_claims_log(request):
    need_type = request.GET.get("need_type")
    status = request.GET.get("status")
    claims = list_all_claims(need_type=need_type, status=status)
    return render(request, "admin/claims_log.html", {"claims": claims})


@login_required
@user_passes_test(is_admin)
def admin_claim_action(request, claim_id):
    claim = get_object_or_404(Claim, id=claim_id)
    if claim.status != "pending":
        return HttpResponseBadRequest("Claim not pending.")

    action = request.POST.get("action")
    reason = request.POST.get("reason", "").strip()
    if action == "approve":
        update_claim_status(claim_id=claim_id, new_status="approved", admin_user_id=request.user.id, reason=reason)
    elif action == "reject":
        update_claim_status(claim_id=claim_id, new_status="rejected", admin_user_id=request.user.id, reason=reason)
    elif action == "manual_pay":
        payout_id = request.POST.get("gcash_payout_id", "").strip()
        if not payout_id:
            return HttpResponseBadRequest("Missing payout ID.")
        update_claim_status(claim_id=claim_id, new_status="paid", admin_user_id=request.user.id, gcash_payout_id=payout_id)
    else:
        return HttpResponseBadRequest("Invalid action.")
    return JsonResponse({"success": True})


@login_required
@user_passes_test(is_admin)
def admin_coin_box_page(request):
    coin_box = get_coin_box_status()
    alert = coin_box.current_count >= 0.75 * coin_box.capacity
    return render(request, "admin/coin_box.html", {
        "coin_box": coin_box,
        "alert": alert,
    })


@login_required
@user_passes_test(is_admin)
def admin_coin_box_reset(request):
    if request.method == "POST":
        reset_coin_box(admin_user_id=request.user.id)
    return JsonResponse({"success": True})


@login_required
@user_passes_test(is_admin)
def admin_reports_page(request):
    return render(request, "admin/reports.html")


@login_required
@user_passes_test(is_admin)
def admin_settings_page(request):
    admins = list_all_admins()
    coin_box = get_coin_box_status()
    return render(request, "admin/settings.html", {
        "admins": admins,
        "coin_box_capacity": coin_box.capacity,
    })


@login_required
@user_passes_test(is_admin)
def admin_audit_logs_page(request):
    logs = list_audit_logs()
    return render(request, "admin/audit_logs.html", {"logs": logs})
