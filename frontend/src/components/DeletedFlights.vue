<template>
    <div class="pt-3" style="padding-left:15px; padding-right:15px;">
        <h1>Mis vuelos eliminados</h1>
    
        <div v-if="error">Error!</div>
        <div class="row">
            <flight-partial v-for="flight in flights" :flight="flight" :key="flight.uuid" deleted @delete-confirmed="updateFlights"  @restore-confirmed="updateFlights"></flight-partial>
        </div>
        <b-alert v-if="noFlights" variant="info" show>No tiene vuelos eliminados</b-alert>
    </div>
</template>

<script>
import axios from 'axios';
import FlightPartial from './FlightPartial'
import forceLogin from './mixins/force_login'

export default {
    data() {
        return {
            flights: [],
            error: "",
        }
    },
    computed: {
        noFlights() {
            return this.flights.length == 0;
        }
    },
    methods: {
        updateFlights() {
            axios
                .get('api/flights/deleted', {
                    headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                })
                .then(response => (this.flights = response.data))
                .catch(error => this.error = error);
        },
    },
    created() {
        this.updateFlights();
    },
    components: { FlightPartial },
    mixins: [forceLogin]
}
</script>