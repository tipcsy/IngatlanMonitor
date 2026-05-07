/**
 * IngatlanMonitor Dashboard JavaScript
 */

// Airport names for tooltips
const AIRPORT_NAMES = {
    'AGP': 'Málaga - Costa del Sol',
    'ALC': 'Alicante - Costa Blanca',
    'RMU': 'Murcia-Corvera - Costa Cálida',
    'VLC': 'Valencia',
    'BIO': 'Bilbao - País Vasco'
};

// DataTable instance
let table;

// Initialize on document ready
$(document).ready(function() {
    loadStats();
    initDataTable();
    initFilters();
    initEditModal();
});

/**
 * Load statistics
 */
function loadStats() {
    $.getJSON('/api/stats', function(data) {
        $('#stat-total').text(data.total || 0);
        $('#stat-high').text(data.high_score || 0);
        $('#stat-favorites').text(data.favorites || 0);

        // Regions
        if (data.by_region) {
            const regionList = Object.entries(data.by_region)
                .map(([r, c]) => `${r}: ${c}`)
                .join(', ');
            $('#stat-regions').text(regionList || '-');
        }
    });
}

/**
 * Initialize DataTable
 */
function initDataTable() {
    table = $('#properties-table').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: '/api/properties',
            data: function(d) {
                // Add custom filters
                d.region = $('#filter-region').val();
                d.min_price = $('#filter-min-price').val() || 0;
                d.max_price = $('#filter-max-price').val() || 0;
                d.min_size = $('#filter-min-size').val() || 0;
                d.min_score = $('#filter-min-score').val() || 0;
                d.show_archived = $('#filter-archived').is(':checked') ? '1' : '0';
                d.favorites_only = $('#filter-favorites').is(':checked') ? '1' : '0';
            }
        },
        columns: [
            // Score
            {
                data: 'score',
                render: function(data) {
                    let cls = 'score-low';
                    if (data >= 7) cls = 'score-high';
                    else if (data >= 5) cls = 'score-medium';
                    return `<span class="score-badge ${cls}">${data}</span>`;
                }
            },
            // City
            { data: 'city' },
            // Price
            {
                data: 'price_eur',
                render: function(data) {
                    if (!data) return '-';
                    return `<span class="price-cell">${data.toLocaleString('hu-HU')} €</span>`;
                }
            },
            // Size
            {
                data: 'size_m2',
                render: function(data) {
                    return data ? `${data} m²` : '-';
                }
            },
            // Sea distance
            {
                data: 'sea_km',
                render: function(data) {
                    return data !== null ? `${data} km` : '-';
                }
            },
            // Airport
            {
                data: 'airport',
                render: function(data) {
                    if (!data) return '-';
                    const name = AIRPORT_NAMES[data] || data;
                    return `<span class="airport-code" title="${name}">${data}</span>`;
                }
            },
            // Airport km
            {
                data: 'airport_km',
                render: function(data) {
                    return data !== null ? `${data} km` : '-';
                }
            },
            // Parking
            {
                data: 'parking',
                render: renderBool
            },
            // Garden
            {
                data: 'garden',
                render: renderBool
            },
            // Garden m2
            {
                data: 'garden_m2',
                render: function(data) {
                    return data ? `${data} m²` : '-';
                }
            },
            // Legal status
            {
                data: 'legal_status',
                render: function(data) {
                    if (!data) return '-';
                    let cls = 'legal-ok';
                    let text = 'OK';
                    if (data === 'kizárt' || data === 'kizart') {
                        cls = 'legal-kizart';
                        text = 'Kizárt';
                    } else if (data === 'kérdéses' || data === 'kerdeses') {
                        cls = 'legal-kerdeses';
                        text = 'Kérdéses';
                    }
                    return `<span class="badge ${cls}">${text}</span>`;
                }
            },
            // Reason
            {
                data: 'reason',
                render: function(data) {
                    if (!data) return '-';
                    const short = data.length > 50 ? data.substring(0, 50) + '...' : data;
                    return `<span class="text-truncate-cell" title="${escapeHtml(data)}">${escapeHtml(short)}</span>`;
                }
            },
            // User notes
            {
                data: 'user_notes',
                render: function(data) {
                    if (!data) return '-';
                    const short = data.length > 30 ? data.substring(0, 30) + '...' : data;
                    return `<span class="text-truncate-cell" title="${escapeHtml(data)}">${escapeHtml(short)}</span>`;
                }
            },
            // Links
            {
                data: null,
                orderable: false,
                render: function(data, type, row) {
                    let links = [];
                    if (row.property_url) {
                        links.push(`<a href="${row.property_url}" target="_blank" title="Ingatlan"><i class="bi bi-house-door"></i></a>`);
                    }
                    if (row.maps_url) {
                        links.push(`<a href="${row.maps_url}" target="_blank" title="Térkép"><i class="bi bi-geo-alt"></i></a>`);
                    }
                    if (row.gmail_url) {
                        links.push(`<a href="${row.gmail_url}" target="_blank" title="Email"><i class="bi bi-envelope"></i></a>`);
                    }
                    return `<span class="links-cell">${links.join(' ')}</span>`;
                }
            },
            // Date
            {
                data: 'email_date',
                render: function(data) {
                    if (!data) return '-';
                    try {
                        const d = new Date(data);
                        return d.toISOString().split('T')[0];
                    } catch {
                        return data.substring(0, 10);
                    }
                }
            },
            // Actions
            {
                data: null,
                orderable: false,
                render: function(data, type, row) {
                    const favClass = row.is_favorite ? 'active' : '';
                    const favIcon = row.is_favorite ? 'bi-heart-fill' : 'bi-heart';
                    const archiveIcon = row.is_archived ? 'bi-archive-fill' : 'bi-archive';
                    const archiveTitle = row.is_archived ? 'Visszaállítás' : 'Archiválás';

                    return `
                        <span class="favorite-star ${favClass}" data-id="${row.id}" title="Kedvenc">
                            <i class="bi ${favIcon}"></i>
                        </span>
                        <button class="btn btn-sm btn-outline-secondary action-btn btn-edit" data-id="${row.id}" title="Szerkesztés">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger action-btn btn-archive" data-id="${row.id}" title="${archiveTitle}">
                            <i class="bi ${archiveIcon}"></i>
                        </button>
                    `;
                }
            }
        ],
        order: [[0, 'desc']], // Score descending
        pageLength: 25,
        lengthMenu: [10, 25, 50, 100],
        language: {
            processing: 'Betöltés...',
            lengthMenu: '_MENU_ elem/oldal',
            zeroRecords: 'Nincs találat',
            info: '_START_ - _END_ / _TOTAL_ ingatlan',
            infoEmpty: 'Nincs adat',
            infoFiltered: '(szűrve: _MAX_ összesen)',
            search: 'Keresés:',
            paginate: {
                first: 'Első',
                last: 'Utolsó',
                next: 'Következő',
                previous: 'Előző'
            }
        },
        createdRow: function(row, data) {
            if (data.is_archived) {
                $(row).addClass('row-archived');
            }
        }
    });

    // Event delegation for action buttons
    $('#properties-table').on('click', '.favorite-star', function() {
        const id = $(this).data('id');
        toggleFavorite(id);
    });

    $('#properties-table').on('click', '.btn-edit', function() {
        const id = $(this).data('id');
        openEditModal(id);
    });

    $('#properties-table').on('click', '.btn-archive', function() {
        const id = $(this).data('id');
        toggleArchive(id);
    });
}

/**
 * Initialize filters
 */
function initFilters() {
    // Debounced filter change handler
    let filterTimeout;
    const applyFilters = function() {
        clearTimeout(filterTimeout);
        filterTimeout = setTimeout(function() {
            table.ajax.reload();
            loadStats();
        }, 300);
    };

    $('#filter-region, #filter-min-score').on('change', applyFilters);
    $('#filter-min-price, #filter-max-price, #filter-min-size').on('input', applyFilters);
    $('#filter-favorites, #filter-archived').on('change', applyFilters);

    // Reset filters
    $('#btn-reset-filters').on('click', function() {
        $('#filter-region').val('');
        $('#filter-min-price').val('');
        $('#filter-max-price').val('');
        $('#filter-min-size').val('');
        $('#filter-min-score').val('7');
        $('#filter-favorites').prop('checked', false);
        $('#filter-archived').prop('checked', false);
        table.ajax.reload();
        loadStats();
    });
}

/**
 * Initialize edit modal
 */
function initEditModal() {
    $('#btn-save-edit').on('click', function() {
        const id = $('#edit-id').val();
        const data = {
            garden_m2: parseInt($('#edit-garden-m2').val()) || null,
            user_notes: $('#edit-notes').val() || null
        };

        $.ajax({
            url: `/api/properties/${id}`,
            method: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function() {
                $('#editModal').modal('hide');
                table.ajax.reload(null, false);
            },
            error: function() {
                alert('Hiba történt a mentés során!');
            }
        });
    });
}

/**
 * Open edit modal for a property
 */
function openEditModal(id) {
    $.getJSON(`/api/properties/${id}`, function(data) {
        $('#edit-id').val(data.id);
        $('#edit-city').val(data.city || '');
        $('#edit-garden-m2').val(data.garden_m2 || '');
        $('#edit-notes').val(data.user_notes || '');
        $('#editModal').modal('show');
    });
}

/**
 * Toggle favorite status
 */
function toggleFavorite(id) {
    $.post(`/api/properties/${id}/favorite`, function() {
        table.ajax.reload(null, false);
        loadStats();
    });
}

/**
 * Toggle archive status
 */
function toggleArchive(id) {
    $.post(`/api/properties/${id}/archive`, function() {
        table.ajax.reload(null, false);
        loadStats();
    });
}

/**
 * Render boolean field (igen/nem/ismeretlen)
 */
function renderBool(data) {
    if (data === 'igen') {
        return '<i class="bi bi-check-circle-fill bool-yes" title="Igen"></i>';
    } else if (data === 'nem') {
        return '<i class="bi bi-x-circle-fill bool-no" title="Nem"></i>';
    }
    return '<i class="bi bi-question-circle bool-unknown" title="Ismeretlen"></i>';
}

/**
 * Escape HTML entities
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
