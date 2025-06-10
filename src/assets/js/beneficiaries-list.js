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
  // 1. Initialize any toasts
  document.querySelectorAll('.toast').forEach(function (element) {
    new bootstrap.Toast(element).show();
  });

  // 2. Initialize DataTable
  const dt_beneficiary_table = $('.datatables-beneficiary');
  let dt;

  if (dt_beneficiary_table.length) {
    dt_beneficiary_table.addClass('w-100');
    dt = dt_beneficiary_table.DataTable({
      autoWidth: false,
      scrollX: true,
      order: [[1, 'asc']], // sort by First Name
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
        searchPlaceholder: 'Search beneficiaries..',
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
              exportOptions: {
                columns: [1, 2, 3, 4], // First / Last / Email / Phone
                format: {
                  body: function (inner) {
                    if (!inner) return '';
                    const el = $.parseHTML(inner);
                    let result = '';
                    $.each(el, function (i, item) {
                      if (item.classList !== undefined && item.classList.contains('user-name')) {
                        result += item.lastChild.firstChild.textContent;
                      } else if (item.innerText === undefined) {
                        result += item.textContent;
                      } else {
                        result += item.innerText;
                      }
                    });
                    return result;
                  }
                }
              },
              customize: function (win) {
                $(win.document.body)
                  .css('color', config.colors.headingColor)
                  .css('border-color', config.colors.borderColor)
                  .css('background-color', config.colors.bodyBg);
                $(win.document.body)
                  .find('table')
                  .addClass('compact')
                  .css('color', 'inherit')
                  .css('border-color', 'inherit')
                  .css('background-color', 'inherit');
              }
            },
            {
              extend: 'csv',
              text: '<i class="ri-file-text-line me-1"></i>Csv',
              className: 'dropdown-item',
              exportOptions: {
                columns: [1, 2, 3, 4],
                format: {
                  body: function (inner) {
                    if (!inner) return '';
                    const el = $.parseHTML(inner);
                    let result = '';
                    $.each(el, function (i, item) {
                      if (item.classList !== undefined && item.classList.contains('user-name')) {
                        result += item.lastChild.firstChild.textContent;
                      } else if (item.innerText === undefined) {
                        result += item.textContent;
                      } else {
                        result += item.innerText;
                      }
                    });
                    return result;
                  }
                }
              }
            },
            {
              extend: 'excel',
              text: '<i class="ri-file-excel-line me-1"></i>Excel',
              className: 'dropdown-item',
              exportOptions: {
                columns: [1, 2, 3, 4],
                format: {
                  body: function (inner) {
                    if (!inner) return '';
                    const el = $.parseHTML(inner);
                    let result = '';
                    $.each(el, function (i, item) {
                      if (item.classList !== undefined && item.classList.contains('user-name')) {
                        result += item.lastChild.firstChild.textContent;
                      } else if (item.innerText === undefined) {
                        result += item.textContent;
                      } else {
                        result += item.innerText;
                      }
                    });
                    return result;
                  }
                }
              }
            },
            {
              extend: 'pdf',
              text: '<i class="ri-file-pdf-line me-1"></i>Pdf',
              className: 'dropdown-item',
              exportOptions: {
                columns: [1, 2, 3, 4],
                format: {
                  body: function (inner) {
                    if (!inner) return '';
                    const el = $.parseHTML(inner);
                    let result = '';
                    $.each(el, function (i, item) {
                      if (item.classList !== undefined && item.classList.contains('user-name')) {
                        result += item.lastChild.firstChild.textContent;
                      } else if (item.innerText === undefined) {
                        result += item.textContent;
                      } else {
                        result += item.innerText;
                      }
                    });
                    return result;
                  }
                }
              }
            },
            {
              extend: 'copy',
              text: '<i class="ri-file-copy-line me-1"></i>Copy',
              className: 'dropdown-item',
              exportOptions: {
                columns: [1, 2, 3, 4],
                format: {
                  body: function (inner) {
                    if (!inner) return '';
                    const el = $.parseHTML(inner);
                    let result = '';
                    $.each(el, function (i, item) {
                      if (item.classList !== undefined && item.classList.contains('user-name')) {
                        result += item.lastChild.firstChild.textContent;
                      } else if (item.innerText === undefined) {
                        result += item.textContent;
                      } else {
                        result += item.innerText;
                      }
                    });
                    return result;
                  }
                }
              }
            }
          ]
        }
      ],
      responsive: {
        details: {
          display: $.fn.dataTable.Responsive.display.modal({
            header: function (row) {
              const data = row.data();
              return 'Beneficiary Details: ' + data[1] + ' ' + data[2];
            }
          }),
          renderer: function (api, rowIdx, columns) {
            const data = $.map(columns, function (col) {
              return col.title
                ? '<tr data-dt-row="' +
                    col.rowIndex +
                    '" data-dt-column="' +
                    col.columnIndex +
                    '">' +
                    '<td>' +
                    col.title +
                    ':</td> ' +
                    '<td>' +
                    col.data +
                    '</td>' +
                    '</tr>'
                : '';
            }).join('');

            return data ? $('<table class="table"/><tbody />').append(data) : false;
          }
        }
      },
      columnDefs: [
        {
          className: 'control',
          orderable: false,
          searchable: false,
          targets: 0
        },
        {
          targets: 1 // First Name
        },
        {
          targets: 2 // Last Name
        },
        {
          targets: 3 // Email
        },
        {
          targets: 4 // Phone
        },
        {
          targets: 5, // Actions
          orderable: false,
          searchable: false
        }
      ]
    });

    // Fix styling adjustments
    $('.dataTables_filter input').addClass('ms-0');
    $('div.dataTables_wrapper .dataTables_filter').addClass('mt-0 mt-md-5');
    $('div.dataTables_wrapper div.dataTables_length').addClass('my-5');
  }

  // 3. Handle “Edit” button click
  $(document).on('click', '.edit-beneficiary-btn', function () {
    const beneficiaryId = $(this).data('beneficiary-id');
    $('#editBeneficiaryId').val(beneficiaryId);

    // Fetch existing data via AJAX GET
    $.ajax({
      url: `/web/admin/beneficiaries/${beneficiaryId}/update/`,
      method: 'GET',
      success: function (data) {
        $('#editFirstName').val(data.first_name);
        $('#editLastName').val(data.last_name);
        $('#editEmail').val(data.email);
        $('#editPhone').val(data.phone);
      },
      error: function () {
        Swal.fire({
          icon: 'error',
          title: 'Failed to Load',
          text: 'Could not retrieve beneficiary data.',
          confirmButtonText: 'OK',
          confirmButtonColor: '#d33',
          customClass: {
            confirmButton: 'btn btn-danger'
          },
          buttonsStyling: false
        });
        $('#editBeneficiaryModal').modal('hide');
      }
    });
  });

  // 4. Handle Edit form submission
  function getCookie(name) {
    const cookieValue = document.cookie.split('; ').find(row => row.startsWith(name + '='));
    return cookieValue ? decodeURIComponent(cookieValue.split('=')[1]) : null;
  }

  // Usage:
  const csrfToken = getCookie('csrftoken');

  $('#editBeneficiaryForm').on('submit', function (e) {
    e.preventDefault();
    const beneficiaryId = $('#editBeneficiaryId').val();
    const formData = $(this).serialize();

    $.ajax({
      url: `/web/admin/beneficiaries/${beneficiaryId}/update/`,
      method: 'POST',
      data: formData,
      success: function () {
        $('#editBeneficiaryModal').modal('hide');
        Swal.fire({
          icon: 'success',
          title: 'Updated',
          text: 'Beneficiary updated successfully.',
          confirmButtonText: 'Reload',
          confirmButtonColor: '#28a745',
          customClass: {
            confirmButton: 'btn btn-success'
          },
          buttonsStyling: false
        }).then(() => {
          location.reload();
        });
      },
      error: function (xhr) {
        const err = xhr.responseJSON?.error || 'Failed to update beneficiary.';
        Swal.fire({
          icon: 'error',
          title: 'Update Failed',
          text: err,
          confirmButtonText: 'OK',
          confirmButtonColor: '#d33',
          customClass: {
            confirmButton: 'btn btn-danger'
          },
          buttonsStyling: false
        });
      }
    });
  });

  // 5. Handle “Delete” button click with SweetAlert
  $(document).on('click', '.delete-beneficiary-btn', function () {
    const beneficiaryId = $(this).data('beneficiary-id');
    const beneficiaryUsername = $(this).data('beneficiary-username');

    Swal.fire({
      title: `Delete "${beneficiaryUsername}"?`,
      text: 'This action cannot be undone.',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Yes, delete',
      cancelButtonText: 'Cancel',
      confirmButtonColor: '#dc3545', // Bootstrap red
      cancelButtonColor: '#6c757d',
      customClass: {
        confirmButton: 'btn btn-danger',
        cancelButton: 'btn btn-secondary'
      },
      buttonsStyling: false
    }).then(result => {
      if (result.isConfirmed) {
        // Send AJAX POST to delete endpoint
        $.ajax({
          url: `/web/admin/beneficiaries/${beneficiaryId}/delete/`,
          method: 'POST',
          success: function () {
            Swal.fire({
              icon: 'success',
              title: 'Deleted!',
              text: 'Beneficiary has been deleted.',
              confirmButtonText: 'OK',
              confirmButtonColor: '#198754',
              customClass: {
                confirmButton: 'btn btn-success'
              },
              buttonsStyling: false
            }).then(() => {
              // Remove row from DataTable
              if (dt) {
                const row = $(`tr[data-beneficiary-id="${beneficiaryId}"]`);
                dt.row(row).remove().draw();
              } else {
                location.reload();
              }
            });
          },
          error: function () {
            Swal.fire({
              icon: 'error',
              title: 'Delete Failed',
              text: 'Could not delete beneficiary. Please try again.',
              confirmButtonText: 'OK',
              confirmButtonColor: '#d33',
              customClass: {
                confirmButton: 'btn btn-danger'
              },
              buttonsStyling: false
            });
          }
        });
      }
    });
  });
});
