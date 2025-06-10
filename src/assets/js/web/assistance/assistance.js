document.addEventListener('DOMContentLoaded', () => {
  let currentNeed = '';

  // Modals
  const faceModal = bootstrap.Modal.getOrCreateInstance('#authModal');
  const needModal = bootstrap.Modal.getOrCreateInstance('#needSelectionModal');
  const detailsModal = bootstrap.Modal.getOrCreateInstance('#requestDetailsModal');
  const processingModal = bootstrap.Modal.getOrCreateInstance('#processingModal');
  const pendingModal = bootstrap.Modal.getOrCreateInstance('#confirmationPendingModal');
  const errorModal = bootstrap.Modal.getOrCreateInstance('#errorModal');

  // DOM elements
  const fv = document.getElementById('faceVideo');
  const ferr = document.getElementById('faceCaptureError');
  const spinner = document.getElementById('faceMatchSpinner');
  const btnShow = document.getElementById('btnShowFaceScan');
  const btnCap = document.getElementById('btnCaptureFace');
  const btnRetry = document.getElementById('btnRetryFace');
  const needBtns = document.querySelectorAll('.need-btn');
  const lblNeed = document.getElementById('selectedNeedLabel');
  const amtInp = document.getElementById('requestedAmount');
  const btnSubmit = document.getElementById('btnSubmitRequest');
  const errMsg = document.getElementById('errorMessage');
  const btnFinishPending = document.getElementById('btnFinishPending');

  // Camera
  let camStream = null;
  async function startCam() {
    ferr.style.display = 'none';
    try {
      camStream = await navigator.mediaDevices.getUserMedia({ video: true });
      fv.srcObject = camStream;
      await fv.play();
    } catch {
      ferr.textContent = 'Cannot access camera.';
      ferr.style.display = 'block';
    }
  }
  function stopCam() {
    if (camStream) camStream.getTracks().forEach(t => t.stop());
  }

  // Reset to initial state & re-open face-scan
  function resetAll() {
    // hide any open modals
    [needModal, detailsModal, processingModal, pendingModal, errorModal].forEach(m => m.hide());
    // clear inputs
    amtInp.value = '';
    btnSubmit.disabled = true;
    // re-open face scan
    // faceModal.show();
  }

  // When face modal hides, stop camera
  document.getElementById('authModal').addEventListener('hidden.bs.modal', stopCam);

  // Show capture UI
  btnShow.addEventListener('click', () => {
    ferr.style.display = 'none';
    document.getElementById('faceCaptureContainer').classList.remove('d-none');
    startCam();
  });

  btnRetry.addEventListener('click', () => {
    ferr.style.display = 'none';
    spinner.style.display = 'none';
    stopCam();
    startCam();
  });

  // Capture & verify
  btnCap.addEventListener('click', () => {
    ferr.style.display = 'none';
    spinner.style.display = 'block';

    const canvas = document.createElement('canvas');
    canvas.width = fv.videoWidth;
    canvas.height = fv.videoHeight;
    canvas.getContext('2d').drawImage(fv, 0, 0);

    canvas.toBlob(async blob => {
      stopCam();
      const fd = new FormData();
      fd.append('photo', blob, 'scan.jpg');

      try {
        const res = await fetch('/web/beneficiary/verify-face/', {
          method: 'POST',
          credentials: 'same-origin',
          body: fd
        });
        spinner.style.display = 'none';

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Verification failed');

        // success!
        faceModal.hide();
        needModal.show();
      } catch (e) {
        ferr.textContent = e.message;
        ferr.style.display = 'block';
      }
    }, 'image/jpeg');
  });

  // Need selection
  needBtns.forEach(b =>
    b.addEventListener('click', () => {
      currentNeed = b.dataset.need;
      const labels = {
        food: 'Food Assistance',
        school_supplies: 'School Supplies',
        transport: 'Transport',
        rent: 'Rent'
      };
      lblNeed.textContent = labels[currentNeed] || '';
      needModal.hide();
      detailsModal.show();
    })
  );

  // Enable Submit button
  amtInp.addEventListener('input', () => {
    btnSubmit.disabled = !(parseInt(amtInp.value, 10) >= 1);
  });

  // Submit the request
  btnSubmit.addEventListener('click', async () => {
    const amount = parseInt(amtInp.value, 10);
    detailsModal.hide();
    processingModal.show();

    try {
      const res = await fetch('/web/beneficiary/new-request/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ need_type: currentNeed, requested_amount: amount })
      });

      const data = await res.json();
      // hide processing before any next modal
      processingModal.hide();

      if (!res.ok) throw new Error(data.error || 'Submission failed');

      // show pending
      pendingModal.show();
    } catch (e) {
      processingModal.hide();
      errMsg.textContent = e.message;
      errorModal.show();
      needModal.show();
    }
  });

  // Finish Pending → reset flow
  btnFinishPending.addEventListener('click', () => {
    pendingModal.hide();
    resetAll();
  });
});
