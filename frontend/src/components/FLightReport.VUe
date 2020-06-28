<template>
    <div>
        <h1>Reporte del vuelo {{ flight.name }}</h1>
    
        <b-alert variant="danger" v-if="error" show>{{error}}</b-alert>
    
        <div class="row my-3">
            <div class="col text-center">
                <input type="checkbox" id="element1" name="elemento 1" value="Ortomosaico">
                <label for="element1"> Detalles Ortomosaico </label><br>
                <input type="checkbox" id="element2" name="elemento 2" value="Nube de puntos">
                <label for="element2"> Detalles nube de puntos </label><br>
                <input type="checkbox" id="element3" name="elemento 3" value="Modelo 3D">
                <label for="element3"> Detalles modelo 3D </label><br>
                <input type="checkbox" id="element4" name="elemento 4" value="Ortomosaico RGB">
                <label for="element4"> Ortomosaico RGB </label><br>
                <input type="checkbox" id="element5" name="elemento 5" value="Ortomosaico NDVI">
                <label for="element5"> Ortomosaico NDVI </label><br>
            </div>
        </div>
        <div class="row my-5">
            <div class="col-md-6 text-center">
                <b-button class="my-3 mx-5" variant="primary">Descargar</b-button>
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
            artifacts: ["Ortomosaico (GeoTIFF)", "Modelo 3D"],
            downloads: [false],
            urls: ["/report.pdf"]
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
        axios.get("/reports/report.pdf")
    },
    mixins: [forceLogin]
}
</script>