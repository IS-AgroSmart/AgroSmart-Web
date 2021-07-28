<template>
    <div class="pt-3 px-3">
        <h1>Mis vuelos</h1>
    
        <b-skeleton-wrapper :loading="loading">
            <template #loading>
                <b-row>
                    <b-col v-for="i in 3" :key="i">
                        <b-card class="my-3">
                            <b-skeleton width="85%" height="40%"></b-skeleton>
                            <b-skeleton width="100%"></b-skeleton>
                            <b-skeleton width="100%"></b-skeleton>
                            <b-skeleton type="button"></b-skeleton>
                        </b-card>
                    </b-col>
                </b-row>
            </template>

            <div v-if="error">Error!</div>
            <div class="row">
                <flight-partial v-for="flight in flights" :flight="flight" :key="flight.uuid"></flight-partial>
            </div>
            <b-alert v-if="noFlights" variant="info" show>Aún no ha creado ningún vuelo</b-alert>
        </b-skeleton-wrapper>
        
        <add-new-flight-partial/>
    </div>
</template>

<script>
import axios from 'axios';
import FlightPartial from './FlightPartial'
import AddNewFlightPartial from './AddNewFlightPartial'
import forceLogin from './mixins/force_login'

export default {
    data() {
        return {
            flights: [],
            error: "",
            polling: null,
            loading: true,
        }
    },
    computed: {
        noFlights() {
            return this.flights.length == 0;
        }
    },
    methods: {
        updateFlights() {
            return axios
                .get('api/flights', {
                    headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                })
                .then(response => this.flights = response.data)
                .catch(error => this.error = error);
        },
    },
    created() {
        this.updateFlights().then(() => this.loading = false);
        this.polling = setInterval(() => {
            this.updateFlights();
        }, 2000);
    },
    beforeDestroy() {
        clearInterval(this.polling)
    },
    components: { FlightPartial, AddNewFlightPartial },
    mixins: [forceLogin]
}
</script>