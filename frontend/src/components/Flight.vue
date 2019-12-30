<template>
    <div>
        <h1>Mis vuelos</h1>
    
        <div v-if="error">Error!</div>
        <div class="row">
            <flight-partial v-for="flight in flights" :flight="flight" :key="flight.uuid"></flight-partial>
        </div>
        <b-alert v-if="noFlights" variant="info" show>Aún no ha creado ningún vuelo</b-alert>
        <add-new-flight-partial/>
    </div>
</template>

<script>
import axios from 'axios';
import FlightPartial from './FlightPartial'
import AddNewFlightPartial from './AddNewFlightPartial'

export default {
    data() {
        return {
            flights: [],
            error: "",
            polling: null
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
                .get('api/flights', {
                    headers: { "Authorization": "Token " + this.storage.token }
                })
                .then(response => (this.flights = response.data))
                .catch(error => this.error = error);
        }
    },
    created() {
        if (!this.$isLoggedIn()) {
            this.$router.push("/login");
        }

        this.updateFlights();
        this.polling = setInterval(() => {
            this.updateFlights();
        }, 2000);
    },
    beforeDestroy() {
        clearInterval(this.polling)
    },
    components: { FlightPartial, AddNewFlightPartial }
}
</script>