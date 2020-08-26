<template>
    <iframe :src="mapper_url" height="100%" width="100%" frameborder="0">Your browser doesn't support iFrames.</iframe>
</template>

<script>
import forceLogin from './mixins/force_login'

export default {
    data() {
        return {};
    },
    computed: {
        mapper_url() {
            return "/mapper/" + this.$route.params.uuid;
        },
    },
    mixins: [forceLogin]
}
</script>