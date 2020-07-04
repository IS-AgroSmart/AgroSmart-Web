<template>
    <div>
        <h1>Mis vuelos eliminados</h1>
    
        <div v-if="error">Error!</div>
        <div class="row">
            <flight-partial v-for="flight in flights" :flight="flight" :key="flight.uuid" deleted></flight-partial>
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
                    headers: { "Authorization": "Token " + this.storage.token }
                })
                .then(response => (this.flights = response.data))
                .catch(error => this.error = error);
        }
    },
    created() {
        this.updateFlights();
    },
    components: { FlightPartial },
    mixins: [forceLogin]
}
</script>