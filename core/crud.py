# core/crud.py

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import (
  UserPhoto,
  CoinBoxStatus,
  Donation,
  Claim,
  AuditLog, SystemBalance,
)

from decimal import Decimal

User = get_user_model()


# -----------------------------------------------------------------------------
# 1. USER‐RELATED CRUD (Donor / Beneficiary / Admin all use User model)
# -----------------------------------------------------------------------------

def create_donor(
    username: str,
    password: str,
    email: str,
    first_name: str = "",
    last_name: str = "",
    phone: str = "",
    face_photo_file=None,
) -> User:
    """
    Create a new User with role='donor'. Optionally attach a registration photo.
    """

    try:
      with transaction.atomic():
          user = User.objects.create_user(
              username=username,
              password=password,
              email=email,
              first_name=first_name,
              last_name=last_name,
              role="donor",
          )
          user.phone = phone
          user.save()

          if face_photo_file:
              UserPhoto.objects.create(
                  user=user,
                  photo=face_photo_file,
                  photo_type="registration",
              )
          return user

    except IntegrityError as e:
      # wrap DB errors in a ValidationError so the view can treat them uniformly
      raise ValidationError("A user with your username, ID number, or email already exists.")


def create_beneficiary(
    idnumber: str,
    username: str,
    password: str,
    email: str,
    phone: str = "",
    first_name: str = "",
    last_name: str = "",
    face_photo_file=None,
) -> User:
    """
    Create a new User with role='beneficiary'. Optionally attach a registration photo.
    """
    try:
      with transaction.atomic():
        # You could re-check here too if you wanted...
        user = User.objects.create_user(
          idnumber=idnumber,
          username=username,
          password=password,
          email=email,
          phone=phone,
          first_name=first_name,
          last_name=last_name,
          role="beneficiary",
        )
        # profile gets auto-created via post_save signal
        if face_photo_file:
          UserPhoto.objects.create(
            user=user,
            photo=face_photo_file,
            photo_type="registration",
          )
        return user

    except IntegrityError as e:
      # wrap DB errors in a ValidationError so the view can treat them uniformly
      raise ValidationError("A user with your username, ID number, or email already exists.")


def create_admin_user(
    username: str,
    password: str,
    email: str,
    first_name: str = "",
    last_name: str = "",
    enable_mfa: bool = False,
) -> User:
    """
    Create a new superuser with role='admin'.
    """
    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role="admin",
        is_staff=True,
        is_superuser=True,
    )
    user.enable_mfa = enable_mfa
    user.save()
    return user


def get_user_by_id(user_id: int) -> User:
    return get_object_or_404(User, id=user_id)


def update_user(user_id: int, **kwargs) -> User:
    """
    Update any User fields. If changing password, caller should pass 'password'
    and this function will call set_password().
    """
    user = get_user_by_id(user_id)
    password = kwargs.pop("password", None)
    for field, value in kwargs.items():
        setattr(user, field, value)
    if password:
        user.set_password(password)
    user.save()
    return user


def delete_user(user_id: int):
    user = get_user_by_id(user_id)
    user.delete()


# -----------------------------------------------------------------------------
# 2. DONATION‐RELATED CRUD
# -----------------------------------------------------------------------------

def create_coin_donation(user_id: int = None, coin_count: int = 0) -> Donation:
    """
    Called at end of a coin insertion flow. Increments the CoinBoxStatus and
    creates a pending Donation of method='coin'.
    If user_id is None, this is a guest donation.
    """
    user = None
    if user_id:
        user = get_user_by_id(user_id)
        if user.role != "donor":
            raise ValueError("User is not a donor.")

    with transaction.atomic():
        # Ensure a single CoinBoxStatus row exists
        coin_box, _ = CoinBoxStatus.objects.get_or_create(id=1, defaults={"capacity": 10000})
        coin_box.current_count += coin_count
        coin_box.save()

        amount = coin_count * 1.00  # adjust conversion if needed
        donation = Donation.objects.create(
            user=user,
            method="coin",
            amount=amount,
            coin_count=coin_count,
            status="pending",
            facial_verified=False,
        )
        return donation


def create_gcash_donation(
    user_id: int = None, amount: float = 0.0, gcash_ref_number: str = ""
) -> Donation:
    """
    Create a new GCash donation. Status defaults to 'pending' until admin confirms.
    If user_id is None, treat as guest donor.
    """
    user = None
    if user_id:
        user = get_user_by_id(user_id)
        if user.role != "donor":
            raise ValueError("User is not a donor.")

    donation = Donation.objects.create(
        user=user,
        method="gcash",
        amount=amount,
        gcash_ref_number=gcash_ref_number,
        status="pending",
        facial_verified=False,
    )
    return donation


def get_donation_by_id(donation_id: int) -> Donation:
    return get_object_or_404(Donation, id=donation_id)


def update_donation_status(
    donation_id: int, new_status: str, admin_user_id: int, notes: str = ""
) -> Donation:
    """
    Approve or reject a pending donation. Logs an AuditLog entry.
    new_status must be 'confirmed' or 'pending' (or 'rejected' if extended).
    """
    donation = get_donation_by_id(donation_id)
    admin = get_user_by_id(admin_user_id)
    if admin.role != "admin":
        raise ValueError("User is not an admin.")

    if donation.status == "confirmed":
      raise ValueError("Donation is already confirmed.")

    donation.status = new_status
    donation.save()

    if new_status == "confirmed":
      system_balance, _ = SystemBalance.objects.get_or_create(id=1)
      system_balance.total_balance += donation.amount
      system_balance.save()
    if donation.amount == donation.coin_count:
      coin_box, _ = CoinBoxStatus.objects.get_or_create(id=1)
      coin_box.current_count = max(
        coin_box.current_count - donation.coin_count,
        0
      )
      coin_box.save()

    action = "donation_confirmed" if new_status == "confirmed" else "donation_rejected"
    AuditLog.objects.create(
      admin_user=admin,
      action=action,
      target_model="Donation",
      target_id=donation.id,
      notes=notes,
    )
    return donation


def verify_donation_facial(donation_id: int, verification_photo_file) -> Donation:
    """
    Save a 'verification' photo and mark facial_verified=True.
    In production, you'd do an actual face‐matching check; here, we assume match.
    """
    donation = get_donation_by_id(donation_id)
    user = donation.user
    if not user:
        raise ValueError("Cannot facial‐verify a guest donation.")
    if user.role != "donor":
        raise ValueError("User is not a donor.")

    UserPhoto.objects.create(
        user=user,
        photo=verification_photo_file,
        photo_type="verification",
    )
    donation.facial_verified = True
    donation.save()
    return donation


def list_all_donations(method: str = None, status: str = None):
    """
    Return a QuerySet of Donation objects, optionally filtered.
    """
    qs = Donation.objects.select_related('user')
    if method:
        qs = qs.filter(method=method)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")


def get_system_balance() -> SystemBalance:
  return SystemBalance.objects.get_or_create(id=1)[0]

def get_system_disbursed() -> SystemBalance:
  return SystemBalance.objects.get_or_create(id=1)[0].total_disbursed

# -----------------------------------------------------------------------------
# 3. CLAIM‐RELATED CRUD
# -----------------------------------------------------------------------------

def create_claim(user_id: int, need_type: str, requested_amount: float, willing_partial: bool = False, purpose_of_travel: str = None, landlord_gcash_number: str = None, proof_file=None,) -> Claim:
    """
    Create a new Claim with status='pending'. User must have role='beneficiary'.
    """
    user = get_user_by_id(user_id)
    if user.role != "beneficiary":
        raise ValueError("User is not a beneficiary.")

    # claim = Claim.objects.create(
    #     user=user,
    #     need_type=need_type,
    #     requested_amount=requested_amount,
    #     status="pending",
    # )
    # Build kwargs for the new Claim
    params = dict(
        user = user,
        need_type = need_type,
        requested_amount = requested_amount,
        willing_partial = willing_partial,
        purpose_of_travel = purpose_of_travel or "",
        landlord_gcash_number = landlord_gcash_number or "",
        status = "pending",
    )

    if proof_file:
        params["proof_of_need"] = proof_file

    claim = Claim(**params)
    # run model-level validations (two-week rule, required fields, proof)
    claim.full_clean()
    claim.save()
    print(">>> Claim saved with ID:", claim.id)
    return claim


def get_claim_by_id(claim_id: int) -> Claim:
    return get_object_or_404(Claim, id=claim_id)


def update_claim_status(
    claim_id: int,
    new_status: str,
    admin_user_id: int,
    reason: str = "",
    gcash_payout_id: str = None,
    amount: Decimal = None,
) -> Claim:
    claim = get_claim_by_id(claim_id)
    admin = get_user_by_id(admin_user_id)
    if admin.role != "admin":
        raise ValueError("User is not an admin.")

    if new_status == "approved":
        system_balance, _ = SystemBalance.objects.get_or_create(id=1)
        approved_amount = amount or claim.requested_amount  # Default to full
        if approved_amount > system_balance.total_balance:
          raise ValueError("Insufficient system balance for payout.")

        system_balance.total_balance -= approved_amount
        system_balance.total_disbursed += approved_amount
        system_balance.save()

        # Update beneficiary balance
        beneficiary = claim.user
        beneficiary.current_balance += claim.requested_amount
        beneficiary.save()

        if gcash_payout_id:
            claim.gcash_payout_id = gcash_payout_id

    claim.status = new_status
    claim.admin_processed_by = admin
    claim.admin_decision_reason = reason or ""
    claim.processed_at = timezone.now()
    claim.save()

    action_map = {
        "approved": "claim_approved",
        "rejected": "claim_rejected",
        "paid": "claim_paid",
    }
    action = action_map.get(new_status)
    if action:
        AuditLog.objects.create(
            admin_user=admin,
            action=action,
            target_model="Claim",
            target_id=claim.id,
            notes=reason,
        )
    return claim


def delete_claim(claim_id: int):
    claim = get_claim_by_id(claim_id)
    claim.delete()


def list_all_claims(need_type: str = None, status: str = None):
    """
    Return a QuerySet of Claim objects, optionally filtered.
    """
    qs = Claim.objects.select_related('user')
    if need_type:
        qs = qs.filter(need_type=need_type)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-priority", "-created_at")


# -----------------------------------------------------------------------------
# 4. ADMIN‐RELATED CRUD (CoinBoxStatus & AuditLog)
# -----------------------------------------------------------------------------

def get_coin_box_status() -> CoinBoxStatus:
    """
    Return (or create) the single CoinBoxStatus row.
    """
    coin_box, _ = CoinBoxStatus.objects.get_or_create(id=1, defaults={"capacity": 10000})
    return coin_box


def reset_coin_box(admin_user_id: int) -> CoinBoxStatus:
    """
    Reset current_count to 0 and log in AuditLog. Must be done by an admin.
    """
    admin = get_user_by_id(admin_user_id)
    if admin.role != "admin":
        raise ValueError("User is not an admin.")

    coin_box = get_coin_box_status()
    coin_box.current_count = 0
    coin_box.save()

    AuditLog.objects.create(
        admin_user=admin,
        action="coinbox_reset",
        target_model="CoinBoxStatus",
        target_id=coin_box.id,
        notes="Coin box emptied by admin.",
    )
    return coin_box


def list_all_donors():
    """
    Return a QuerySet of Users with role='donor'.
    """
    return User.objects.filter(role="donor")


def list_all_beneficiaries():
    """
    Return a QuerySet of Users with role='beneficiary'.
    """
    return User.objects.filter(role="beneficiary")


def list_all_admins():
    """
    Return a QuerySet of Users with role='admin'.
    """
    return User.objects.filter(role="admin")


def list_audit_logs():
    """
    Return all AuditLog entries, newest first.
    """
    return AuditLog.objects.all().order_by("-timestamp")
