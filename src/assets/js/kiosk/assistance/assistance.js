document.addEventListener('DOMContentLoaded', () => {
  let currentBeneficiaryId = null;
  let currentFirstName = '';
  let currentNeedType = '';

  const authModalEl = document.getElementById('authModal');
  const faceScanSection = document.getElementById('faceScanSection');
  const loginSection = document.getElementById('loginSection');
  const faceCaptureContainer = document.getElementById('faceCaptureContainer');
  const faceVideo = document.getElementById('faceVideo');
  const faceCaptureError = document.getElementById('faceCaptureError');
  const btnShowFaceScan = document.getElementById('btnShowFaceScan');
  const btnCaptureFace = document.getElementById('btnCaptureFace');
  const btnRetryFace = document.getElementById('btnRetryFace');
  const btnLoginInstead = document.getElementById('btnLoginInstead');

  const loginUsername = document.getElementById('loginUsername');
  const loginPassword = document.getElementById('loginPassword');
  const btnLoginSubmit = document.getElementById('btnLoginSubmit');
  const loginError = document.getElementById('loginError');
  const btnBackToWelcome = document.getElementById('btnBackToWelcome');

  const needButtons = document.querySelectorAll('.need-btn');
  const beneficiaryFirstNameEl = document.getElementById('beneficiaryFirstName');
  const selectedNeedLabel = document.getElementById('selectedNeedLabel');

  const requestedAmount = document.getElementById('requestedAmount');
  const btnSubmitRequest = document.getElementById('btnSubmitRequest');

  const btnFinishPaid = document.getElementById('btnFinishPaid');
  const btnViewClaimStatusPaid = document.getElementById('btnViewClaimStatusPaid');
  const btnFinishPending = document.getElementById('btnFinishPending');

  let triggerMode = null; // "face" or "login"

  /* ---------------------------------------------------------
       Main Buttons → Set triggerMode & then show authModal
     --------------------------------------------------------- */
  document.getElementById('btnMainFaceScan').addEventListener('click', () => {
    triggerMode = 'face';
    // Now that triggerMode is set, show the modal:
    bootstrap.Modal.getOrCreateInstance(authModalEl).show();
  });

  document.getElementById('btnMainLogin').addEventListener('click', () => {
    triggerMode = 'login';
    bootstrap.Modal.getOrCreateInstance(authModalEl).show();
  });

  /* ---------------------------------------------------------
       When authModal is about to be shown → toggle sections
     --------------------------------------------------------- */
  authModalEl.addEventListener('show.bs.modal', () => {
    if (triggerMode === 'face') {
      faceScanSection.classList.remove('d-none');
      loginSection.classList.add('d-none');
    } else if (triggerMode === 'login') {
      faceScanSection.classList.add('d-none');
      loginSection.classList.remove('d-none');
    }
    // Reset any prior error messages & hide camera container
    faceCaptureError.style.display = 'none';
    loginError.style.display = 'none';
    faceCaptureContainer.classList.add('d-none');
    loginUsername.value = '';
    loginPassword.value = '';
    btnLoginSubmit.disabled = true;
  });

  /* ---------------------------------------------------------
       Authentication Modal Logic
     --------------------------------------------------------- */
  // 1. “Scan Face” button inside authModal → show camera preview
  btnShowFaceScan.addEventListener('click', () => {
    faceCaptureError.style.display = 'none';
    faceCaptureContainer.classList.remove('d-none');

    navigator.mediaDevices
      .getUserMedia({ video: true })
      .then(stream => {
        faceVideo.srcObject = stream;
      })
      .catch(e => {
        faceCaptureError.innerText = 'Cannot access camera.';
        faceCaptureError.style.display = 'block';
      });
  });

  btnRetryFace.addEventListener('click', () => {
    faceCaptureError.style.display = 'none';
    // Keep camera open
  });

  btnLoginInstead.addEventListener('click', () => {
    faceCaptureContainer.classList.add('d-none');
    loginSection.classList.remove('d-none');
  });

  btnCaptureFace.addEventListener('click', () => {
    const canvas = document.createElement('canvas');
    canvas.width = faceVideo.videoWidth;
    canvas.height = faceVideo.videoHeight;
    canvas.getContext('2d').drawImage(faceVideo, 0, 0);

    canvas.toBlob(blob => {
      // ─── DEMO: STUBBED FACE-MATCH ─────────────────────────────────────────────
      currentBeneficiaryId = 123;
      currentFirstName = 'Juan';
      beneficiaryFirstNameEl.innerText = currentFirstName;

      // Stop camera preview
      const tracks = faceVideo.srcObject.getTracks();
      tracks.forEach(t => t.stop());

      // Close authModal → open needSelectionModal
      bootstrap.Modal.getInstance(authModalEl).hide();
      bootstrap.Modal.getOrCreateInstance(document.getElementById('needSelectionModal')).show();
      // ──────────────────────────────────────────────────────────────────────────
      //
      // // REAL IMPLEMENTATION:
      // const formData = new FormData();
      // formData.append('image', blob, 'capture.png');
      // fetch('/api/face-match/', {
      //   method: 'POST',
      //   body: formData
      // })
      //   .then(res => res.json())
      //   .then(data => {
      //     if (data.match && data.score >= 0.8) {
      //       currentBeneficiaryId = data.beneficiary_id;
      //       currentFirstName = data.first_name;
      //       beneficiaryFirstNameEl.innerText = currentFirstName;
      //       faceVideo.srcObject.getTracks().forEach(t => t.stop());
      //       bootstrap.Modal.getInstance(authModalEl).hide();
      //       bootstrap.Modal.getOrCreateInstance(document.getElementById('needSelectionModal')).show();
      //     } else {
      //       faceCaptureError.style.display = 'block';
      //     }
      //   });
    });
  });

  /* ---------------------------------------------------------
       Login Form Validation & Submission
     --------------------------------------------------------- */
  [loginUsername, loginPassword].forEach(input => {
    input.addEventListener('input', () => {
      btnLoginSubmit.disabled = !(loginUsername.value && loginPassword.value);
    });
  });

  btnBackToWelcome.addEventListener('click', () => {
    bootstrap.Modal.getInstance(authModalEl).hide();
  });

  document.getElementById('loginForm').addEventListener('submit', e => {
    e.preventDefault();
    loginError.style.display = 'none';

    // ─── DEMO: STUBBED LOGIN ────────────────────────────────────────────────────
    currentBeneficiaryId = 123;
    currentFirstName = 'Juan';
    beneficiaryFirstNameEl.innerText = currentFirstName;

    bootstrap.Modal.getInstance(authModalEl).hide();
    bootstrap.Modal.getOrCreateInstance(document.getElementById('needSelectionModal')).show();
    // ──────────────────────────────────────────────────────────────────────────
    //
    // // REAL IMPLEMENTATION:
    // fetch('/api/login-beneficiary/', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({
    //     username: loginUsername.value,
    //     password: loginPassword.value
    //   })
    // })
    //   .then(res => res.json())
    //   .then(data => {
    //     if (data.success) {
    //       currentBeneficiaryId = data.beneficiary_id;
    //       currentFirstName = data.first_name;
    //       beneficiaryFirstNameEl.innerText = currentFirstName;
    //       bootstrap.Modal.getInstance(authModalEl).hide();
    //       bootstrap.Modal.getOrCreateInstance(document.getElementById('needSelectionModal')).show();
    //     } else {
    //       loginError.style.display = 'block';
    //     }
    //   });
  });

  /* ---------------------------------------------------------
       Need Selection Logic
     --------------------------------------------------------- */
  needButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      currentNeedType = btn.getAttribute('data-need');
      const mapping = {
        food: 'Food Assistance',
        school_supplies: 'School Supplies',
        transport: 'Transport',
        rent: 'Rent'
      };
      selectedNeedLabel.innerText = mapping[currentNeedType];
      bootstrap.Modal.getInstance(document.getElementById('needSelectionModal')).hide();
      bootstrap.Modal.getOrCreateInstance(document.getElementById('requestDetailsModal')).show();
    });
  });

  /* ---------------------------------------------------------
       Request Details Logic
     --------------------------------------------------------- */
  requestedAmount.addEventListener('input', () => {
    btnSubmitRequest.disabled = !(parseInt(requestedAmount.value) >= 1);
  });

  btnSubmitRequest.addEventListener('click', () => {
    const amount = parseInt(requestedAmount.value);
    const note = document.getElementById('optionalNote').value;

    // ─── DEMO: Simulate Claim Submission & Auto-Payout ───────────────────────
    bootstrap.Modal.getInstance(document.getElementById('requestDetailsModal')).hide();
    bootstrap.Modal.getOrCreateInstance(document.getElementById('processingModal')).show();

    setTimeout(() => {
      const autoPayoutEnabled = true;
      const fundsAvailable = true;

      if (autoPayoutEnabled && fundsAvailable) {
        const fakePayoutId = 'GCASH123456';
        document.getElementById('paidAmount').innerText = amount.toFixed(2);
        document.getElementById('gcashPayoutId').innerText = fakePayoutId;
        bootstrap.Modal.getInstance(document.getElementById('processingModal')).hide();
        bootstrap.Modal.getOrCreateInstance(document.getElementById('confirmationPaidModal')).show();
      } else {
        bootstrap.Modal.getInstance(document.getElementById('processingModal')).hide();
        bootstrap.Modal.getOrCreateInstance(document.getElementById('confirmationPendingModal')).show();
      }
    }, 3000);
    // ─────────────────────────────────────────────────────────────────────────
    //
    // // REAL IMPLEMENTATION:
    // fetch('/api/submit-claim/', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({
    //     beneficiary_id: currentBeneficiaryId,
    //     need_type: currentNeedType,
    //     requested_amount: amount,
    //     note: note
    //   })
    // })
    //   .then(res => res.json())
    //   .then(data => {
    //     if (data.success) {
    //       bootstrap.Modal.getInstance(document.getElementById('requestDetailsModal')).hide();
    //       bootstrap.Modal.getOrCreateInstance(document.getElementById('processingModal')).show();
    //       handleProcessing(data.claim_id, amount);
    //     }
    //   });
  });

  /* ---------------------------------------------------------
       Confirmation Buttons Logic
     --------------------------------------------------------- */
  btnFinishPaid.addEventListener('click', () => {
    bootstrap.Modal.getInstance(document.getElementById('confirmationPaidModal')).hide();
    resetAll();
  });
  btnViewClaimStatusPaid.addEventListener('click', () => {
    bootstrap.Modal.getInstance(document.getElementById('confirmationPaidModal')).hide();
    resetAll();
    // Optionally open a “Claim Status” modal
  });
  btnFinishPending.addEventListener('click', () => {
    bootstrap.Modal.getInstance(document.getElementById('confirmationPendingModal')).hide();
    resetAll();
  });

  /* ---------------------------------------------------------
       Utility: Reset Everything to Welcome State
     --------------------------------------------------------- */
  function resetAll() {
    currentBeneficiaryId = null;
    currentFirstName = '';
    currentNeedType = '';

    // Hide all active modals
    [
      'authModal',
      'needSelectionModal',
      'requestDetailsModal',
      'processingModal',
      'confirmationPaidModal',
      'confirmationPendingModal'
    ].forEach(id => {
      const m = document.getElementById(id);
      if (bootstrap.Modal.getInstance(m)) {
        bootstrap.Modal.getInstance(m).hide();
      }
    });

    // Reset authentication sections
    faceCaptureContainer.classList.add('d-none');
    faceCaptureError.style.display = 'none';
    loginSection.classList.add('d-none');
    loginError.style.display = 'none';
    loginUsername.value = '';
    loginPassword.value = '';
    btnLoginSubmit.disabled = true;

    // Reset greeting
    beneficiaryFirstNameEl.innerText = 'User';

    // Reset request details
    requestedAmount.value = '';
    document.getElementById('optionalNote').value = '';
    btnSubmitRequest.disabled = true;
  }
});
