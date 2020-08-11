<template>
    <div class="my-4">
        <b-card title="" class="mb-2">
            <div class="text-center">
                <b-button v-if="canCreateFlights" :to="{name: 'newFlight'}" variant="primary">Crear vuelo</b-button>
                <b-card-text v-else>
                    <small class="text-muted">No puede crear vuelos. Póngase en contacto con AgroSmart para activar su cuenta.</small>
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
        canCreateFlights: function() { return ["ACTIVE", "ADMIN"].includes(this.storage.loggedInUser.type); },
    },
    mixins: [forceLogin]
}
</script>