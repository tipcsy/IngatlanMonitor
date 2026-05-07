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
    initAddPropertyModal();
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
 * Initialize Add Property modal
 */
function initAddPropertyModal() {
    // Gomb megnyomása → modal megnyitása + mezők ürítése
    $('#btn-add-property').on('click', function() {
        resetAddForm();
        $('#addPropertyModal').modal('show');
    });

    // URL betöltés
    $('#btn-fetch-url').on('click', function() {
        const url = $('#add-url').val().trim();
        if (!url) {
            setFetchStatus('Kérlek add meg az URL-t!', 'warning');
            return;
        }
        fetchPropertyFromUrl(url);
    });

    // Enter az URL mezőben
    $('#add-url').on('keydown', function(e) {
        if (e.key === 'Enter') $('#btn-fetch-url').click();
    });

    // Város geocoding gomb
    $('#btn-geocode').on('click', function() {
        const city = $('#add-city').val().trim();
        if (!city) {
            setFetchStatus('Kérlek add meg a várost!', 'warning');
            return;
        }
        geocodeCity(city);
    });

    // Mentés
    $('#btn-save-add').on('click', saveNewProperty);
}

/**
 * Reset add property form to empty state
 */
function resetAddForm() {
    ['add-url', 'add-city', 'add-property-url', 'add-price', 'add-size',
     'add-garden-m2', 'add-sea-km', 'add-airport-km', 'add-score',
     'add-reason', 'add-notes', 'add-lat', 'add-lon'].forEach(function(id) {
        $('#' + id).val('');
    });
    $('#add-portal').val('egyéb');
    $('#add-parking').val('ismeretlen');
    $('#add-garden').val('ismeretlen');
    $('#add-airport').val('');
    $('#add-legal').val('ok');
    setFetchStatus('', '');
}

/**
 * Set fetch status message
 */
function setFetchStatus(msg, type) {
    const el = $('#fetch-status');
    el.removeClass('text-muted text-success text-danger text-warning');
    if (type) el.addClass('text-' + type);
    el.html(msg);
}

/**
 * Fetch property data from URL via backend scrape endpoint
 */
function fetchPropertyFromUrl(url) {
    setFetchStatus('<i class="bi bi-hourglass-split"></i> Betöltés...', 'muted');
    $('#btn-fetch-url').prop('disabled', true);

    $.ajax({
        url: '/api/scrape',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ url: url }),
        success: function(data) {
            fillAddFormFromData(data);
            if (data.error) {
                setFetchStatus('<i class="bi bi-exclamation-triangle"></i> Részleges betöltés: ' + escapeHtml(data.error) + ' — töltsd ki a hiányzó mezőket kézzel.', 'warning');
            } else {
                setFetchStatus('<i class="bi bi-check-circle"></i> Adatok betöltve — ellenőrizd és egészítsd ki!', 'success');
            }
        },
        error: function(xhr) {
            const msg = xhr.responseJSON ? xhr.responseJSON.error : 'Ismeretlen hiba';
            setFetchStatus('<i class="bi bi-x-circle"></i> Hiba: ' + escapeHtml(msg), 'danger');
        },
        complete: function() {
            $('#btn-fetch-url').prop('disabled', false);
        }
    });
}

/**
 * Fill the add form with scraped data
 */
function fillAddFormFromData(data) {
    if (data.portal) $('#add-portal').val(data.portal);
    if (data.city) $('#add-city').val(data.city);
    if (data.property_url) $('#add-property-url').val(data.property_url);
    if (data.price_eur) $('#add-price').val(data.price_eur);
    if (data.size_m2) $('#add-size').val(data.size_m2);
    if (data.sea_km) $('#add-sea-km').val(data.sea_km);
    if (data.parking && data.parking !== null) $('#add-parking').val(data.parking);
    if (data.garden && data.garden !== null) $('#add-garden').val(data.garden);
    if (data.airport) $('#add-airport').val(data.airport);
    if (data.airport_km) $('#add-airport-km').val(data.airport_km);
    if (data.latitude) $('#add-lat').val(data.latitude);
    if (data.longitude) $('#add-lon').val(data.longitude);
}

/**
 * Geocode city and fill airport/coords fields
 */
function geocodeCity(city) {
    setFetchStatus('<i class="bi bi-hourglass-split"></i> Koordináták lekérése...', 'muted');
    $('#btn-geocode').prop('disabled', true);

    $.ajax({
        url: '/api/geocode',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ city: city }),
        success: function(data) {
            $('#add-lat').val(data.latitude);
            $('#add-lon').val(data.longitude);
            if (data.airport) $('#add-airport').val(data.airport);
            if (data.airport_km) $('#add-airport-km').val(data.airport_km);
            setFetchStatus('<i class="bi bi-check-circle"></i> Koordináták meghatározva: ' + data.airport + ' ' + data.airport_km + ' km', 'success');
        },
        error: function() {
            setFetchStatus('<i class="bi bi-x-circle"></i> Város nem található a geocoding adatbázisban.', 'danger');
        },
        complete: function() {
            $('#btn-geocode').prop('disabled', false);
        }
    });
}

/**
 * Save new property to database
 */
function saveNewProperty() {
    const city = $('#add-city').val().trim();
    if (!city) {
        alert('A város megadása kötelező!');
        $('#add-city').focus();
        return;
    }

    const payload = {
        portal: $('#add-portal').val(),
        city: city,
        property_url: $('#add-property-url').val().trim() || null,
        price_eur: parseInt($('#add-price').val()) || null,
        size_m2: parseInt($('#add-size').val()) || null,
        garden_m2: parseInt($('#add-garden-m2').val()) || null,
        sea_km: parseInt($('#add-sea-km').val()) || null,
        parking: $('#add-parking').val(),
        garden: $('#add-garden').val(),
        airport: $('#add-airport').val() || null,
        airport_km: parseInt($('#add-airport-km').val()) || null,
        score: parseInt($('#add-score').val()) || null,
        legal_status: $('#add-legal').val(),
        reason: $('#add-reason').val().trim() || null,
        user_notes: $('#add-notes').val().trim() || null,
        latitude: parseFloat($('#add-lat').val()) || null,
        longitude: parseFloat($('#add-lon').val()) || null,
    };

    $('#btn-save-add').prop('disabled', true);

    $.ajax({
        url: '/api/properties',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(payload),
        success: function() {
            $('#addPropertyModal').modal('hide');
            table.ajax.reload(null, false);
            loadStats();
        },
        error: function(xhr) {
            const msg = xhr.responseJSON ? xhr.responseJSON.error : 'Ismeretlen hiba';
            alert('Mentési hiba: ' + msg);
        },
        complete: function() {
            $('#btn-save-add').prop('disabled', false);
        }
    });
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
