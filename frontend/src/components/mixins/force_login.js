export default {
    created: function () {
        if (!this.$isLoggedIn()) {
            this.$router.push("/login");
        }
    },
}