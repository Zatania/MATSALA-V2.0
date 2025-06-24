'use strict';

$(function () {
  // -- DataTable initialization (same as before, minus manual-pay) --
  let borderColor, bodyBg, headingColor;
  if (isDarkStyle) {
    borderColor = config.colors_dark.borderColor;
    bodyBg = config.colors_dark.bodyBg;
    headingColor = config.colors_dark.headingColor;
  } else {
    borderColor = config.colors.borderColor;
    bodyBg = config.colors.bodyBg;
    headingColor = config.colors.headingColor;
  }

  const dt = $('.datatables-claims').DataTable({
    autoWidth: false,
    scrollX: true,
    order: [[3, 'desc']], // Order by Priority (4th column) descending
    dom:
      '<"row"' +
      '<"col-md-2"<l>>' +
      '<"col-md-10"<"dt-action-buttons d-flex align-items-center justify-content-end flex-md-row flex-column gap-md-4 mb-4 mb-md-0"fB>>' +
      '>t' +
      '<"row"' +
      '<"col-sm-12 col-md-6"i>' +
      '<"col-sm-12 col-md-6"p>' +
      '>',
    language: {
      sLengthMenu: '_MENU_',
      search: '',
      searchPlaceholder: 'Search claims...',
      paginate: {
        next: '<i class="ri-arrow-right-s-line"></i>',
        previous: '<i class="ri-arrow-left-s-line"></i>'
      }
    },
    buttons: [
      {
        extend: 'collection',
        className: 'btn btn-outline-secondary dropdown-toggle me-4 waves-effect waves-light',
        text: '<i class="ri-download-line ri-16px me-1"></i> <span class="d-none d-sm-inline-block">Export</span>',
        buttons: [
          {
            extend: 'print',
            exportOptions: {
              columns: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], // whatever columns you want
              modifier: {
                order: 'applied', // use the table’s current order
                page: 'all' // export all pages, not just the current one
              }
            }
          },
          {
            extend: 'csv',
            exportOptions: {
              columns: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
              modifier: { order: 'applied', page: 'all' }
            }
          },
          {
            extend: 'excel',
            exportOptions: {
              columns: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
              modifier: { order: 'applied', page: 'all' }
            }
          },
          {
            extend: 'pdf',
            exportOptions: {
              columns: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
              modifier: { order: 'applied', page: 'all' }
            }
          },
          {
            extend: 'copy',
            exportOptions: {
              columns: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
              modifier: { order: 'applied', page: 'all' }
            }
          }
        ]
      }
    ],
    responsive: true,
    columnDefs: [{ targets: 5, orderable: false, searchable: false }]
  });

  // -- CSRF helper --
  function getCookie(name) {
    const val = document.cookie.split('; ').find(r => r.startsWith(name + '='));
    return val ? decodeURIComponent(val.split('=')[1]) : null;
  }
  const csrfToken = getCookie('csrftoken');

  // -- Track which row & claim -->
  let currentRow, currentClaimId, allowsPartial;

  // -- Show Approve Modal --
  $(document).on('click', '.approve-claim', function () {
    const $btn = $(this);
    currentRow = $(this).closest('tr');
    currentClaimId = $btn.data('claim-id');

    // EXPLICITALLY READ THE ATTRIBUTE AS A STRING
    // DEBUG

    allowsPartial = $(this).attr('data-willing') === 'true';

    // reset inputs & error
    $('#approveRefInput').val('');
    $('#approveAmountInput').val('');
    $('#approveError').hide();
    $('#approveConfirmBtn').prop('disabled', true);

    // show or hide the amount-field container
    if (allowsPartial) {
      $('#amountGroup').show();
    } else {
      $('#amountGroup').hide();
    }

    new bootstrap.Modal(document.getElementById('approveModal')).show();
  });

  // Enable Confirm only when ref is provided—and if partial, when amount>0
  $('#approveRefInput, #approveAmountInput').on('input', function () {
    const refOk = $('#approveRefInput').val().trim() !== '';
    const amtOk = !allowsPartial || parseFloat($('#approveAmountInput').val()) > 0;
    $('#approveConfirmBtn').prop('disabled', !(refOk && amtOk));
  });

  // handle Approve confirm
  // Submit the approval
  $('#approveConfirmBtn').on('click', function () {
    const ref = $('#approveRefInput').val().trim();
    const payload = { action: 'approve', gcash_payout_id: ref };

    if (allowsPartial) {
      payload.approved_amount = $('#approveAmountInput').val().trim();
    }

    $.ajax({
      url: `/web/admin/claims/${currentClaimId}/action/`,
      method: 'POST',
      data: payload,
      headers: { 'X-CSRFToken': csrfToken },
      success() {
        $('#approveModal').modal('hide');

        // Update status cell
        let html = 'Approved<br><small class="text-muted">Ref: ' + ref + '</small>';
        if (allowsPartial) {
          html += '<br><small class="text-muted">Amt: ₱' + payload.approved_amount + '</small>';
        }
        currentRow.find('.claim-status-cell').html(html);

        // No more actions
        currentRow.find('td').last().html('<span class="badge bg-label-secondary">No Actions</span>');

        Swal.fire('Approved', 'Claim approved successfully.', 'success');
      },
      error(xhr) {
        const msg = xhr.responseJSON?.error || 'Error approving';
        $('#approveError').text(msg).show();
      }
    });
  });

  // -- Show Reject Modal --
  $(document).on('click', '.reject-claim', function () {
    const $btn = $(this);
    currentRow = $(this).closest('tr');
    currentClaimId = $btn.data('claim-id');
    $('#rejectReasonInput').val('');
    $('#rejectError').hide();
    $('#rejectConfirmBtn').prop('disabled', true);
    new bootstrap.Modal(document.getElementById('rejectModal')).show();
  });

  // enable Confirm when textarea non-empty
  $('#rejectReasonInput').on('input', function () {
    $('#rejectConfirmBtn').prop('disabled', !this.value.trim());
  });

  // handle Reject confirm
  $('#rejectConfirmBtn').on('click', function () {
    const reason = $('#rejectReasonInput').val().trim();
    if (!reason) {
      $('#rejectError').text('Rejection reason required.').show();
      return;
    }
    $.ajax({
      url: `/web/admin/claims/${currentClaimId}/action/`,
      method: 'POST',
      data: { action: 'reject', reason: reason },
      success() {
        $('#rejectModal').modal('hide');

        currentRow
          .find('.claim-status-cell')
          .html('Rejected<br><small class="text-muted">Reason: ' + reason + '</small>');

        currentRow.find('td').last().html('<span class="badge bg-label-secondary">No Actions</span>');

        Swal.fire('Rejected', 'Claim has been rejected.', 'success');
      },
      error(xhr) {
        let msg =
          xhr.responseJSON && xhr.responseJSON.error ? xhr.responseJSON.error : xhr.statusText || 'Error rejecting';
        $('#rejectError').text(msg).show();
      }
    });
  });

  // Proof-viewer handler
  $(document).on('click', '.view-proof', function () {
    const url = $(this).data('proof-url');
    const container = $('#proofContainer').empty();

    // Determine file type by extension
    const ext = url.split('.').pop().toLowerCase();
    if (['jpg', 'jpeg', 'png', 'gif'].includes(ext)) {
      // Show image
      $('<img>').attr('src', url).css({ 'max-width': '100%', 'max-height': '70vh' }).appendTo(container);
    } else if (ext === 'pdf') {
      // Embed PDF
      $('<iframe>').attr({ src: url, width: '100%', height: '70vh', frameborder: 0 }).appendTo(container);
    } else {
      // Fallback link
      $('<a>').attr({ href: url, target: '_blank' }).text('Download/View proof').appendTo(container);
    }

    // Show the modal
    new bootstrap.Modal(document.getElementById('proofModal')).show();
  });
});
