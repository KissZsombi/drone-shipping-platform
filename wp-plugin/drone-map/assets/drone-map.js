(function (window, document) {
    'use strict';

    const settings = window.DRONE_MAP || {};
    const restBase = (settings.REST_BASE_URL || '').replace(/\/$/, '');
    const wsUrl = settings.WS_URL || '';

    document.addEventListener('DOMContentLoaded', init);

    function init() {
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
            if (!restBase) {
                console.warn('REST_BASE_URL is not configured for Drone Map.');
                return Promise.resolve();
            }

            return fetch(restBase + '/api/points')
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
            if (!restBase) {
                return;
            }
            fetch(restBase + '/api/route')
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
})(window, document);
