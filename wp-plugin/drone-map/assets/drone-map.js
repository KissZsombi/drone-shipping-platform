(function (window, document) {
    'use strict';

    const settings = window.DRONE_MAP || {};
    const backendSettings = window.DRONE_BACKEND || {};
    const restBase = (settings.REST_BASE_URL || '').replace(/\/$/, '');
    const apiBase = (backendSettings.BACKEND_BASE_URL || restBase).replace(/\/$/, '');
    const wsUrl = settings.WS_URL || '';

    document.addEventListener('DOMContentLoaded', init);

    function init() {
        setupMap();
        setupOrderForm();
    }

    function setupMap() {
        if (typeof L === 'undefined') {
            console.warn('Leaflet is required for Drone Map.');
            return;
        }

        const mapElement = document.getElementById('drone-map');
        if (!mapElement) {
            return;
        }

        const map = L.map(mapElement).setView([47.1625, 19.5033], 7);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        const statsElement = document.getElementById('drone-stats');
        const liveTrack = L.polyline([], {color: '#0d6efd', weight: 3}).addTo(map);
        const pointLookup = new Map();
        let droneMarker = null;

        loadPoints().then(loadRoute).catch(console.error);
        connectWebSocket();

        function loadPoints() {
            if (!apiBase) {
                console.warn('Backend URL is not configured for Drone Map.');
                return Promise.resolve();
            }

            return fetch(apiBase + '/api/points')
                .then((response) => response.json())
                .then((points) => {
                    if (!Array.isArray(points)) {
                        return;
                    }
                    const bounds = [];
                    points.forEach((point) => {
                        if (typeof point.lat !== 'number' || typeof point.lon !== 'number') {
                            return;
                        }
                        const latLng = [point.lat, point.lon];
                        pointLookup.set(point.name, latLng);
                        const marker = L.marker(latLng).addTo(map);
                        marker.bindPopup(`<strong>${point.name}</strong>`);
                        bounds.push(latLng);
                    });
                    if (bounds.length > 0) {
                        map.fitBounds(bounds, {padding: [30, 30]});
                    }
                })
                .catch((error) => {
                    console.error('Failed to load points', error);
                });
        }

        function loadRoute() {
            if (!apiBase) {
                return;
            }
            fetch(apiBase + '/api/route')
                .then((response) => response.json())
                .then((route) => {
                    if (!Array.isArray(route)) {
                        return;
                    }
                    const coords = route
                        .map((name) => pointLookup.get(name))
                        .filter(Boolean);
                    if (coords.length > 0) {
                        liveTrack.setLatLngs(coords);
                    }
                })
                .catch((error) => console.error('Failed to load route', error));
        }

        function connectWebSocket() {
            if (!wsUrl) {
                console.warn('WS_URL is not configured for Drone Map.');
                return;
            }

            const socket = new window.WebSocket(wsUrl);

            socket.addEventListener('message', (event) => {
                try {
                    const payload = JSON.parse(event.data);
                    handleTelemetry(payload);
                } catch (error) {
                    console.error('Invalid telemetry payload', error);
                }
            });

            socket.addEventListener('close', () => {
                setTimeout(connectWebSocket, 3000);
            });

            socket.addEventListener('error', () => {
                socket.close();
            });
        }

        function handleTelemetry(payload) {
            if (!payload || !payload.coordinates) {
                return;
            }

            const lon = Number(payload.coordinates.x);
            const lat = Number(payload.coordinates.y);
            if (Number.isNaN(lat) || Number.isNaN(lon)) {
                return;
            }

            const latLng = [lat, lon];
            if (!droneMarker) {
                droneMarker = L.marker(latLng, {title: payload.next || 'Drone'}).addTo(map);
            } else {
                droneMarker.setLatLng(latLng);
            }
            liveTrack.addLatLng(latLng);
            updateStats(payload);
        }

        function updateStats(payload) {
            if (!statsElement) {
                return;
            }

            const previous = payload.previous || 'N/A';
            const next = payload.next || 'N/A';
            const distance = typeof payload.distance === 'number'
                ? `${payload.distance.toFixed(1)} m`
                : 'N/A';

            statsElement.innerHTML = `
                <div><strong>Previous:</strong> ${previous}</div>
                <div><strong>Next:</strong> ${next}</div>
                <div><strong>Distance:</strong> ${distance}</div>
            `;
        }
    }

    function setupOrderForm() {
        const form = document.getElementById('drone-order-form');
        const originSelect = document.getElementById('drone-order-origin');
        const destinationSelect = document.getElementById('drone-order-destination');
        const weightInput = document.getElementById('drone-order-weight');
        const messageEl = document.getElementById('drone-order-message');

        if (!form || !originSelect || !destinationSelect || !weightInput) {
            return;
        }

        if (apiBase) {
            populateLocations(originSelect, destinationSelect);
        } else {
            setMessage('Backend URL is not configured.', true);
        }

        form.addEventListener('submit', (event) => {
            event.preventDefault();
            if (!apiBase) {
                setMessage('Backend URL is not configured.', true);
                return;
            }

            const payload = {
                origin_location_id: parseInt(originSelect.value, 10),
                destination_location_id: parseInt(destinationSelect.value, 10),
                weight_kg: parseFloat(weightInput.value),
            };

            if (!payload.origin_location_id || !payload.destination_location_id || Number.isNaN(payload.weight_kg)) {
                setMessage('Please select both locations and provide a weight.', true);
                return;
            }

            fetch(apiBase + '/api/orders', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload),
            })
                .then(async (response) => {
                    if (!response.ok) {
                        const errorPayload = await response.json().catch(() => ({}));
                        const detail = errorPayload.detail || 'Failed to place order.';
                        throw new Error(detail);
                    }
                    return response.json();
                })
                .then((data) => {
                    setMessage(`Order #${data.id} created. Status: ${data.status}`, false);
                    form.reset();
                })
                .catch((error) => {
                    setMessage(error.message || 'Failed to place order.', true);
                });
        });

        function populateLocations(originTarget, destinationTarget) {
            fetch(apiBase + '/api/locations')
                .then((response) => response.json())
                .then((locations) => {
                    if (!Array.isArray(locations)) {
                        return;
                    }
                    const sorted = locations.slice().sort((a, b) => a.name.localeCompare(b.name));
                    [originTarget, destinationTarget].forEach((select) => {
                        select.innerHTML = '<option value="">Select location</option>';
                        sorted.forEach((loc) => {
                            const option = document.createElement('option');
                            option.value = String(loc.id);
                            option.textContent = loc.name;
                            select.appendChild(option);
                        });
                    });
                })
                .catch((error) => {
                    console.error('Failed to load locations', error);
                    setMessage('Failed to load locations from backend.', true);
                });
        }

        function setMessage(text, isError) {
            if (!messageEl) {
                return;
            }
            messageEl.textContent = text;
            messageEl.style.color = isError ? '#dc3545' : '#198754';
        }
    }
})(window, document);
