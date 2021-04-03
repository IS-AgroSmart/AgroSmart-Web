<template>
    <div class="my-4">
        <b-card title="" class="mb-2">
            <div class="text-center">
                <b-button v-if="canCreateFlights" :to="{name: 'newFlight'}" variant="primary">Crear vuelo</b-button>
                <b-card-text v-else>
                    <small class="text-muted">No puede crear vuelos. {{ unableReason }}</small>
                </b-card-text>
            </div>
        </b-card>
    </div>
</template>

<script>
// import forceLogin from './mixins/force_login'

export default {
    computed: {
        targetUser: function() {
            // returns this.storage.otherUserPk. If it's null, it falls back to this.storage.loggedInUser
            return this.storage.otherUserPk || this.storage.loggedInUser;
        },
        canCreateFlights: function() { return this.unableReason == "" },
        unableReason: function() {
            if (this.targetUser.used_space >= this.targetUser.maximum_space)
                return "Su almacenamiento está lleno.";
            else if (!(["ACTIVE", "ADMIN"].includes(this.targetUser.type)))
                return "Póngase en contacto con AgroSmart para activar su cuenta.";
            return "";
        }
    },
    // mixins: [forceLogin] // forceLogin not required, this will only be instantiated from page components
}
</script>