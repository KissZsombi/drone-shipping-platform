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
