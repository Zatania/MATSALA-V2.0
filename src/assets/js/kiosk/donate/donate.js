// donate.js
document.addEventListener('DOMContentLoaded', function () {
  // Utility to handle donation-type view logic (show/hide name fields, toggle "Done")
  function setupDonationModal(modalId, pickerId, namedFieldsId, doneBtnId, tallyId = null) {
    const picker = document.getElementById(pickerId);
    const namedFields = document.getElementById(namedFieldsId);
    const modal = document.getElementById(modalId);
    const doneButton = document.getElementById(doneBtnId);
    const firstNameInput = modal.querySelector('#firstName');
    const lastNameInput = modal.querySelector('#lastName');
    const usernameInput = modal.querySelector('#username');
    const tallyDisplay = tallyId ? document.getElementById(tallyId) : null;

    // Show/hide named fields based on picker; then update Done-button state
    function updateView() {
      if (picker.value === 'Named') {
        namedFields.style.display = 'block';
      } else {
        namedFields.style.display = 'none';
      }
      updateDoneButtonState();
    }

    // If Anonymous → enable "Done" immediately; if Named → wait for first+last
    function updateDoneButtonState() {
      if (picker.value === 'Anonymous') {
        doneButton.disabled = false;
      } else {
        const isFirstFilled = firstNameInput.value.trim() !== '';
        const isLastFilled = lastNameInput.value.trim() !== '';
        doneButton.disabled = !(isFirstFilled && isLastFilled);
      }
    }

    // When modal opens, reset tally (if applicable) and view
    modal.addEventListener('shown.bs.modal', () => {
      updateView();
      if (tallyDisplay) {
        tallyDisplay.textContent = '0.00';
      }
    });

    // When modal closes, clear everything and revert picker to Anonymous
    modal.addEventListener('hidden.bs.modal', () => {
      firstNameInput.value = '';
      lastNameInput.value = '';
      usernameInput.value = '';
      if (tallyDisplay) {
        tallyDisplay.textContent = '0.00';
      }
      $(picker).selectpicker('val', 'Anonymous');
      namedFields.style.display = 'none';
      doneButton.disabled = true;
    });

    // Wire up change/input events
    picker.addEventListener('change', updateView);
    firstNameInput.addEventListener('input', updateDoneButtonState);
    lastNameInput.addEventListener('input', updateDoneButtonState);
  }

  // ––––––––––– Apply logic to both Coin Slot and GCash modals –––––––––––
  setupDonationModal('coinModal', 'coinslotpickerDonationType', 'coinslotnamedFields', 'coinDoneBtn', 'coinTally');

  setupDonationModal('gcashModal', 'gcashpickerDonationType', 'gcashnamedFields', 'gcashDoneBtn');

  // ––––––––––– GCash QR display logic (unchanged) –––––––––––
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

  // ––––––––––– Reference‐Number Modal Logic (only for GCash) –––––––––––
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
    const refValue = referenceNumberInput.value.trim();
    if (refValue === '') {
      referenceError.textContent = 'Please enter a valid reference number.';
      referenceError.style.display = 'block';
      return;
    }

    // TODO: Send GCash donation to your backend:
    //   e.g. AJAX / fetch({
    //     amount: <selected-amount>,
    //     donationType: <Anonymous|Named>,
    //     firstName: ...,
    //     lastName: ...,
    //     username: ...,
    //     referenceNumber: refValue
    //   });

    alert('GCash donation received with Reference # ' + refValue);

    referenceModal.hide();
    $('.modal').modal('hide'); // hide any open GCash or coinModal
  });

  // ––––––––––– Coin‐Slot “Done” logic (no Reference Number) –––––––––––
  const coinDoneBtn = document.getElementById('coinDoneBtn');

  coinDoneBtn.addEventListener('click', function () {
    const donationType = document.getElementById('coinslotpickerDonationType').value;
    const rawTally = document.getElementById('coinTally').textContent || '0';
    const amount = parseFloat(rawTally);

    let firstName = '';
    let lastName = '';
    let username = '';
    if (donationType === 'Named') {
      firstName = document.querySelector('#coinModal #firstName').value.trim();
      lastName = document.querySelector('#coinModal #lastName').value.trim();
      username = document.querySelector('#coinModal #username').value.trim();
    }

    // TODO: Send coin‐slot donation to your backend:
    //   e.g. AJAX / fetch({
    //     amount: amount,
    //     donationType: donationType,
    //     firstName: firstName,
    //     lastName: lastName,
    //     username: username
    //   });

    // Immediately close the coin modal and show “Thank You”
    $('#coinModal').modal('hide');
    const thankYouModal = new bootstrap.Modal(document.getElementById('thankYouModal'));
    thankYouModal.show();
  });
});
