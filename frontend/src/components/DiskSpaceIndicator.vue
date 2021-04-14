<template>
    <div class="px-3">
        <b-progress :max="maximum" :value="used" variant="primary" data-cy="disk-space"></b-progress>
        <strong>{{ used }} GB de {{ maximum }} GB</strong> usados 
        <b-icon-info-circle id="info-icon"/>
        <b-tooltip target="info-icon" variant="light">
            <h6>Detalles</h6>
            <p><strong>Espacio usado:</strong> {{ used }} GB</p>
            <p><strong>Espacio disponible:</strong> {{ maximum }} GB</p>
            <p><strong>Cuota de imágenes:</strong> {{ images }}</p>
        </b-tooltip>
    </div>
</template>

<script>
import { BIconInfoCircle } from 'bootstrap-vue';

export default {
    components: {
        BIconInfoCircle,
    },
    computed: {
        used() { return (this.$effectiveUser().used_space / Math.pow(1024, 2)).toFixed(2); },
        maximum() { return (this.$effectiveUser().maximum_space / Math.pow(1024, 2)).toFixed(2); },
        images() { return this.$effectiveUser().remaining_images; },
    }
}
</script>