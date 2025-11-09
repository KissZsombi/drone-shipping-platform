<?php
if (!defined('ABSPATH')) {
    exit;
}

function drone_map_register_settings(): void
{
    register_setting(
        'drone_map_settings_group',
        'drone_map_rest_base_url',
        [
            'type' => 'string',
            'sanitize_callback' => 'esc_url_raw',
            'default' => '',
        ]
    );

    register_setting(
        'drone_map_settings_group',
        'drone_map_ws_url',
        [
            'type' => 'string',
            'sanitize_callback' => 'esc_url_raw',
            'default' => '',
        ]
    );
}
add_action('admin_init', 'drone_map_register_settings');

function drone_map_add_settings_page(): void
{
    add_options_page(
        __('Drone Map Settings', 'drone-map'),
        __('Drone Map', 'drone-map'),
        'manage_options',
        'drone-map-settings',
        'drone_map_render_settings_page'
    );
}
add_action('admin_menu', 'drone_map_add_settings_page');

function drone_map_render_settings_page(): void
{
    if (!current_user_can('manage_options')) {
        return;
    }

    $rest_value = get_option('drone_map_rest_base_url', '');
    $ws_value = get_option('drone_map_ws_url', '');
    ?>
    <div class="wrap">
        <h1><?php esc_html_e('Drone Map Settings', 'drone-map'); ?></h1>
        <form method="post" action="options.php">
            <?php settings_fields('drone_map_settings_group'); ?>
            <table class="form-table" role="presentation">
                <tr>
                    <th scope="row">
                        <label for="drone_map_rest_base_url"><?php esc_html_e('REST Base URL', 'drone-map'); ?></label>
                    </th>
                    <td>
                        <input
                                type="url"
                                id="drone_map_rest_base_url"
                                name="drone_map_rest_base_url"
                                class="regular-text"
                                value="<?php echo esc_attr($rest_value); ?>"
                                placeholder="http://localhost:8000"
                        />
                        <p class="description">
                            <?php esc_html_e('FastAPI base URL (example: http://localhost:8000)', 'drone-map'); ?>
                        </p>
                    </td>
                </tr>
                <tr>
                    <th scope="row">
                        <label for="drone_map_ws_url"><?php esc_html_e('WebSocket URL', 'drone-map'); ?></label>
                    </th>
                    <td>
                        <input
                                type="url"
                                id="drone_map_ws_url"
                                name="drone_map_ws_url"
                                class="regular-text"
                                value="<?php echo esc_attr($ws_value); ?>"
                                placeholder="ws://localhost:8000/ws"
                        />
                        <p class="description">
                            <?php esc_html_e('WebSocket endpoint exposed by the backend (example: ws://localhost:8000/ws)', 'drone-map'); ?>
                        </p>
                    </td>
                </tr>
            </table>
            <?php submit_button(); ?>
        </form>
    </div>
    <?php
}

function drone_map_get_options(): array
{
    return [
        'rest_base_url' => get_option('drone_map_rest_base_url', ''),
        'ws_url' => get_option('drone_map_ws_url', ''),
    ];
}
