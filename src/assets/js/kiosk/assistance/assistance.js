document.addEventListener('DOMContentLoaded', () => {
  let currentBeneficiaryId = null;
  let currentFirstName = '';
  let currentNeedType = '';

  // Modal instances
  const authModal = bootstrap.Modal.getOrCreateInstance(document.getElementById('authModal'));
  const needSelectionModal = bootstrap.Modal.getOrCreateInstance(document.getElementById('needSelectionModal'));
  const requestDetailsModal = bootstrap.Modal.getOrCreateInstance(document.getElementById('requestDetailsModal'));
  const processingModal = bootstrap.Modal.getOrCreateInstance(document.getElementById('processingModal'));
  const confirmationPaidModal = bootstrap.Modal.getOrCreateInstance(document.getElementById('confirmationPaidModal'));
  const confirmationPendingModal = bootstrap.Modal.getOrCreateInstance(
    document.getElementById('confirmationPendingModal')
  );

  const authModalEl = document.getElementById('authModal');
  const faceScanSection = document.getElementById('faceScanSection');
  const loginSection = document.getElementById('loginSection');
  const faceCaptureContainer = document.getElementById('faceCaptureContainer');
  const faceVideo = document.getElementById('faceVideo');
  const faceCaptureError = document.getElementById('faceCaptureError');
  const btnShowFaceScan = document.getElementById('btnShowFaceScan');
  const btnCaptureFace = document.getElementById('btnCaptureFace');
  const btnRetryFace = document.getElementById('btnRetryFace');

  const loginUsername = document.getElementById('loginUsername');
  const loginPassword = document.getElementById('loginPassword');
  const btnLoginSubmit = document.getElementById('btnLoginSubmit');
  const loginError = document.getElementById('loginError');

  const needButtons = document.querySelectorAll('.need-btn');
  const beneficiaryFirstNameEl = document.getElementById('beneficiaryFirstName');
  const selectedNeedLabel = document.getElementById('selectedNeedLabel');

  const requestedAmount = document.getElementById('requestedAmount');
  const btnSubmitRequest = document.getElementById('btnSubmitRequest');

  const btnFinishPaid = document.getElementById('btnFinishPaid');
  const btnViewClaimStatusPaid = document.getElementById('btnViewClaimStatusPaid');
  const btnFinishPending = document.getElementById('btnFinishPending');

  let triggerMode = null; // 'face' or 'login'

  /* ---------------------------------------------------------
       Camera Stream
     --------------------------------------------------------- */
  let cameraStream = null;
  function startCamera() {
    return navigator.mediaDevices
      .getUserMedia({ video: true })
      .then(stream => {
        cameraStream = stream;
        faceVideo.srcObject = stream;
        return faceVideo.play();
      })
      .catch(err => {
        console.error('Camera error', err);
        faceCaptureError.innerText = 'Cannot access camera.';
        faceCaptureError.style.display = 'block';
      });
  }
  function stopCamera() {
    if (cameraStream) {
      cameraStream.getTracks().forEach(t => t.stop());
      cameraStream = null;
    }
  }

  /* ---------------------------------------------------------
       Main Buttons
     --------------------------------------------------------- */
  document.getElementById('btnMainFaceScan').addEventListener('click', () => {
    triggerMode = 'face';
    authModal.show();
  });
  document.getElementById('btnMainLogin').addEventListener('click', () => {
    triggerMode = 'login';
    authModal.show();
  });

  /* ---------------------------------------------------------
       Toggle Auth Sections
     --------------------------------------------------------- */
  authModalEl.addEventListener('show.bs.modal', () => {
    faceCaptureError.style.display = 'none';
    loginError.style.display = 'none';
    faceCaptureContainer.classList.add('d-none');
    loginUsername.value = '';
    loginPassword.value = '';
    btnLoginSubmit.disabled = true;

    if (triggerMode === 'face') {
      faceScanSection.classList.remove('d-none');
      loginSection.classList.add('d-none');
    } else {
      faceScanSection.classList.add('d-none');
      loginSection.classList.remove('d-none');
    }
  });
  authModalEl.addEventListener('hidden.bs.modal', stopCamera);

  /* ---------------------------------------------------------
       Face Scan Logic
     --------------------------------------------------------- */
  btnShowFaceScan.addEventListener('click', () => {
    faceCaptureError.style.display = 'none';
    faceCaptureContainer.classList.remove('d-none');
    startCamera();
  });

  btnRetryFace.addEventListener('click', () => {
    faceCaptureError.style.display = 'none';
    const spinner = document.getElementById('faceMatchSpinner');
    if (spinner) spinner.style.display = 'none';
    stopCamera();
    startCamera();
  });

  btnCaptureFace.addEventListener('click', () => {
    function getCookie(name) {
      const v = document.cookie.split('; ').find(row => row.startsWith(name + '='));
      return v ? decodeURIComponent(v.split('=')[1]) : null;
    }
    const csrfToken = getCookie('csrftoken');
    faceCaptureError.style.display = 'none';
    const spinner = document.getElementById('faceMatchSpinner');
    if (spinner) spinner.style.display = 'block';

    // capture
    const canvas = document.createElement('canvas');
    canvas.width = faceVideo.videoWidth;
    canvas.height = faceVideo.videoHeight;
    canvas.getContext('2d').drawImage(faceVideo, 0, 0);
    canvas.toBlob(async blob => {
      stopCamera();
      const formData = new FormData();
      formData.append('photo', blob, 'capture.jpg');

      try {
        const res = await fetch('/kiosk/beneficiary/facial-recog/', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'X-CSRFToken': csrfToken },
          body: formData
        });
        if (spinner) spinner.style.display = 'none';
        const data = await res.json();
        if (data.success) {
          // store and proceed
          currentBeneficiaryId = data.beneficiary_id;
          currentFirstName = data.first_name;
          beneficiaryFirstNameEl.innerText = currentFirstName;
          authModal.hide();
          needSelectionModal.show();
        } else {
          faceCaptureError.innerText = data.error || 'Face not recognized.';
          faceCaptureError.style.display = 'block';
        }
      } catch (err) {
        if (spinner) spinner.style.display = 'none';
        faceCaptureError.innerText = 'Error processing photo.';
        faceCaptureError.style.display = 'block';
      }
    }, 'image/jpeg');
  });

  /* ---------------------------------------------------------
       Login Logic
     --------------------------------------------------------- */
  [loginUsername, loginPassword].forEach(inp =>
    inp.addEventListener('input', () => (btnLoginSubmit.disabled = !(loginUsername.value && loginPassword.value)))
  );
  document.getElementById('loginForm').addEventListener('submit', async e => {
    e.preventDefault();
    loginError.style.display = 'none';

    try {
      const res = await fetch('/kiosk/beneficiary/login/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          username: loginUsername.value.trim(),
          password: loginPassword.value
        })
      });

      if (!res.ok) {
        // show inline error
        loginError.style.display = 'block';
        return;
      }

      const data = await res.json();
      currentBeneficiaryId = data.beneficiary_id;
      currentFirstName = data.first_name;
      beneficiaryFirstNameEl.innerText = currentFirstName;

      authModal.hide();
      needSelectionModal.show();
    } catch {
      loginError.innerText = 'Network error, try again.';
      loginError.style.display = 'block';
    }
  });

  /* ---------------------------------------------------------
       Need Selection
     --------------------------------------------------------- */
  needButtons.forEach(btn =>
    btn.addEventListener('click', () => {
      currentNeedType = btn.getAttribute('data-need');
      const labels = {
        food: 'Food Assistance',
        school_supplies: 'School Supplies',
        transport: 'Transport',
        rent: 'Rent'
      };
      selectedNeedLabel.innerText = labels[currentNeedType];
      needSelectionModal.hide();
      requestDetailsModal.show();
    })
  );

  /* ---------------------------------------------------------
       Request Details
     --------------------------------------------------------- */
  requestedAmount.addEventListener(
    'input',
    () => (btnSubmitRequest.disabled = !(parseInt(requestedAmount.value) >= 1))
  );

  btnSubmitRequest.addEventListener('click', async () => {
    const amount = parseInt(requestedAmount.value);

    requestDetailsModal.hide();
    processingModal.show();

    try {
      const res = await fetch('/kiosk/beneficiary/submit-claim/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', credentials: 'same-origin' },
        body: JSON.stringify({
          beneficiary_id: currentBeneficiaryId,
          need_type: currentNeedType,
          requested_amount: amount
        })
      });

      processingModal.hide();
      if (!res.ok) {
        let errMsg = 'Unknown error.';

        try {
          const err = await res.json();
          errMsg = err.error || errMsg;
        } catch {}
        document.getElementById('errorMessage').innerText = errMsg;
        new bootstrap.Modal(document.getElementById('errorModal')).show();
        return;
      }

      confirmationPendingModal.show();
    } catch (err) {
      processingModal.hide();
      document.getElementById('errorMessage').innerText = 'Network error. Please try again.';
      new bootstrap.Modal(document.getElementById('errorModal')).show();
      needSelectionModal.show();
    }
  });

  /* ---------------------------------------------------------
       Confirmation Buttons & Reset
     --------------------------------------------------------- */
  const resetAll = () => {
    currentBeneficiaryId = null;
    currentFirstName = '';
    currentNeedType = '';
    [
      authModal,
      needSelectionModal,
      requestDetailsModal,
      processingModal,
      confirmationPaidModal,
      confirmationPendingModal
    ].forEach(m => m.hide());
    // reset UI
    beneficiaryFirstNameEl.innerText = 'User';
    faceCaptureContainer.classList.add('d-none');
    faceCaptureError.style.display = 'none';
    loginSection.classList.add('d-none');
    loginError.style.display = 'none';
    loginUsername.value = '';
    loginPassword.value = '';
    btnLoginSubmit.disabled = true;
    requestedAmount.value = '';
    document.getElementById('optionalNote').value = '';
    btnSubmitRequest.disabled = true;
    // restart face flow
    triggerMode = 'face';
    authModal.show();
  };

  btnFinishPaid.addEventListener('click', resetAll);
  btnViewClaimStatusPaid.addEventListener('click', resetAll);
  btnFinishPending.addEventListener('click', resetAll);
});
