<template>
    <p>
    </p>
</template>

<script>
export default {
    created() {
        this.storage.token = "";
        this.storage.loggedInUser = {};
        this.$router.replace("/");
    }
}
</script>
