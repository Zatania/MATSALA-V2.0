# core/views.py
import datetime
from datetime import timedelta
import json
import tempfile
from decimal import Decimal

import face_recognition
import numpy as np
from PIL import Image
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models.aggregates import Sum, Count
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

from auth.models import Profile
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
  list_audit_logs, get_system_balance, get_system_disbursed,
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
@login_required
def web_donor_dashboard(request):
    user = request.user

    # 1) Compute “today” boundaries in local time
    now = timezone.localtime(timezone.now())
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_tomorrow = start_of_today + timedelta(days=1)

    # 2) Compute week & month boundaries relative to start_of_today
    week_start = start_of_today - timedelta(days=7)
    month_start = start_of_today.replace(day=1)

    qs = Donation.objects.filter(user=user)

    # 3) Build totals using __gte / __lt on full datetimes
    totals = {
      "Today": qs.filter(
        created_at__gte=start_of_today,
        created_at__lt=start_of_tomorrow
      ).aggregate(total=Sum("amount"))["total"] or 0,

      "Last 7 Days": qs.filter(
        created_at__gte=week_start,
        created_at__lt=start_of_tomorrow
      ).aggregate(total=Sum("amount"))["total"] or 0,

      "This Month": qs.filter(
        created_at__gte=month_start,
        created_at__lt=start_of_tomorrow
      ).aggregate(total=Sum("amount"))["total"] or 0,
    }

    methods = {
        "Coin Donations":  (
            qs.filter(method="coin")
              .aggregate(Sum("amount"))["amount__sum"] or 0,
            "bi-coin"
        ),
        "GCash Donations": (
            qs.filter(method="gcash")
              .aggregate(Sum("amount"))["amount__sum"] or 0,
            "bi-wallet2"
        ),
    }

    summary_stats = [
        {"label": label, "value": value}
        for label, value in totals.items()
    ]
    method_stats = [
        {"label": label, "value": value, "icon": icon}
        for label, (value, icon) in methods.items()
    ]

    return render(request, "web/donor/dashboard.html", {
        "summary_stats": summary_stats,
        "method_stats":  method_stats,
        "is_flex": True,
        "content_navbar": True,
        "is_navbar": True,
        "is_menu": False,
        "is_footer": True,
        "navbar_detached": True,
        "layout_path" : "layout/layout_vertical.html"
    })

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
        email = data.get("email", "")
        password = data.get("password")
        confirm_pw = data.get("confirm_password")

        # 1) basic match check
        if password != confirm_pw:
          messages.error(request, "Passwords do not match.")
          return redirect(reverse("web_donor_register"))

        # 2) explicit uniqueness checks
        if not username:
          messages.error(request, "Username is required.")
          return redirect(reverse("web_donor_register"))
        if User.objects.filter(username=username).exists():
          messages.error(request, "That username is already taken.")
          return redirect(reverse("web_donor_register"))
        if email:
          # your Profile model enforces unique email
          if Profile.objects.filter(email=email).exists():
            messages.error(request, "That email is already in use.")
            return redirect(reverse("web_donor_register"))

        # 3) collect the rest of the fields
        phone = data.get("phone", "").strip()
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        face_photo = request.FILES.get("face_photo")

        # 4) attempt creation
        try:
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
          return redirect(reverse("web_donor_dashboard"))

        except IntegrityError as e:
          messages.error(request, "Username or email already exists.")
          return redirect(reverse("web_donor_register"))
        except Exception as e:
          messages.error(request, f"Registration failed: {str(e)}")
          return redirect(reverse("web_donor_register"))

class DonorWebLoginView(View):
    def get(self, request):
        if request.user.is_authenticated and getattr(request.user, "role", None) == "donor":
            return redirect(reverse("web_donor_dashboard"))
        elif request.user.is_authenticated and getattr(request.user, "role", None) == "admin":
            return redirect(reverse("admin_dashboard"))
        elif request.user.is_authenticated and getattr(request.user, "role", None) == "beneficiary":
            return redirect(reverse("web_beneficiary_dashboard"))
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
        return redirect(reverse("web_donor_dashboard"))

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

# -----------------------------------------------------------------------------
# 3. BENEFICIARY KIOSK VIEWS (unchanged)
# -----------------------------------------------------------------------------
class KioskBeneficiaryView(View):
  def get(self, request):
    return render(request, "kiosk/beneficiary/beneficiary.html", {
      "layout_path": "layout/layout_blank.html"
    })

@method_decorator(csrf_exempt, name="dispatch")
class KioskBeneficiaryFacialRecogView(View):
    def post(self, request):
        verification_photo = request.FILES.get("photo")
        if not verification_photo:
          return JsonResponse({"error": "No photo uploaded."}, status=400)

        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            for chunk in verification_photo.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        # Load & normalize uploaded image
        try:
            pil_img = Image.open(temp_file_path).convert("RGB")
            uploaded_image = np.array(pil_img, dtype=np.uint8)
            encodings = face_recognition.face_encodings(uploaded_image)
            if not encodings:
              return JsonResponse({"error": "No face detected"}, status=400)

            uploaded_encoding = encodings[0]
        except IndexError:
            return JsonResponse({"error": "No face found in uploaded photo."}, status=400)
        except Exception as e:
            return JsonResponse({"error": f"Invalid image: {str(e)}"}, status=400)

        # Try matching against registered beneficiaries
        beneficiaries = User.objects.filter(role="beneficiary")
        for beneficiary in beneficiaries:
          # Query registration photos from UserPhoto
          registration_photos = beneficiary.photos.filter(photo_type="registration")
          for user_photo in registration_photos:
            try:
              reg_pil = Image.open(user_photo.photo.path).convert("RGB")
              registered_image = np.array(reg_pil, dtype=np.uint8)
              registered_encodings = face_recognition.face_encodings(registered_image)
              if not registered_encodings:
                continue  # skip photos without faces

              registered_encoding = registered_encodings[0]
            except (IndexError, AttributeError, FileNotFoundError):
              continue  # skip invalid photos

            if face_recognition.compare_faces([registered_encoding], uploaded_encoding)[0]:
              # Instead of logging in & redirecting, just send back beneficiary info
              return JsonResponse({
                "success": True,
                "beneficiary_id": beneficiary.id,
                "first_name": beneficiary.first_name,
              })

        return JsonResponse({"error": "No matching account found."}, status=400)

@method_decorator(csrf_exempt, name="dispatch")
class KioskBeneficiaryLoginView(View):
    def post(self, request):
        try:
          body = json.loads(request.body)
          username = body["username"].strip()
          password = body["password"]
        except (KeyError, json.JSONDecodeError):
          return JsonResponse({"error": "Invalid JSON."}, status=400)

        user = authenticate(request, username=username, password=password)
        if user is None or user.role != "beneficiary":
          return JsonResponse({"error": "Incorrect username/password."}, status=401)

        # DON’T call Django’s login()—we’re stateless here
        return JsonResponse({
          "success": True,
          "beneficiary_id": user.id,
          "first_name": user.first_name
        })

@method_decorator(csrf_exempt, name="dispatch")
class KioskBeneficiarySubmitClaimView(View):
    def post(self, request):
        # 1) parse JSON
        try:
            payload = json.loads(request.body)
            beneficiary_id    = int(payload["beneficiary_id"])
            need_type         = payload["need_type"]
            requested_amount  = float(payload["requested_amount"])
        except (KeyError, ValueError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid request payload."}, status=400)

        # 2) validate amount
        if requested_amount < 1:
            return JsonResponse(
                {"error": "Please enter an amount of at least ₱1."},
                status=400
            )

        # 3) ensure user exists and is a beneficiary
        user = get_object_or_404(User, pk=beneficiary_id, role="beneficiary")

        # 4) create the claim
        try:
            claim = create_claim(
                user_id=beneficiary_id,
                need_type=need_type,
                requested_amount=requested_amount,
            )
        except Exception:
            return JsonResponse(
                {"error": "Unable to create claim. Please try again."},
                status=500
            )

        # 5) success → pending
        return JsonResponse({
            "status": "pending",
            "claim_id": claim.id
        }, status=200)
# -----------------------------------------------------------------------------
# 4. BENEFICIARY WEB PORTAL VIEWS (unchanged)
# -----------------------------------------------------------------------------
class BeneficiaryWebRegisterView(View):
  def get(self, request):
    # no change here
    return render(request, "web/beneficiary/register.html", {
      "layout_path": "layout/layout_blank.html"
    })

  def post(self, request):
    data = request.POST
    idnumber = data.get("idnumber", "").strip()
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    confirm_pw = data.get("confirm_password", "")

    # 1) basic match check
    if password != confirm_pw:
      messages.error(request, "Passwords do not match.")
      return redirect(reverse("web_beneficiary_register"))

    # 2) explicit uniqueness checks
    if not username:
      messages.error(request, "Username is required.")
      return redirect(reverse("web_beneficiary_register"))
    if User.objects.filter(username=username).exists():
      messages.error(request, "That username is already taken.")
      return redirect(reverse("web_beneficiary_register"))
    if idnumber and User.objects.filter(idnumber=idnumber).exists():
      messages.error(request, "That ID number is already registered.")
      return redirect(reverse("web_beneficiary_register"))
    if email:
      # your Profile model enforces unique email
      if Profile.objects.filter(email=email).exists():
        messages.error(request, "That email is already in use.")
        return redirect(reverse("web_beneficiary_register"))

    # 3) collect the rest of the fields
    phone = data.get("phone", "").strip()
    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    face_photo = request.FILES.get("face_photo")

    # -- New check: require face photo --
    if face_photo is None:
      messages.error(request, "Please upload or capture a face photo.")
      return redirect(reverse("web_beneficiary_register"))

    # 4) attempt creation
    try:
      beneficiary = create_beneficiary(
        idnumber=idnumber,
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

    except ValidationError as ve:
      messages.error(request, ve.message)
    except IntegrityError:
      messages.error(request,
                     "An account with that username, ID number or email already exists.")
    except Exception as e:
      messages.error(request, f"Registration failed: {str(e)}")

    return redirect(reverse("web_beneficiary_register"))

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
        # all claims for this beneficiary
        qs = Claim.objects.filter(user=beneficiary)

        # aggregate basic counts
        totals = qs.aggregate(
            total_claims=Count("id"),
            pending_claims=Count("id", filter=Q(status="pending")),
            approved_claims=Count("id", filter=Q(status="approved")),
            rejected_claims=Count("id", filter=Q(status="rejected")),
            total_requested=Sum("requested_amount"),
            total_approved=Sum("requested_amount", filter=Q(status="approved")),
        )

        # optional: breakdown by need type
        needs = qs.values("need_type").annotate(
          total_count=Count("id"),
          total_amount=Sum("requested_amount"),
          approved_count=Count("id", filter=Q(status="approved")),
          approved_amount=Sum("requested_amount", filter=Q(status="approved")),
          rejected_count=Count("id", filter=Q(status="rejected")),
          rejected_amount=Sum("requested_amount", filter=Q(status="rejected")),
          pending_count=Count("id", filter=Q(status="pending")),
          pending_amount=Sum("requested_amount", filter=Q(status="pending")),
        )

        # build summary cards
        summary_stats = [
          {"label": "Total Claims", "value": totals["total_claims"] or 0},
          {"label": "Pending Claims", "value": totals["pending_claims"] or 0},
          {"label": "Approved Claims", "value": totals["approved_claims"] or 0},
          {"label": "Rejected Claims", "value": totals["rejected_claims"] or 0},
          {"label": "Total Requested (₱)", "value": totals["total_requested"] or 0},
          {"label": "Total Approved and Received (₱)", "value": totals["total_approved"] or 0},
        ]

        # build method (need-type) cards
        method_stats = []
        ICON_MAP = {
          "food": "bi-cup-straw",
          "school_supplies": "bi-book",
          "transport": "bi-bus-front",
          "rent": "bi-house",
        }
        for n in needs:
          method_stats.append({
            "label": n["need_type"].replace("_", " ").title(),
            "icon": ICON_MAP.get(n["need_type"], "bi-tag"),
            "total": {
              "count": n["total_count"] or 0,
              "amount": n["total_amount"] or 0,
            },
            "approved": {
              "count": n["approved_count"] or 0,
              "amount": n["approved_amount"] or 0,
            },
            "rejected": {
              "count": n["rejected_count"] or 0,
              "amount": n["rejected_amount"] or 0,
            },
            "pending": {
              "count": n["pending_count"] or 0,
              "amount": n["pending_amount"] or 0,
            },
          })

        return render(request, "web/beneficiary/dashboard.html", {
          "balance": beneficiary.current_balance,
          "claims": qs,
          "summary_stats": summary_stats,
          "method_stats": method_stats,
          "is_flex": True,
          "content_navbar": True,
          "is_navbar": True,
          "is_menu": False,
          "is_footer": True,
          "navbar_detached": True,
          "layout_path": "layout/layout_vertical.html",
        })

@method_decorator([login_required, csrf_exempt], name="dispatch")
class BeneficiaryFaceVerifyView(View):
    def post(self, request):
        photo = request.FILES.get("photo")
        if not photo:
            return JsonResponse({"error": "Photo required"}, status=400)

        # Save upload to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            for chunk in photo.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        # Load & encode
        try:
            img = Image.open(tmp_path).convert("RGB")
            arr = np.array(img)
            encs = face_recognition.face_encodings(arr)
            if not encs:
                return JsonResponse({"error": "No face detected"}, status=400)
            uploaded = encs[0]
        except Exception as e:
            return JsonResponse({"error": f"Invalid image: {e}"}, status=400)

        # Compare against this user’s registration photos
        user = request.user
        for up in user.photos.filter(photo_type="registration"):
            try:
                reg_img = Image.open(up.photo.path).convert("RGB")
                reg_arr = np.array(reg_img)
                reg_encs = face_recognition.face_encodings(reg_arr)
                if reg_encs and face_recognition.compare_faces([reg_encs[0]], uploaded)[0]:
                    return JsonResponse({"success": True})
            except Exception:
                continue

        return JsonResponse({"error": "Face did not match"}, status=400)

@method_decorator(csrf_exempt, name="dispatch")
class BeneficiaryWebNewRequestView(View):
  def post(self, request):
    """
    Expects multipart/form-data with:
      - need_type
      - requested_amount
      - willing_partial (“on” if checked)
      - purpose_of_travel (opt)
      - landlord_gcash_number (opt)
      - proof_of_need (file, required for non-food)
    """
    # 1. Read simple fields from POST
    need_type = request.POST.get("need_type")
    amt = request.POST.get("requested_amount")
    try:
      requested_amount = float(amt)
    except (TypeError, ValueError):
      return JsonResponse({"error": "Invalid amount"}, status=400)

    # 2. Read the extra enhancements
    willing_partial = request.POST.get("willing_partial") == "on"
    purpose_of_travel = request.POST.get("purpose_of_travel") or None
    landlord_gcash_number = request.POST.get("landlord_gcash_number") or None
    proof_file = request.FILES.get("proof_of_need")

    # 3. Call your CRUD function (which invokes full_clean())
    try:
      create_claim(
        user_id=request.user.id,
        need_type=need_type,
        requested_amount=requested_amount,
        willing_partial=willing_partial,
        purpose_of_travel=purpose_of_travel,
        landlord_gcash_number=landlord_gcash_number,
        proof_file=proof_file,
      )
    except ValidationError as e:
      # Extract first error message
      if hasattr(e, "message_dict"):
        # field errors
        msg = next(iter(e.message_dict.values()))[0]
      else:
        # non-field error
        msg = e.messages[0]
      return JsonResponse({"error": msg}, status=400)
    except ValueError as e:
      # e.g. wrong role or other ValueError from crud
      return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"success": True})


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
    # midnight today in local time
    now = timezone.localtime(timezone.now())
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_tomorrow = start_of_today + datetime.timedelta(days=1)

    week_start = start_of_today - datetime.timedelta(days=7)
    month_start = start_of_today.replace(day=1)

    period_defs = [
        # explicit datetime ranges instead of __date
        (
            "today",
            "Today",
            Q(created_at__gte=start_of_today, created_at__lt=start_of_tomorrow),
        ),
        (
            "week",
            "Last 7 Days",
            Q(created_at__gte=week_start, created_at__lt=start_of_tomorrow),
        ),
        (
            "month",
            "This Month",
            Q(created_at__gte=month_start, created_at__lt=start_of_tomorrow),
        ),
    ]
    period_stats = []
    for key, label, filt in period_defs:
        base_qs = Donation.objects.filter(filt)
        total_amount = base_qs.aggregate(total=Sum("amount"))["total"] or 0
        total_count = base_qs.count()
        pending_count = base_qs.filter(status="pending").count()
        confirmed_count = base_qs.filter(status="confirmed").count()

        period_stats.append({
            "key": key,
            "label": label,
            "count": total_count,
            "amount": total_amount,
            "pending_count": pending_count,
            "confirmed_count": confirmed_count,
        })

    # ─── 2) Donation stats by method ───
    method_defs = [
        ("coin", "Coin", "bi-coin"),
        ("gcash", "GCash", "bi-phone"),
    ]
    method_stats = []
    for key, label, icon in method_defs:
        qs = Donation.objects.filter(method=key)
        method_stats.append({
            "key": key,
            "label": label,
            "icon": icon,
            "count": qs.count(),
            "amount": qs.aggregate(total=Sum("amount"))["total"] or 0,
        })

    # ─── 3) Pending claims ───
    pending_qs = Claim.objects.filter(status="pending")
    pending_claims = {
        "count": pending_qs.count(),
        "amount": pending_qs.aggregate(total=Sum("requested_amount"))["total"] or 0,
    }

    # ─── 4) Needs breakdown (unchanged) ───
    needs_qs = Claim.objects.values("need_type").annotate(
        total_count=Count("id"),
        total_amount=Sum("requested_amount"),
        approved_count=Count("id", filter=Q(status="approved")),
        approved_amount=Sum("requested_amount", filter=Q(status="approved")),
        rejected_count=Count("id", filter=Q(status="rejected")),
        rejected_amount=Sum("requested_amount", filter=Q(status="rejected")),
        pending_count=Count("id", filter=Q(status="pending")),
        pending_amount=Sum("requested_amount", filter=Q(status="pending")),
    )
    LABELS = dict(Claim.NEED_CHOICES)
    status_defs = [
        ("total", "Total", "muted"),
        ("approved", "Approved", "success"),
        ("rejected", "Rejected", "danger"),
        ("pending", "Pending", "warning"),
    ]

    need_stats = []
    for n in needs_qs:
        nt = n["need_type"]
        breakdown = []
        for key, label, color in status_defs:
            breakdown.append({
                "status": label,
                "count": n[f"{key}_count"],
                "amount": n[f"{key}_amount"] or 0,
                "color": color,
            })
        need_stats.append({
            "label": LABELS[nt],
            "breakdown": breakdown,
        })

    # ─── 5) Coin box ───
    coin_box = get_coin_box_status()
    fill_pct = (coin_box.current_count / coin_box.capacity) * 100
    fill_color = "danger" if fill_pct >= 90 else "warning" if fill_pct >= 70 else "success"

    menu_data = json.load(menu_file_path.open()) if menu_file_path.exists() else []

    system_balance = get_system_balance()
    total_disbursed = get_system_disbursed()

    return render(request, "admin/dashboard.html", {
        "period_stats": period_stats,
        "method_stats": method_stats,
        "pending_claims": pending_claims,
        "need_stats": need_stats,
        "coin_box": coin_box,
        "fill_percent": round(fill_pct),
        "fill_color": fill_color,

        # system balance
        "system_balance": system_balance,
        "total_disbursed": total_disbursed,

        # layout flags
        "is_flex": True,
        "content_navbar": True,
        "is_navbar": True,
        "is_menu": True,
        "is_footer": True,
        "navbar_detached": True,
        "menu_data": menu_data,
        "layout_path": "layout/layout_vertical.html",
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

@csrf_exempt
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

@csrf_exempt
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


@csrf_exempt
@login_required
@user_passes_test(is_admin)
def admin_beneficiaries_update(request, beneficiaryId):
    """
    GET: Return JSON with the donor's current data (first_name, last_name, email, phone).
    POST: Update those fields. Return {"success": true} on success.
    """
    beneficiary = get_object_or_404(User, id=beneficiaryId, role="beneficiary")

    if request.method == "GET":
        data = {
            "idnumber": beneficiary.idnumber,
            "first_name": beneficiary.first_name,
            "last_name": beneficiary.last_name,
            "email": beneficiary.email,
            "phone": beneficiary.phone or "",
        }
        return JsonResponse(data)

    elif request.method == "POST":
        idnumber = request.POST.get("idnumber", "").strip()
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

        beneficiary.idnumber = idnumber
        beneficiary.first_name = first_name
        beneficiary.last_name = last_name
        beneficiary.email = email
        beneficiary.phone = phone
        if password:
          if password != confirm_pw:
            return JsonResponse({"error": "Passwords do not match."}, status=400)
          beneficiary.set_password(password)
        beneficiary.save()

        return JsonResponse({"success": True})

    else:
        return HttpResponseBadRequest("Invalid method.")

@csrf_exempt
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

@csrf_exempt
@login_required
@user_passes_test(is_admin)
def admin_donations_log(request):
    method = request.GET.get("method")
    status = request.GET.get("status")
    donations = list_all_donations(method=method, status=status)

    menu_data = json.load(menu_file_path.open()) if menu_file_path.exists() else []
    return render(request, "admin/donations_log.html", {
        "donations": donations,
        "is_flex": True,
        "content_navbar": True,
        "is_navbar": True,
        "is_menu": True,
        "is_footer": True,
        "navbar_detached": True,
        "menu_data": menu_data,
        "layout_path": "layout/layout_vertical.html"
    })


@csrf_exempt
@login_required
@user_passes_test(is_admin)
def admin_donation_action(request, donation_id):
  if request.method != "POST":
    return HttpResponseBadRequest("Invalid request method.")

  donation = get_object_or_404(Donation, id=donation_id)
  if donation.status != "pending":
    return JsonResponse({"error": "Donation is not pending."}, status=400)

  action = request.POST.get("action")
  reason = request.POST.get("reason", "").strip()

  if action == "approve":
    try:
      update_donation_status(
        donation_id=donation.id,
        new_status="confirmed",
        admin_user_id=request.user.id,
      )
    except Exception as e:
      return JsonResponse({"error": str(e)}, status=400)

  elif action == "reject":
    if not reason:
      return JsonResponse({"error": "Rejection reason required."}, status=400)
    try:
      update_donation_status(
        donation_id=donation.id,
        new_status="rejected",
        admin_user_id=request.user.id,
        notes=reason,
      )
    except Exception as e:
      return JsonResponse({"error": str(e)}, status=400)

  else:
    return JsonResponse({"error": "Invalid action."}, status=400)

  return JsonResponse({
    "success": True
  })

@csrf_exempt
@login_required
@user_passes_test(is_admin)
def admin_claims_log(request):
    """
    Renders the Claims Log page with all claims.
    Mirrors the donors-log view: server-renders a table,
    DataTable features are added in JS.
    """
    need_type = request.GET.get("need_type")
    status = request.GET.get("status")
    claims = list_all_claims(need_type=need_type, status=status)

    menu_data = json.load(menu_file_path.open()) if menu_file_path.exists() else []
    return render(request, "admin/claims_log.html", {
          "claims": claims,
          "is_flex": True,
          "content_navbar": True,
          "is_navbar": True,
          "is_menu": True,
          "is_footer": True,
          "navbar_detached": True,
          "menu_data": menu_data,
          "layout_path": "layout/layout_vertical.html"
    })

@csrf_exempt
@login_required
@user_passes_test(is_admin)
def admin_claim_action(request, claim_id):
  """
  AJAX endpoint to approve or reject a pending claim.
  """
  claim = get_object_or_404(Claim, id=claim_id)
  if claim.status != "pending":
    return HttpResponseBadRequest("Claim not pending.")

  action = request.POST.get("action")

  if action == "approve":
    ref = request.POST.get("gcash_payout_id", "").strip()
    amount_str = request.POST.get("approved_amount", "").strip()
    if not ref:
      return JsonResponse({"error": "Reference number required."}, status=400)
    # Pass the reference number into your service
    try:
      approved_amount = Decimal(amount_str) if amount_str else None
      update_claim_status(
        claim_id=claim_id,
        new_status="approved",
        admin_user_id=request.user.id,
        gcash_payout_id=ref,
        amount=approved_amount,
      )
    except Exception as e:
      return JsonResponse({"error": str(e)}, status=400)

  elif action == "reject":
    reason = request.POST.get("reason", "").strip()
    if not reason:
      return JsonResponse({"error": "Rejection reason required."}, status=400)
    try:
      update_claim_status(
        claim_id=claim_id,
        new_status="rejected",
        admin_user_id=request.user.id,
        reason=reason
      )
    except Exception as e:
      return JsonResponse({"error": str(e)}, status=400)

  else:
    return HttpResponseBadRequest("Invalid action.")

  return JsonResponse({"success": True})


@login_required
@user_passes_test(is_admin)
@method_decorator(csrf_exempt, name="dispatch")
def admin_coin_box_page(request):
    coin_box = get_coin_box_status()
    alert = coin_box.current_count >= 0.75 * coin_box.capacity
    return render(request, "admin/coin_box.html", {
        "coin_box": coin_box,
        "alert": alert,
    })


@login_required
@user_passes_test(is_admin)
@method_decorator(csrf_exempt, name="dispatch")
def admin_coin_box_reset(request):
    if request.method == "POST":
        reset_coin_box(admin_user_id=request.user.id)
    return JsonResponse({"success": True})


@login_required
@user_passes_test(is_admin)
@method_decorator(csrf_exempt, name="dispatch")
def admin_reports_page(request):
    return render(request, "admin/reports.html")


@login_required
@user_passes_test(is_admin)
@method_decorator(csrf_exempt, name="dispatch")
def admin_settings_page(request):
    admins = list_all_admins()
    coin_box = get_coin_box_status()
    return render(request, "admin/settings.html", {
        "admins": admins,
        "coin_box_capacity": coin_box.capacity,
    })


@login_required
@user_passes_test(is_admin)
@method_decorator(csrf_exempt, name="dispatch")
def admin_audit_logs_page(request):
    logs = list_audit_logs()
    return render(request, "admin/audit_logs.html", {"logs": logs})
