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
    order: [[3, 'desc']], // Order by date, newest first
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
            text: '<i class="ri-printer-line me-1"></i>Print',
            className: 'dropdown-item',
            exportOptions: { columns: [0, 1, 2, 3] }
          },
          {
            extend: 'csv',
            text: '<i class="ri-file-text-line me-1"></i>Csv',
            className: 'dropdown-item',
            exportOptions: { columns: [0, 1, 2, 3] }
          },
          {
            extend: 'excel',
            text: '<i class="ri-file-excel-line me-1"></i>Excel',
            className: 'dropdown-item',
            exportOptions: { columns: [0, 1, 2, 3] }
          },
          {
            extend: 'pdf',
            text: '<i class="ri-file-pdf-line me-1"></i>Pdf',
            className: 'dropdown-item',
            exportOptions: { columns: [0, 1, 2, 3] }
          },
          {
            extend: 'copy',
            text: '<i class="ri-file-copy-line me-1"></i>Copy',
            className: 'dropdown-item',
            exportOptions: { columns: [0, 1, 2, 3] }
          }
        ]
      }
    ],
    responsive: true,
    columnDefs: [{ targets: 4, orderable: false, searchable: false }]
  });

  // -- CSRF helper --
  function getCookie(name) {
    const val = document.cookie.split('; ').find(r => r.startsWith(name + '='));
    return val ? decodeURIComponent(val.split('=')[1]) : null;
  }
  const csrfToken = getCookie('csrftoken');

  // -- Track which row & claim -->
  let currentRow, currentClaimId;

  // -- Show Approve Modal --
  $(document).on('click', '.approve-claim', function () {
    currentRow = $(this).closest('tr');
    currentClaimId = currentRow.data('claim-id');
    $('#approveRefInput').val('');
    $('#approveError').hide();
    $('#approveConfirmBtn').prop('disabled', true);
    new bootstrap.Modal(document.getElementById('approveModal')).show();
  });

  // enable Confirm when input non-empty
  $('#approveRefInput').on('input', function () {
    $('#approveConfirmBtn').prop('disabled', !this.value.trim());
  });

  // handle Approve confirm
  $('#approveConfirmBtn').on('click', function () {
    const ref = $('#approveRefInput').val().trim();
    if (!ref) {
      $('#approveError').text('Reference number required.').show();
      return;
    }
    $.ajax({
      url: `/web/admin/claims/${currentClaimId}/action/`,
      method: 'POST',
      data: { action: 'approve', reference_number: ref },
      success() {
        $('#approveModal').modal('hide');
        // update row
        currentRow.find('td').eq(2).text('Approved');
        currentRow.find('td').eq(4).html('<span class="badge bg-label-secondary">No Actions</span>');
        Swal.fire('Approved', 'Claim has been approved.', 'success');
      },
      error(xhr) {
        $('#approveError')
          .text(xhr.responseText || 'Error approving')
          .show();
      }
    });
  });

  // -- Show Reject Modal --
  $(document).on('click', '.reject-claim', function () {
    currentRow = $(this).closest('tr');
    currentClaimId = currentRow.data('claim-id');
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
        // update row
        currentRow.find('td').eq(2).text('Rejected');
        currentRow.find('td').eq(4).html('<span class="badge bg-label-secondary">No Actions</span>');
        Swal.fire('Rejected', 'Claim has been rejected.', 'success');
      },
      error(xhr) {
        $('#rejectError')
          .text(xhr.responseText || 'Error rejecting')
          .show();
      }
    });
  });
});
