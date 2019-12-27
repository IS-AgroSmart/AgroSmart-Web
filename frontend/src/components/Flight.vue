<template>
    <div>
        <h1>Mis vuelos</h1>
    
        <div v-if="error">Error!</div>
        <div class="row">
            <flight-partial v-for="flight in flights" :flight="flight" :key="flight.uuid"></flight-partial>
        </div>
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
            error: ""
        }
    },
    computed: {
        allFlights() {
            return this.flights.concat({ addNew: true })
        }
    },
    created() {
        if (!this.$isLoggedIn()) {
            this.$router.push("/login");
        }

        axios
            .get('api/flights', {
                headers: { "Authorization": "Token " + this.storage.token }
            })
            .then(response => (this.flights = response.data))
            .catch(error => this.error = error);
    },
    components: { FlightPartial, AddNewFlightPartial }
}
</script>