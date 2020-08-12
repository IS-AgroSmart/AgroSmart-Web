<template>
    <div class="my-4">
        <b-card title="" class="mb-2">
            <div class="text-center">
                <b-button v-if="canCreateProjects" :to="{name: 'newProject'}" variant="primary">Crear proyecto</b-button>
                <b-card-text v-else>
                    <small class="text-muted">No puede crear proyectos. Póngase en contacto con AgroSmart para activar su cuenta.</small>
                </b-card-text>
            </div>
        </b-card>
    </div>
</template>

<script>
import forceLogin from './mixins/force_login'

export default {
    created() {
        if (!this.$isLoggedIn()) {
            this.$router.push("/login");
        }
    },
    data() {
        return {

        };
    },
    computed: {
        canCreateProjects: function() { return ["ACTIVE", "ADMIN"].includes(this.storage.loggedInUser.type); },
    },
    mixins: [forceLogin]
}
</script>