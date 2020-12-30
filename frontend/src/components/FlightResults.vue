<template>
    <div v-if="flight" class=" pt-3" style="padding-left:15px; padding-right:15px;">
        <h1>Artefactos de {{ flight.name }}</h1>
    
        <b-alert variant="danger" v-if="error" show>{{error}}</b-alert>
    
        <div v-for="(artifact, index) in artifacts" :key="index" class="row my-3">
            <div class="col text-center">
                <b-button :href="link(index)" download variant="outline-primary">{{artifact}}</b-button>
            </div>
        </div>
        <div class="row my-3">
            <div class="col text-center">
                <b-button variant="outline-primary" :to="{name: 'flightReport', params: {uuid: this.flight.uuid}}">Reporte</b-button>
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
            artifacts: ["Ortomosaico (PNG)", "Ortomosaico (GeoTIFF)", "Modelo 3D (PLY)","Nube de puntos (PLY)", "Modelo Digital de Superficie (TIF)", "Modelo Digital de Terreno (TIF)"],
            downloads: [false, false],
            urls: ["/orthomosaic.png", "/orthomosaic.tiff", "/3dmodel","/pointcloud.ply","/dsm.tif", "/dtm.tif"]

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
                headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
            })
            .then(response => this.flight = response.data)
            .catch(error => this.error = error);
    },
    mixins: [forceLogin]
}
</script>