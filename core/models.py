# core/models.py
import os
import uuid
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


# -----------------------------------------------------------------------------
# 1. SINGLE CUSTOM USER MODEL
# -----------------------------------------------------------------------------

class User(AbstractUser):
    """
    One single custom user. We distinguish roles via a 'role' field:
      - 'donor'
      - 'beneficiary'
      - 'admin'
    """
    ROLE_CHOICES = [
        ("donor", "Donor"),
        ("beneficiary", "Beneficiary"),
        ("admin", "Administrator"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    # Specific fields for Donor and Beneficiary:
    phone = models.CharField(max_length=20, blank=True, null=True)
    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        help_text="Only used if role='beneficiary'.",
    )

    # For 'admin' users, we might enable MFA:
    enable_mfa = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


# -----------------------------------------------------------------------------
# 2. USER PHOTOS (facial registration & verification)
# -----------------------------------------------------------------------------

def user_photo_upload_path(instance, filename):
  """
  Generate unique file name: firstname_lastname_UUID.ext
  """
  ext = os.path.splitext(filename)[1]  # Get file extension
  user = instance.user
  timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
  unique_id = uuid.uuid4().hex[:8]

  # Slugify to avoid spaces and unsafe chars
  first = slugify(user.first_name or "first")
  last = slugify(user.last_name or "last")

  new_filename = f"{first}_{last}_{timestamp}_{unique_id}{ext}"
  return os.path.join("uploads/img", new_filename)

class UserPhoto(models.Model):
    """
    Stores facial photos for any User (Donors or Beneficiaries).
    - photo_type: 'registration' or 'verification'
    """
    PHOTO_TYPE_CHOICES = [
        ("registration", "Registration"),
        ("verification", "Verification"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="photos"
    )
    photo = models.ImageField(upload_to=user_photo_upload_path)
    photo_type = models.CharField(max_length=20, choices=PHOTO_TYPE_CHOICES)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.photo_type} @ {self.uploaded_at}"


# -----------------------------------------------------------------------------
# 3. COIN BOX STATUS (singleton)
# -----------------------------------------------------------------------------

class CoinBoxStatus(models.Model):
    """
    Tracks current coin count in the kiosk.
    We assume exactly one row (id=1). Use get_or_create(id=1) to fetch it.
    """
    current_count = models.PositiveIntegerField(default=0)
    capacity = models.PositiveIntegerField(default=10000)

    def __str__(self):
        return f"CoinBox: {self.current_count} / {self.capacity}"


# -----------------------------------------------------------------------------
# 4. DONATIONS (coin or GCash)
# -----------------------------------------------------------------------------

class Donation(models.Model):
    """
    Records every donation (coin or GCash).
    - user: FK to User. If user is None, treat as 'guest donor'.
    - method: 'coin' or 'gcash'
    - amount: decimal
    - coin_count: integer (only if method='coin')
    - gcash_ref_number: text (only if method='gcash')
    - status: 'pending' or 'confirmed'
    - facial_verified: boolean
    - created_at: timestamp
    """
    METHOD_CHOICES = [
        ("coin", "Coin"),
        ("gcash", "GCash"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending Admin Approval"),
        ("confirmed", "Confirmed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="donations",
        help_text="If null → guest donor.",
    )
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    coin_count = models.PositiveIntegerField(null=True, blank=True)
    gcash_ref_number = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    facial_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        who = self.user.username if self.user else "Guest"
        return f"{who} donated ₱{self.amount} via {self.method} at {self.created_at}"


# -----------------------------------------------------------------------------
# 5. CLAIMS (beneficiary assistance requests)
# -----------------------------------------------------------------------------

class Claim(models.Model):
    """
    A request by a beneficiary (User with role='beneficiary') for assistance.
    - user → must have role='beneficiary'
    - need_type: 'food', 'school_supplies', 'transport', 'rent'
    - requested_amount: decimal
    - status: 'pending', 'approved', 'rejected', 'paid'
    - gcash_payout_id: payout reference if paid
    - admin_processed_by: foreign key to User with role='admin'
    - admin_decision_reason: optional text (e.g. rejection reason)
    - created_at, processed_at
    """
    NEED_CHOICES = [
        ("food", "Food Assistance"),
        ("school_supplies", "School Supplies"),
        ("transport", "Transport"),
        ("rent", "Rent"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("paid", "Paid"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="claims",
        help_text="Must have role='beneficiary'."
    )
    need_type = models.CharField(max_length=20, choices=NEED_CHOICES)
    requested_amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    gcash_payout_id = models.CharField(max_length=100, blank=True, null=True)
    admin_processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_claims",
        help_text="Must have role='admin'."
    )
    admin_decision_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Claim #{self.id} by {self.user.username} ({self.need_type}) – {self.status}"


# -----------------------------------------------------------------------------
# 6. AUDIT LOGS
# -----------------------------------------------------------------------------

class AuditLog(models.Model):
    """
    Logs admin actions on Donations and Claims (and coin box resets).
    - admin_user: FK to User with role='admin'
    - action: e.g. 'donation_confirmed', 'claim_approved', etc.
    - target_model: text name of the model (e.g. 'Donation')
    - target_id: primary key of that instance
    - timestamp
    - notes: optional
    """
    ACTION_CHOICES = [
        ("donation_confirmed", "Donation Confirmed"),
        ("donation_rejected", "Donation Rejected"),
        ("claim_approved", "Claim Approved"),
        ("claim_rejected", "Claim Rejected"),
        ("claim_paid", "Claim Paid"),
        ("coinbox_reset", "Coin Box Reset"),
    ]

    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
        help_text="User with role='admin'."
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    target_model = models.CharField(max_length=30)   # e.g. 'Donation', 'Claim', 'CoinBoxStatus'
    target_id = models.PositiveIntegerField()         # primary key of the target instance
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return (
            f"{self.admin_user.username} performed {self.action} "
            f"on {self.target_model} #{self.target_id} at {self.timestamp}"
        )
