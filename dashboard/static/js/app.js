/**
 * IngatlanMonitor Dashboard JavaScript
 */

// Airport names for tooltips
const AIRPORT_NAMES = {
    'AGP': 'Málaga - Costa del Sol',
    'ALC': 'Alicante - Costa Blanca',
    'RMU': 'Murcia-Corvera - Costa Cálida',
    'VLC': 'Valencia',
    'BIO': 'Bilbao - País Vasco',
    'BRU': 'Brüsszel - Zaventem',
    'CRL': 'Brüsszel - Charleroi'
};

const COUNTRY_NAMES = {
    'ES': 'Spanyolország',
    'BE': 'Belgium'
};

// DataTable instance
let table;

// Add/Edit modal mode: 'add' | 'edit'
let propertyModalMode = 'add';
let propertyEditId = null;
// Vágólapról beillesztett kép tárolása (File objektum)
let pendingPastedImage = null;

// Initialize on document ready
$(document).ready(function() {
    loadStats();
    initDataTable();
    initFilters();
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
            type: 'POST',
            data: function(d) {
                // Add custom filters
                d.country = $('#filter-country').val();
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
            // Image thumbnail
            {
                data: 'image_path',
                orderable: false,
                render: function(data) {
                    if (!data) return '<i class="bi bi-image text-muted" style="font-size:1.4rem;opacity:0.25"></i>';
                    return `<img src="/images/${data}" style="height:48px;width:60px;object-fit:cover;border-radius:4px;cursor:pointer" class="prop-thumbnail" title="Kép megtekintése">`;
                }
            },
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
            // Country
            {
                data: 'country',
                render: function(data) {
                    if (!data) return '-';
                    return `<span class="airport-code" title="${COUNTRY_NAMES[data] || data}">${data}</span>`;
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
            // Rooms
            {
                data: 'rooms',
                render: function(data) {
                    return data ? `${data}` : '-';
                }
            },
            // Bathrooms
            {
                data: 'bathrooms',
                render: function(data) {
                    return data ? `${data}` : '-';
                }
            },
            // Sea distance
            {
                data: 'sea_km',
                render: function(data) {
                    return data !== null ? `${data} km` : '-';
                }
            },
            // Capital distance
            {
                data: 'capital_km',
                render: function(data) {
                    return data !== null && data !== undefined ? `${data} km` : '-';
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
            // Garage
            {
                data: 'has_garage',
                render: function(data) {
                    if (data) return '<i class="bi bi-check-circle-fill bool-yes" title="Van garázs"></i>';
                    return '<i class="bi bi-x-circle-fill bool-no" title="Nincs garázs"></i>';
                }
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
            // IKEA km
            {
                data: 'ikea_km',
                render: function(data) {
                    return data !== null && data !== undefined ? `${data} km` : '-';
                }
            },
            // Lidl km
            {
                data: 'lidl_km',
                render: function(data) {
                    return data !== null && data !== undefined ? `${data} km` : '-';
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
        order: [[1, 'desc']], // Score descending (0. oszlop = kép, nem rendezhető)
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

    $('#properties-table').on('click', '.btn-edit', function(e) {
        e.stopPropagation();
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

    $('#filter-country, #filter-region, #filter-min-score').on('change', applyFilters);
    $('#filter-min-price, #filter-max-price, #filter-min-size').on('input', applyFilters);
    $('#filter-favorites, #filter-archived').on('change', applyFilters);

    // Reset filters
    $('#btn-reset-filters').on('click', function() {
        $('#filter-country').val('');
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
 * Open edit modal for an existing property (reuses addPropertyModal)
 */
function openEditModal(id) {
    $.ajax({
        url: '/api/properties/' + id,
        method: 'GET',
        success: function(data) {
            try {
                propertyModalMode = 'edit';
                propertyEditId = id;

                $('#addPropertyModalTitle').html('<i class="bi bi-pencil"></i> Ingatlan szerkesztése');
                $('#btn-save-add').removeClass('btn-success').addClass('btn-primary')
                    .html('<i class="bi bi-check-lg"></i> Mentés');
                $('#btn-archive-from-edit').show();

                $('#add-url').val('');
                setFetchStatus('', '');

                $('#add-country').val(data.country || 'ES');
                $('#add-portal').val(data.portal || 'egyéb');
                $('#add-city').val(data.city || '');
                $('#add-property-url').val(data.property_url || '');
                $('#add-price').val(data.price_eur !== null ? data.price_eur : '');
                $('#add-size').val(data.size_m2 !== null ? data.size_m2 : '');
                $('#add-rooms').val(data.rooms !== null ? data.rooms : '');
                $('#add-bathrooms').val(data.bathrooms !== null ? data.bathrooms : '');
                $('#add-garden-m2').val(data.garden_m2 !== null ? data.garden_m2 : '');
                $('#add-sea-km').val(data.sea_km !== null ? data.sea_km : '');
                $('#add-capital-km').val(data.capital_km !== null ? data.capital_km : '');
                $('#add-parking').val(data.parking || 'ismeretlen');
                $('#add-garden').val(data.garden || 'ismeretlen');
                $('#add-airport').val(data.airport || '');
                $('#add-airport-km').val(data.airport_km !== null ? data.airport_km : '');
                $('#add-score').val(data.score !== null ? data.score : '');
                $('#add-legal').val(data.legal_status || 'ok');
                $('#add-reason').val(data.reason || '');
                $('#add-description-hu').val(data.description_hu || '');
                $('#add-has-garage').prop('checked', !!data.has_garage);
                $('#add-notes').val(data.user_notes || '');
                $('#add-lat').val(data.latitude !== null ? data.latitude : '');
                $('#add-lon').val(data.longitude !== null ? data.longitude : '');
                $('#add-original-text').val(data.original_text || '');
                $('#add-ikea-km').val(data.ikea_km != null ? data.ikea_km : '');
                $('#add-lidl-km').val(data.lidl_km != null ? data.lidl_km : '');

                // Kép előnézet
                const preview = $('#add-image-preview');
                $('#add-image-file').val('');
                pendingPastedImage = null;
                if (data.image_path) {
                    preview.html(`<img src="/images/${data.image_path}" style="height:80px;border-radius:6px;object-fit:cover" class="me-2"><small class="text-muted">Új fájl választásával cseréled</small>`);
                } else {
                    preview.html('<small class="text-muted">Még nincs kép feltöltve</small>');
                }

                setTimeout(function() {
                    bootstrap.Modal.getOrCreateInstance(
                        document.getElementById('addPropertyModal')
                    ).show();
                }, 0);
            } catch (err) {
                alert('Hiba a szerkesztő megnyitásakor: ' + err.message);
                console.error('openEditModal error:', err);
            }
        },
        error: function(xhr) {
            alert('Nem sikerült betölteni az ingatlan adatait. (HTTP ' + xhr.status + ')');
            console.error('openEditModal AJAX error:', xhr.status, xhr.responseText);
        }
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
        propertyModalMode = 'add';
        propertyEditId = null;
        resetAddForm();
        bootstrap.Modal.getOrCreateInstance(document.getElementById('addPropertyModal')).show();
    });

    // Modal bezárásakor visszaállítás "add" módba
    $('#addPropertyModal').on('hidden.bs.modal', function() {
        propertyModalMode = 'add';
        propertyEditId = null;
        $('#addPropertyModalTitle').html('<i class="bi bi-plus-circle"></i> Új ingatlan felvétele');
        $('#btn-save-add').removeClass('btn-primary').addClass('btn-success').html('<i class="bi bi-check-lg"></i> Mentés');
        $('#btn-archive-from-edit').hide();
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

    // Távolságok újraszámítása koordinátákból
    $('#btn-recalc-distances').on('click', function() {
        const lat = parseFloat($('#add-lat').val());
        const lon = parseFloat($('#add-lon').val());
        if (!lat || !lon) {
            setFetchStatus('Kérlek add meg a koordinátákat!', 'warning');
            return;
        }
        const $btn = $(this);
        $btn.prop('disabled', true).html('<i class="bi bi-hourglass-split"></i> Számítás...');
        setFetchStatus('<i class="bi bi-hourglass-split"></i> Távolságok számítása...', 'muted');

        $.ajax({
            url: '/api/calc_distances',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ latitude: lat, longitude: lon, country: $('#add-country').val() || 'ES' }),
            success: function(d) {
                if (d.airport) $('#add-airport').val(d.airport);
                if (d.airport_km) $('#add-airport-km').val(d.airport_km);
                if (d.capital_km != null) $('#add-capital-km').val(d.capital_km);
                if (d.sea_km != null) $('#add-sea-km').val(d.sea_km);
                if (d.ikea_km != null) $('#add-ikea-km').val(d.ikea_km);
                if (d.lidl_km != null) $('#add-lidl-km').val(d.lidl_km);
                const extras = [];
                if (d.capital_km != null) extras.push(`Főváros: ${d.capital_km} km`);
                if (d.sea_km != null) extras.push(`Tenger: ${d.sea_km} km`);
                if (d.ikea_km != null) extras.push(`IKEA: ${d.ikea_km} km`);
                extras.push(d.lidl_km != null ? `Lidl: ${d.lidl_km} km` : 'Lidl: nincs cache');
                setFetchStatus(
                    `<i class="bi bi-check-circle"></i> Reptér: ${d.airport} ${d.airport_km} km | ${extras.join(' | ')}`,
                    'success'
                );
            },
            error: function(xhr) {
                const msg = xhr.responseJSON ? xhr.responseJSON.error : 'Ismeretlen hiba';
                setFetchStatus('<i class="bi bi-x-circle"></i> Hiba: ' + escapeHtml(msg), 'danger');
            },
            complete: function() {
                $btn.prop('disabled', false).html('<i class="bi bi-arrow-repeat"></i> Távolságok újraszámítása');
            }
        });
    });

    // DeepL Fordítás gomb: teljes szöveg → magyar fordítás
    $('#btn-translate-hu').on('click', function() {
        const text = $('#add-original-text').val().trim();
        if (!text) {
            setFetchStatus('Az eredeti leírás mező üres — illeszd be vagy töltsd be URL-ből!', 'warning');
            return;
        }
        const $btn = $(this);
        $btn.prop('disabled', true).html('<i class="bi bi-hourglass-split"></i> Fordítás...');
        setFetchStatus('<i class="bi bi-hourglass-split"></i> DeepL fordítás folyamatban...', 'muted');

        $.ajax({
            url: '/api/translate',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ text: text }),
            success: function(data) {
                if (data.translated) {
                    $('#add-description-hu').val(data.translated);
                    setFetchStatus('<i class="bi bi-check-circle"></i> Fordítás kész!', 'success');
                }
            },
            error: function(xhr) {
                const msg = xhr.responseJSON ? xhr.responseJSON.error : 'Ismeretlen hiba';
                setFetchStatus('<i class="bi bi-x-circle"></i> Fordítási hiba: ' + escapeHtml(msg), 'danger');
            },
            complete: function() {
                $btn.prop('disabled', false).html('<i class="bi bi-translate"></i> Fordítás');
            }
        });
    });

    // AI Generálás gomb: angol szöveg → mezőkinyerés (kert, garázs, parkolás stb.)
    $('#btn-generate-hu').on('click', function() {
        const text = $('#add-original-text').val().trim();
        if (!text) {
            setFetchStatus('Az eredeti leírás mező üres — illeszd be vagy töltsd be URL-ből!', 'warning');
            return;
        }
        const $btn = $(this);
        $btn.prop('disabled', true).html('<i class="bi bi-hourglass-split"></i> Generálás...');
        setFetchStatus('<i class="bi bi-hourglass-split"></i> AI generálás folyamatban...', 'muted');

        $.ajax({
            url: '/api/ai_describe',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ original_text: text }),
            success: function(data) {
                if (data.description_hu) $('#add-description-hu').val(data.description_hu);
                if (data.garden_m2) $('#add-garden-m2').val(data.garden_m2);
                if (data.has_garage !== undefined) $('#add-has-garage').prop('checked', !!data.has_garage);
                if (data.parking && data.parking !== 'ismeretlen') $('#add-parking').val(data.parking);
                if (data.garden && data.garden !== 'ismeretlen') $('#add-garden').val(data.garden);
                setFetchStatus('<i class="bi bi-check-circle"></i> Magyar leírás generálva — ellenőrizd!', 'success');
            },
            error: function(xhr) {
                const msg = xhr.responseJSON ? xhr.responseJSON.error : 'Ismeretlen hiba';
                setFetchStatus('<i class="bi bi-x-circle"></i> AI hiba: ' + escapeHtml(msg), 'danger');
            },
            complete: function() {
                $btn.prop('disabled', false).html('<i class="bi bi-stars"></i> Generálás');
            }
        });
    });

    // Kép: fájl kiválasztás előnézet
    $('#add-image-file').on('change', function() {
        const file = this.files[0];
        if (file) {
            pendingPastedImage = null;
            showImagePreview(file);
        }
    });

    // Kép: Ctrl+V paste a modalban
    document.getElementById('addPropertyModal').addEventListener('paste', function(e) {
        const items = (e.clipboardData || e.originalEvent.clipboardData).items;
        for (const item of items) {
            if (item.type.startsWith('image/')) {
                const file = item.getAsFile();
                pendingPastedImage = file;
                $('#add-image-file').val('');
                showImagePreview(file);
                e.preventDefault();
                break;
            }
        }
    });

    // Archiválás a szerkesztő modalból
    $('#btn-archive-from-edit').on('click', function() {
        if (!propertyEditId) return;
        if (!confirm('Biztosan archiválod ezt az ingatlant?')) return;
        $.post(`/api/properties/${propertyEditId}/archive`, function() {
            $('#addPropertyModal').modal('hide');
            table.ajax.reload(null, false);
        }).fail(function() {
            alert('Archiválási hiba!');
        });
    });

    // Mentés
    $('#btn-save-add').on('click', saveNewProperty);
}

function showImagePreview(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        $('#add-image-preview').html(
            `<img src="${e.target.result}" style="height:80px;border-radius:6px;object-fit:cover" class="me-2">` +
            `<small class="text-muted">${escapeHtml(file.name || 'vágólapról')}</small>`
        );
    };
    reader.readAsDataURL(file);
}

/**
 * Reset add property form to empty state
 */
function resetAddForm() {
    ['add-url', 'add-city', 'add-property-url', 'add-price', 'add-size',
     'add-rooms', 'add-bathrooms',
     'add-garden-m2', 'add-sea-km', 'add-capital-km', 'add-airport-km', 'add-score',
     'add-reason', 'add-original-text', 'add-description-hu', 'add-notes',
     'add-lat', 'add-lon', 'add-ikea-km', 'add-lidl-km'].forEach(function(id) {
        $('#' + id).val('');
    });
    $('#add-country').val('ES');
    $('#add-portal').val('egyéb');
    $('#add-parking').val('ismeretlen');
    $('#add-garden').val('ismeretlen');
    $('#add-airport').val('');
    $('#add-legal').val('ok');
    $('#add-has-garage').prop('checked', false);
    $('#add-image-file').val('');
    $('#add-image-preview').html('');
    pendingPastedImage = null;
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
    if (data.country) $('#add-country').val(data.country);
    if (data.portal) $('#add-portal').val(data.portal);
    if (data.city) $('#add-city').val(data.city);
    if (data.property_url) $('#add-property-url').val(data.property_url);
    if (data.price_eur) $('#add-price').val(data.price_eur);
    if (data.size_m2) $('#add-size').val(data.size_m2);
    if (data.rooms) $('#add-rooms').val(data.rooms);
    if (data.bathrooms) $('#add-bathrooms').val(data.bathrooms);
    if (data.sea_km) $('#add-sea-km').val(data.sea_km);
    if (data.capital_km != null) $('#add-capital-km').val(data.capital_km);
    if (data.parking && data.parking !== null) $('#add-parking').val(data.parking);
    if (data.garden && data.garden !== null) $('#add-garden').val(data.garden);
    if (data.airport) $('#add-airport').val(data.airport);
    if (data.airport_km) $('#add-airport-km').val(data.airport_km);
    if (data.latitude) $('#add-lat').val(data.latitude);
    if (data.longitude) $('#add-lon').val(data.longitude);
    // Eredeti leírás — mindig felülírjuk (üres is, hogy látszódjon sikerült-e letölteni)
    $('#add-original-text').val(data.original_text || '');
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
        data: JSON.stringify({ city: city, country: $('#add-country').val() || 'ES' }),
        success: function(data) {
            $('#add-lat').val(data.latitude);
            $('#add-lon').val(data.longitude);
            if (data.airport) $('#add-airport').val(data.airport);
            if (data.airport_km) $('#add-airport-km').val(data.airport_km);
            if (data.capital_km != null) $('#add-capital-km').val(data.capital_km);
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
 * Save property (new or edited)
 */
function saveNewProperty() {
    const city = $('#add-city').val().trim();
    if (!city) {
        alert('A város megadása kötelező!');
        $('#add-city').focus();
        return;
    }

    const payload = {
        country: $('#add-country').val() || 'ES',
        portal: $('#add-portal').val(),
        city: city,
        property_url: $('#add-property-url').val().trim() || null,
        price_eur: parseInt($('#add-price').val()) || null,
        size_m2: parseInt($('#add-size').val()) || null,
        rooms: parseInt($('#add-rooms').val()) || null,
        bathrooms: parseInt($('#add-bathrooms').val()) || null,
        garden_m2: parseInt($('#add-garden-m2').val()) || null,
        sea_km: parseInt($('#add-sea-km').val()) || null,
        capital_km: parseInt($('#add-capital-km').val()) || null,
        parking: $('#add-parking').val(),
        garden: $('#add-garden').val(),
        airport: $('#add-airport').val() || null,
        airport_km: parseInt($('#add-airport-km').val()) || null,
        score: parseInt($('#add-score').val()) || null,
        legal_status: $('#add-legal').val(),
        reason: $('#add-reason').val().trim() || null,
        description_hu: $('#add-description-hu').val().trim() || null,
        original_text: $('#add-original-text').val().trim() || null,
        has_garage: $('#add-has-garage').is(':checked') ? 1 : 0,
        ikea_km: parseInt($('#add-ikea-km').val()) || null,
        lidl_km: parseInt($('#add-lidl-km').val()) || null,
        user_notes: $('#add-notes').val().trim() || null,
        latitude: parseFloat($('#add-lat').val()) || null,
        longitude: parseFloat($('#add-lon').val()) || null,
    };

    const isEdit = propertyModalMode === 'edit';
    const ajaxUrl = isEdit ? `/api/properties/${propertyEditId}` : '/api/properties';
    const ajaxMethod = isEdit ? 'PUT' : 'POST';

    $('#btn-save-add').prop('disabled', true);

    $.ajax({
        url: ajaxUrl,
        method: ajaxMethod,
        contentType: 'application/json',
        data: JSON.stringify(payload),
        success: function(resp) {
            const savedId = resp.id || propertyEditId;
            const imageFile = pendingPastedImage || $('#add-image-file')[0].files[0];
            if (imageFile && savedId) {
                const ext = imageFile.type === 'image/png' ? '.png' : imageFile.type === 'image/webp' ? '.webp' : '.jpg';
                const namedFile = imageFile.name ? imageFile : new File([imageFile], `paste${ext}`, { type: imageFile.type });
                const formData = new FormData();
                formData.append('image', namedFile);
                $.ajax({
                    url: '/api/properties/' + savedId + '/image',
                    method: 'POST',
                    data: formData,
                    processData: false,
                    contentType: false,
                    success: function() {
                        bootstrap.Modal.getOrCreateInstance(document.getElementById('addPropertyModal')).hide();
                        table.ajax.reload(null, false);
                        loadStats();
                    },
                    error: function(xhr) {
                        const msg = xhr.responseJSON ? xhr.responseJSON.error : ('HTTP ' + xhr.status);
                        alert('Képfeltöltés sikertelen: ' + msg + '\n\nAz ingatlan adatai mentve, csak a kép nem töltődött fel.');
                        bootstrap.Modal.getOrCreateInstance(document.getElementById('addPropertyModal')).hide();
                        table.ajax.reload(null, false);
                        loadStats();
                    }
                });
            } else {
                bootstrap.Modal.getOrCreateInstance(document.getElementById('addPropertyModal')).hide();
                table.ajax.reload(null, false);
                loadStats();
            }
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
