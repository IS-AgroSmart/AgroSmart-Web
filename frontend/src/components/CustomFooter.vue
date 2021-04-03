<template>
    <footer class="footer mt-auto py-2 bg-light">
        <b-row align-v="center">
            <b-col md="4">
                <disk-space-indicator v-if="shouldShowDisk" />
            </b-col>
            <b-col md="4" offset-md="4">&copy; Flysensor 2021</b-col>
        </b-row>
    </footer>
</template>

<script>
import DiskSpaceIndicator from './DiskSpaceIndicator'

export default {
    components: {
        DiskSpaceIndicator
    },
    computed: {
        shouldShowDisk() { return this.$effectiveUser() != null; },
    },
}
</script>