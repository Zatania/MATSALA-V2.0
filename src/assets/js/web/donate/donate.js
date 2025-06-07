// donate.js
document.addEventListener('DOMContentLoaded', function () {
  // Utility to handle GCash donation modal logic
  function setupDonationModal(modalId, pickerId, namedFieldsId, doneBtnId) {
    const picker = document.getElementById(pickerId);
    const namedFields = document.getElementById(namedFieldsId);
    const modal = document.getElementById(modalId);
    const doneButton = document.getElementById(doneBtnId);
    const firstNameInput = modal.querySelector('#firstName');
    const lastNameInput = modal.querySelector('#lastName');
    const usernameInput = modal.querySelector('#username');

    function updateView() {
      if (picker.value === 'Named') {
        namedFields.style.display = 'block';
      } else {
        namedFields.style.display = 'none';
      }
      updateDoneButtonState();
    }

    function updateDoneButtonState() {
      if (picker.value === 'Anonymous') {
        doneButton.disabled = false;
      } else {
        const isFirstFilled = firstNameInput.value.trim() !== '';
        const isLastFilled = lastNameInput.value.trim() !== '';
        doneButton.disabled = !(isFirstFilled && isLastFilled);
      }
    }

    modal.addEventListener('shown.bs.modal', () => {
      updateView();
    });

    modal.addEventListener('hidden.bs.modal', () => {
      firstNameInput.value = '';
      lastNameInput.value = '';
      usernameInput.value = '';
      $(picker).selectpicker('val', 'Anonymous');
      namedFields.style.display = 'none';
      doneButton.disabled = true;
    });

    picker.addEventListener('change', updateView);
    firstNameInput.addEventListener('input', updateDoneButtonState);
    lastNameInput.addEventListener('input', updateDoneButtonState);
  }

  // GCash modal logic
  setupDonationModal('gcashModal', 'gcashpickerDonationType', 'gcashnamedFields', 'gcashDoneBtn');

  // GCash QR display logic
  const gcashAmountSelect = document.getElementById('gcashpickerAmountQR');
  const gcashQrWrapper = document.getElementById('gcashQrImageWrapper');
  const gcashQrImage = document.getElementById('gcashQrImage');
  const gcashQrText = document.getElementById('gcashQrText');

  const amountToImageMap = {
    5: '/static/img/kiosk/qr-5.jpg',
    10: '/static/img/kiosk/qr-10.jpg',
    20: '/static/img/kiosk/qr-20.jpg',
    50: '/static/img/kiosk/qr-50.jpg',
    100: '/static/img/kiosk/qr-100.jpg',
    500: '/static/img/kiosk/qr-500.jpg',
    1000: '/static/img/kiosk/qr-1000.jpg'
  };

  function updateGcashQr(amount) {
    if (amountToImageMap[amount]) {
      gcashQrImage.src = amountToImageMap[amount];
      gcashQrWrapper.style.display = 'block';
      gcashQrText.textContent = `Scan this with your GCash app to pay ₱${parseFloat(amount).toFixed(2)}`;
    } else {
      gcashQrWrapper.style.display = 'none';
      gcashQrImage.src = '';
      gcashQrText.textContent = '';
    }
  }

  gcashAmountSelect.addEventListener('change', function () {
    updateGcashQr(gcashAmountSelect.value);
  });

  const gcashModalEl = document.getElementById('gcashModal');
  gcashModalEl.addEventListener('shown.bs.modal', () => {
    $(gcashAmountSelect).selectpicker('render');
    updateGcashQr(gcashAmountSelect.value);
  });
  gcashModalEl.addEventListener('hidden.bs.modal', () => {
    gcashQrWrapper.style.display = 'none';
    gcashQrImage.src = '';
    gcashQrText.textContent = '';
    $(gcashAmountSelect).selectpicker('val', '5');
  });

  // Reference Number Modal Logic for GCash
  const gcashDoneBtn = document.getElementById('gcashDoneBtn');
  const referenceModal = new bootstrap.Modal(document.getElementById('referenceModal'));
  const referenceNumberInput = document.getElementById('referenceNumberInput');
  const referenceConfirmBtn = document.getElementById('referenceConfirmBtn');
  const referenceError = document.getElementById('referenceError');

  function showReferenceModal() {
    referenceNumberInput.value = '';
    referenceConfirmBtn.disabled = true;
    referenceError.style.display = 'none';
    referenceModal.show();
  }

  gcashDoneBtn.addEventListener('click', function () {
    showReferenceModal();
  });

  referenceNumberInput.addEventListener('input', function () {
    if (referenceNumberInput.value.trim() === '') {
      referenceConfirmBtn.disabled = true;
      referenceError.style.display = 'none';
    } else {
      referenceConfirmBtn.disabled = false;
      referenceError.style.display = 'none';
    }
  });

  referenceConfirmBtn.addEventListener('click', function () {
    function getCookie(name) {
      const cookieValue = document.cookie.split('; ').find(row => row.startsWith(name + '='));
      return cookieValue ? decodeURIComponent(cookieValue.split('=')[1]) : null;
    }

    // Usage:
    const csrfToken = getCookie('csrftoken');

    const refValue = referenceNumberInput.value.trim();
    if (!refValue) {
      referenceError.textContent = 'Please enter a valid reference number.';
      referenceError.style.display = 'block';
      return;
    }

    // Build payload
    const donationType = document.getElementById('gcashpickerDonationType').value;
    const amount = document.getElementById('gcashpickerAmountQR').value;
    const payload = {
      donation_type: donationType,
      amount: amount,
      reference_number: refValue
    };

    if (donationType === 'Named') {
      payload.first_name = document.getElementById('firstName').value.trim();
      payload.last_name = document.getElementById('lastName').value.trim();
      payload.username = document.getElementById('username').value.trim();
    }

    // POST to your Django view
    fetch('/kiosk/donor/gcash-donate/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(payload)
    })
      .then(res =>
        res
          .json()
          .catch(() => ({}))
          .then(data => ({ status: res.status, body: data }))
      )
      .then(({ status, body }) => {
        if (status === 200 && body.success) {
          // hide reference modal + any other open modal
          referenceModal.hide();
          $('.modal').modal('hide');
          // show thank you
          new bootstrap.Modal(document.getElementById('thankYouModal')).show();
        } else {
          // show backend error
          referenceError.textContent = body.error || 'An unexpected error occurred.';
          referenceError.style.display = 'block';
        }
      })
      .catch(err => {
        referenceError.textContent = 'Network error. Please try again.';
        referenceError.style.display = 'block';
      });
  });
});
