<template>
    <p>
    </p>
</template>

<script>
export default {
    created() {
        this.storage.token = "";
        this.storage.loggedInUser = {};
        this.storage.otherUserPk = 0;
        this.$router.replace("/");
    }
}
</script>
