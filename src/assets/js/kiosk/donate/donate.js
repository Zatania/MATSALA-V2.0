let coinSocket = null;
function initCoinSocket() {
  const loc = window.location;
  const wsProtocol = loc.protocol === 'https:' ? 'wss' : 'ws';
  const socketUrl = `${wsProtocol}://${loc.host}/ws/coins/`;
  coinSocket = new WebSocket(socketUrl);

  coinSocket.onopen = () => console.log('Coin WS open');
  coinSocket.onclose = () => {
    console.log('Coin WS closed, retrying in 5s');
    setTimeout(initCoinSocket, 5000);
  };
  coinSocket.onmessage = evt => {
    const data = JSON.parse(evt.data);
    if (data.event === 'coin_inserted') {
      document.getElementById('coinTally').textContent = parseFloat(data.coin_count).toFixed(2);
      document.getElementById('coinDoneBtn').disabled = false;
    }
  };
}
// donate.js
document.addEventListener('DOMContentLoaded', function () {
  document.getElementById('resetTestBtn').addEventListener('click', () => {
    console.log('>>> Test button clicked, sending reset');
    if (coinSocket && coinSocket.readyState === WebSocket.OPEN) {
      coinSocket.send(JSON.stringify({ event: 'reset' }));
      console.log('>>> reset sent');
    } else {
      console.warn('Socket not open');
    }
  });
  /* // initialize coin socket
  initCoinSocket(); */
  // Utility to handle donation-type view logic (show/hide name fields, toggle "Done")
  function setupDonationModal(modalId, pickerId, namedFieldsId, doneBtnId, tallyId = null, inputSelectors = {}) {
    const modal = document.getElementById(modalId);
    const doneButton = document.getElementById(doneBtnId);
    const picker = document.getElementById(pickerId);
    const namedFields = document.getElementById(namedFieldsId);
    const tallyDisplay = tallyId ? document.getElementById(tallyId) : null;

    const firstNameInput = modal.querySelector(inputSelectors.firstName);
    const lastNameInput = modal.querySelector(inputSelectors.lastName);
    const usernameInput = modal.querySelector(inputSelectors.username);

    // Optional amount input (only for GCash)
    const amountInput = inputSelectors.amount ? modal.querySelector(inputSelectors.amount) : null;
    const amountError = inputSelectors.amountError ? modal.querySelector(inputSelectors.amountError) : null;

    // QR wrapper
    const qrWrapper = document.getElementById('gcashQrImageWrapper');

    // Show/hide Named fields and then reevaluate “Done” state
    function updateView() {
      namedFields.style.display = picker.value === 'Named' ? 'block' : 'none';
      updateDoneButtonState();
    }

    // Decide whether “Done” should be enabled, show/hide error
    function updateDoneButtonState() {
      // 1) Name logic
      let enabled =
        picker.value === 'Anonymous' ? true : firstNameInput.value.trim() !== '' && lastNameInput.value.trim() !== '';

      // 2) Amount logic (if present)
      if (amountInput) {
        const raw = amountInput.value.trim();
        const amt = parseFloat(raw);
        const validAmt = !isNaN(amt) && amt > 0 && amt <= 10000;

        // validation message
        if (amountError) {
          amountError.style.display = validAmt ? 'none' : 'block';
        }

        enabled = enabled && validAmt;
      }

      doneButton.disabled = !enabled;
    }

    // When modal opens, reset tally (if applicable) and view
    modal.addEventListener('shown.bs.modal', () => {
      updateView();
      if (amountError) amountError.style.display = 'none';
      if (qrWrapper) qrWrapper.style.display = 'none';
      /* if (tallyDisplay) {
        tallyDisplay.textContent = '0.00';
      } */
    });

    // When modal closes, clear everything and revert picker to Anonymous
    modal.addEventListener('hidden.bs.modal', () => {
      firstNameInput.value = '';
      lastNameInput.value = '';
      usernameInput.value = '';
      if (amountInput) amountInput.value = '';
      if (amountError) amountError.style.display = 'none';
      if (qrWrapper) qrWrapper.style.display = 'none';
      /* if (tallyDisplay) {
        tallyDisplay.textContent = '0.00';
      } */
      $(picker).selectpicker('val', 'Anonymous');
      namedFields.style.display = 'none';
      doneButton.disabled = true;
    });

    // Wire up change/input events
    picker.addEventListener('change', updateView);
    firstNameInput.addEventListener('input', updateDoneButtonState);
    lastNameInput.addEventListener('input', updateDoneButtonState);

    // If we have an amount field, wire its own listener
    if (amountInput) {
      amountInput.addEventListener('input', () => {
        const raw = amountInput.value.trim();
        const amt = parseFloat(raw);
        const validAmt = !isNaN(amt) && amt > 0 && amt <= 10000;

        // only update QR when valid
        if (validAmt) {
          updateGcashQrFromInput(); // your existing function that reads the field
          qrWrapper.style.display = 'block';
        } else {
          qrWrapper.style.display = 'none';
        }

        // always re-check Done button
        updateDoneButtonState();
      });
    }
  }

  // ––––––––––– Apply logic to both Coin Slot and GCash modals –––––––––––
  setupDonationModal('coinModal', 'coinslotpickerDonationType', 'coinslotnamedFields', 'coinDoneBtn', 'coinTally', {
    firstName: '#coinFirstName',
    lastName: '#coinLastName',
    username: '#coinUsername'
  });

  setupDonationModal('gcashModal', 'gcashpickerDonationType', 'gcashnamedFields', 'gcashDoneBtn', null, {
    firstName: '#gcashFirstName',
    lastName: '#gcashLastName',
    username: '#gcashUsername',
    amount: '#gcashCustomAmount',
    amountError: '#gcashAmountError'
  });

  // ––––––––––– GCash QR display logic (unchanged) –––––––––––
  // const gcashAmountSelect = document.getElementById('gcashpickerAmountQR');
  const gcashCustomAmount = document.getElementById('gcashCustomAmount');
  const gcashQrWrapper = document.getElementById('gcashQrImageWrapper');
  const gcashQrImage = document.getElementById('gcashQrImage');
  const gcashQrText = document.getElementById('gcashQrText');

  // Set your static QR or fallback logic here
  function updateGcashQrFromInput() {
    const amount = parseFloat(gcashCustomAmount.value);
    if (!isNaN(amount) && amount <= 10000) {
      gcashQrImage.src = '/static/img/kiosk/qr.jpg'; // Replace with your static QR
      gcashQrText.textContent = `Scan this with your GCash app to pay ₱${amount.toFixed(2)}`;
      gcashQrWrapper.style.display = 'block';
    } else {
      gcashQrWrapper.style.display = 'none';
      gcashQrText.textContent = '';
    }
  }

  gcashCustomAmount.addEventListener('input', () => {
    updateGcashQrFromInput();
  });

  /* const amountToImageMap = {
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
  }); */

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

  // gcashDoneBtn.addEventListener('click', function () {
  //   showReferenceModal();
  // });

  gcashDoneBtn.addEventListener('click', function () {
    const amount = parseFloat(gcashCustomAmount.value);
    if (isNaN(amount) || amount <= 0) {
      alert('Please enter a valid donation amount.');
      return;
    }
    showReferenceModal();
  });

  // referenceNumberInput.addEventListener('input', function () {
  //   if (referenceNumberInput.value.trim() === '') {
  //     referenceConfirmBtn.disabled = true;
  //     referenceError.style.display = 'none';
  //   } else {
  //     referenceConfirmBtn.disabled = false;
  //     referenceError.style.display = 'none';
  //   }
  // });

  referenceNumberInput.addEventListener('input', function () {
    const value = referenceNumberInput.value.trim();
    const isValid = /^[0-9]{12,12}$/.test(value); // Example: numeric, 10–20 digits
    referenceConfirmBtn.disabled = !isValid;
    referenceError.style.display = isValid ? 'none' : 'block';
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
    const amount = document.getElementById('gcashCustomAmount').value;
    const payload = {
      donation_type: donationType,
      amount: amount,
      reference_number: refValue
    };

    if (donationType === 'Named') {
      payload.first_name = document.getElementById('gcashFirstName').value.trim();
      payload.last_name = document.getElementById('gcashLastName').value.trim();
      payload.username = document.getElementById('gcashUsername').value.trim();
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

  // ––––––––––– Coin‐Slot “Done” logic (no Reference Number) –––––––––––
  const coinDoneBtn = document.getElementById('coinDoneBtn');

  // Get a handle to the coin‐modal element
  const coinModalEl = document.getElementById('coinModal');

  // When the coin modal opens:
  coinModalEl.addEventListener('shown.bs.modal', () => {
    // reset tally & disable Done
    document.getElementById('coinTally').textContent = '0.00';
    document.getElementById('coinDoneBtn').disabled = true;

    // open WebSocket
    initCoinSocket();
  });

  // When the coin modal closes:
  coinModalEl.addEventListener('hidden.bs.modal', () => {
    // close WS if open
    if (coinSocket) {
      coinSocket.close();
      coinSocket = null;
    }
    // reset tally again (in case user re‑opens later)
    document.getElementById('coinTally').textContent = '0.00';
  });

  coinDoneBtn.addEventListener('click', function () {
    const donationType = document.getElementById('coinslotpickerDonationType').value;

    // read the tally exactly as displayed (e.g. "3.00") and turn it into a number
    const rawTally = document.getElementById('coinTally').textContent || '0';
    const coinCount = parseFloat(rawTally);

    let payload = {
      donation_type: donationType,
      coin_count: coinCount
    };

    if (donationType === 'Named') {
      payload.first_name = document.getElementById('coinFirstName').value.trim();
      payload.last_name = document.getElementById('coinLastName').value.trim();
      payload.username = document.getElementById('coinUsername').value.trim();
    }

    // grab CSRF token
    function getCookie(name) {
      const row = document.cookie.split('; ').find(r => r.startsWith(name + '='));
      return row ? decodeURIComponent(row.split('=')[1]) : null;
    }
    const csrfToken = getCookie('csrftoken');

    fetch('/kiosk/donor/coin-donate/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(payload)
    })
      .then(res => res.json().then(data => ({ status: res.status, body: data })))
      .then(({ status, body }) => {
        if (status === 200 && body.success) {
          $('#coinModal').modal('hide');
          new bootstrap.Modal(document.getElementById('thankYouModal')).show();
        } else {
          // show backend error in an alert or inline
          alert(body.error || 'An unexpected error occurred.');
        }
      })
      .catch(() => {
        alert('Network error. Please try again.');
      });
  });
});
