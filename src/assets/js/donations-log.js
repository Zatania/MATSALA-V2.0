'use strict';

$(function () {
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

  const dt_donations = $('.datatables-donations');

  if (dt_donations.length) {
    dt_donations.DataTable({
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
        searchPlaceholder: 'Search donations...',
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
      columnDefs: [{ targets: '_all', className: 'align-middle' }]
    });

    // Optional tweaks
    $('.dataTables_filter input').addClass('ms-0');
    $('div.dataTables_wrapper .dataTables_filter').addClass('mt-0 mt-md-5');
    $('div.dataTables_wrapper div.dataTables_length').addClass('my-5');
  }

  let currentRow, currentDonationId;

  // Approve button
  $(document).on('click', '.approve-donation', function () {
    currentRow = $(this).closest('tr');
    currentDonationId = currentRow.data('donation-id');

    $.ajax({
      url: `/web/admin/donations/${currentDonationId}/action/`,
      method: 'POST',
      data: { action: 'approve' },
      success() {
        Swal.fire('Approved', 'Donation confirmed.', 'success');
      },
      error(xhr) {
        const msg = xhr.responseJSON?.error || 'Error approving';
        Swal.fire('Error', msg, 'error');
      }
    });
  });

  // Reject button: show modal
  $(document).on('click', '.reject-donation', function () {
    currentRow = $(this).closest('tr');
    currentDonationId = currentRow.data('donation-id');
    $('#donationRejectReason').val('');
    $('#donationRejectError').hide();
    $('#donationRejectConfirm').prop('disabled', true);
    new bootstrap.Modal($('#rejectDonationModal')).show();
  });

  // Enable Confirm when non-empty
  $('#donationRejectReason').on('input', function () {
    $('#donationRejectConfirm').prop('disabled', !this.value.trim());
  });

  // Handle Reject confirm
  $('#donationRejectConfirm').on('click', function () {
    const reason = $('#donationRejectReason').val().trim();
    if (!reason) {
      $('#donationRejectError').text('Reason required.').show();
      return;
    }
    $.ajax({
      url: `/web/admin/donations/${currentDonationId}/action/`,
      method: 'POST',
      data: { action: 'reject', reason: reason },
      success() {
        $('#rejectDonationModal').modal('hide');
        // update status cell with rejection note
        currentRow
          .find('td')
          .eq(4)
          .html('Rejected<br><small class="text-muted">Reason: ' + reason + '</small>');
        currentRow.find('td').eq(5).html('<span class="badge bg-label-secondary">No Actions</span>');
        Swal.fire('Rejected', 'Donation has been rejected.', 'success');
      },
      error(xhr) {
        const msg = xhr.responseJSON?.error || 'Error rejecting';
        $('#donationRejectError').text(msg).show();
      }
    });
  });
});
