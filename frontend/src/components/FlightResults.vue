<template>
    <div>
        <h1>Artefactos de {{ flight.name }}</h1>
    
        <b-alert variant="danger" v-if="error" show>{{error}}</b-alert>
    
        <div v-for="(artifact, index) in artifacts" :key="index" class="row my-3">
            <div class="col text-center">
                <b-button :href="link(index)" download variant="outline-primary">{{artifact}}</b-button>
            </div>
        </div>
        <div class="row my-5">
            <div class="col-md-6 text-right">
                <b-button class="my-3 mx-5" variant="primary">Descargar</b-button>
            </div>
            <div class="col-md-6 text-left">
                <b-button class="my-3 mx-5" variant="primary">Reporte</b-button>
            </div>
        </div>
    </div>
</template>

<script>
import axios from 'axios'
import forceLogin from './mixins/force_login'

const baseUrl = window.location.protocol + "//" + window.location.hostname + "/api/downloads/";
export default {
    data() {
        return {
            flight: {},
            error: "",
            artifacts: ["Ortomosaico (PNG)", "Ortomosaico (GeoTIFF)", "Modelo 3D"],
            downloads: [false, false],
            urls: ["/orthomosaic.png", "/orthomosaic.tiff", "/3dmodel"]
        };
    },
    methods: {
        link(index) {
            return baseUrl + this.flight.uuid + this.urls[index];
        }
    },
    created() {
        axios
            .get("api/flights/" + this.$route.params.uuid, {
                headers: { "Authorization": "Token " + this.storage.token }
            })
            .then(response => (this.flight = response.data))
            .catch(error => this.error = error);
    },
    mixins: [forceLogin]
}
</script>