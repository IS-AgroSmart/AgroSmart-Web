<template>
    <div class="col-md-4">
        <b-card :title="flight.name" class="my-3">
    
            <b-card-text>
                <b-spinner variant="warning" type="grow" v-if="isWaiting" title="Suba imágenes al vuelo para comenzar"></b-spinner>
                <b-spinner variant="success" type="grow" v-if="isBusy" title="En proceso"></b-spinner>
                <span v-if="isBusy">{{progress}}</span>
                <b-spinner variant="danger" type="grow" v-if="isErrored" title="Error!"></b-spinner>
                <span style="white-space: pre;">{{flight.annotations}}</span>
            </b-card-text>
    
            <b-button v-if="!deleted" :to="{name: 'flightDetails', params: {uuid: flight.uuid}}" variant="primary">Ver detalles</b-button>
            <b-button v-else @click="deleteFlight" variant="danger">Eliminar</b-button>
        </b-card>
    </div>
</template>

<script>
import axios from 'axios'
import forceLogin from './mixins/force_login'

export default {
    data() {
        return {

        };
    },
    computed: {
        progress() {
            if (this.flight.state != "PROCESSING") {
                return ""
            }
            return " (" + this.flight.nodeodm_info.progress.toFixed(0) + "%) ";
        },
        isWaiting() {
            return this.flight.state == "WAITING"
        },
        isBusy() {
            return this.flight.state == "PROCESSING"
        },
        isErrored() {
            return this.flight.state == "ERROR"
        },
    },
    methods: {
        deleteFlight() {
            axios.delete("api/flights/" + this.flight.uuid, {
                headers: { "Authorization": "Token " + this.storage.token }
            }).then(() => this.$router.replace("/flights/deleted"))
        }
    },
    props: {
        flight: { type: Object },
        deleted: { type: Boolean, default: false }
    },
    mixins: [forceLogin]
}
</script>