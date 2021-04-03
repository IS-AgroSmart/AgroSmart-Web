import {
    getUserInfo
} from "../../api/users"

export default {
    created: function () {
        if (!this.$isLoggedIn()) {
            this.$router.push("/login");
        } else {
            getUserInfo(this.storage.token, this.storage.loggedInUser.username)
                .then(([user, err]) => {
                    if (err == null) {
                        window.console.log("Updated user", user)
                        this.storage.loggedInUser = user;
                    }
                });
        }
    },
}