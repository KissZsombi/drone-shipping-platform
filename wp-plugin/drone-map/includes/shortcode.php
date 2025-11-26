<?php
if (!defined('ABSPATH')) {
    exit;
}

function drone_map_render_shortcode(): string
{
    ob_start();
    ?>
    <div id="drone-map" style="height: 80vh;"></div>
    <div id="drone-stats" class="drone-stats"></div>
    <?php
    return ob_get_clean();
}

add_shortcode('drone_map', 'drone_map_render_shortcode');

function drone_map_render_order_form(): string
{
    ob_start();
    ?>
    <form id="drone-order-form" class="drone-order-form">
        <div class="drone-order-field">
            <label for="drone-order-origin"><?php esc_html_e('Origin', 'drone-map'); ?></label>
            <select id="drone-order-origin" name="origin_location_id" required>
                <option value=""><?php esc_html_e('Select origin', 'drone-map'); ?></option>
            </select>
        </div>
        <div class="drone-order-field">
            <label for="drone-order-destination"><?php esc_html_e('Destination', 'drone-map'); ?></label>
            <select id="drone-order-destination" name="destination_location_id" required>
                <option value=""><?php esc_html_e('Select destination', 'drone-map'); ?></option>
            </select>
        </div>
        <div class="drone-order-field">
            <label for="drone-order-weight"><?php esc_html_e('Weight (kg)', 'drone-map'); ?></label>
            <input type="number" id="drone-order-weight" name="weight_kg" min="0.1" step="0.1" placeholder="1.0" required />
        </div>
        <button type="submit" class="drone-order-submit"><?php esc_html_e('Place order', 'drone-map'); ?></button>
    </form>
    <div id="drone-order-message" class="drone-order-message" aria-live="polite"></div>
    <?php
    return ob_get_clean();
}

add_shortcode('drone_order_form', 'drone_map_render_order_form');
