<template>
    <div class="px-3">
        <b-progress :max="maximum" :value="used" variant="primary"></b-progress>
        <strong>{{ used }} GB de {{ maximum }} GB</strong> usados
    </div>
</template>

<script>
export default {
    computed: {
        used() { return (this.$effectiveUser().used_space / Math.pow(1024, 2)).toFixed(2); },
        maximum() { return (this.$effectiveUser().maximum_space / Math.pow(1024, 2)).toFixed(2); },

    }
}
</script>