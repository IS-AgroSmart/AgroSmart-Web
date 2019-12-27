<template>
    <p>
    </p>
</template>

<script>
export default {
    created() {
        window.console.log("Clearing")
        this.storage.token = "";
        this.$router.replace("/")
    }
}
</script>