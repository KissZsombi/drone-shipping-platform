<?php
/**
 * Plugin Name: Drone Map
 * Description: Displays the latest drone route on a Leaflet map using the FastAPI backend.
 * Version: 0.1.0
 * Author: Drone Shipping Team
 */

if (!defined('ABSPATH')) {
    exit;
}

define('DRONE_MAP_VERSION', '0.1.0');
define('DRONE_MAP_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('DRONE_MAP_PLUGIN_URL', plugin_dir_url(__FILE__));

require_once DRONE_MAP_PLUGIN_DIR . 'includes/settings.php';
require_once DRONE_MAP_PLUGIN_DIR . 'includes/shortcode.php';

function drone_map_enqueue_assets(): void
{
    wp_enqueue_style(
        'leaflet',
        'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
        [],
        '1.9.4'
    );

    wp_enqueue_style(
        'drone-map',
        DRONE_MAP_PLUGIN_URL . 'assets/drone-map.css',
        ['leaflet'],
        DRONE_MAP_VERSION
    );

    wp_enqueue_script(
        'leaflet',
        'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
        [],
        '1.9.4',
        true
    );

    wp_enqueue_script(
        'drone-map',
        DRONE_MAP_PLUGIN_URL . 'assets/drone-map.js',
        ['leaflet'],
        DRONE_MAP_VERSION,
        true
    );

    $options = drone_map_get_options();
    $localized = [
        'REST_BASE_URL' => esc_url_raw($options['rest_base_url'] ?? ''),
        'WS_URL' => esc_url_raw($options['ws_url'] ?? ''),
    ];

    wp_localize_script('drone-map', 'DRONE_MAP', $localized);

    $backend_localized = [
        'BACKEND_BASE_URL' => esc_url_raw($options['rest_base_url'] ?? ''),
    ];
    wp_localize_script('drone-map', 'DRONE_BACKEND', $backend_localized);
}
add_action('wp_enqueue_scripts', 'drone_map_enqueue_assets');
