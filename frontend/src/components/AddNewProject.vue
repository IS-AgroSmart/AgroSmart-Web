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
    data() {
        return {

        };
    },
    computed: {
        targetUser: function() {
            // returns this.storage.otherUserPk. If it's null, it falls back to this.storage.loggedInUser
            return this.storage.otherUserPk || this.storage.loggedInUser;
        },
        canCreateProjects: function() { return ["ACTIVE", "ADMIN"].includes(this.targetUser.type); },
    },
    mixins: [forceLogin]
}
</script>