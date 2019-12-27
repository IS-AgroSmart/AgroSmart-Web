<template>
    <div class="col-md-4">
        <b-card :title="flight.name" class="my-3">
    
            <b-card-text>
                <b-spinner variant="success" type="grow" v-if="isBusy(flight)"></b-spinner>{{flight.annotations}}
            </b-card-text>
    
            <b-button :to="{name: 'flightDetails', params: {uuid: flight.uuid}}" variant="primary">Ver detalles</b-button>
        </b-card>
    </div>
</template>

<script>
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
    methods: {
        isBusy(flight) {
            return flight.state == "PROCESSING"
        },
    },
    props: ["flight"]
}
</script>