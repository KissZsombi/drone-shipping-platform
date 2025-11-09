# Drone Map WordPress Plugin

Displays live drone telemetry on a Leaflet map using the FastAPI backend provided in this repository.

## Installation

1. Compress the `drone-map` folder or copy it into your WordPress `wp-content/plugins` directory.
2. Activate **Drone Map** from the WordPress Plugins list.

## Configuration

1. Navigate to **Settings → Drone Map**.
2. Fill in:
   - **REST Base URL** – e.g. `http://localhost:8000`
   - **WebSocket URL** – e.g. `ws://localhost:8000/ws`
3. Save the settings.

## Usage

Add the shortcode `[drone_map]` to any page or post. The map displays:

- All static points returned by `GET /api/points`
- The cached route from `GET /api/route`
- The live drone marker driven by the `/ws` WebSocket stream
