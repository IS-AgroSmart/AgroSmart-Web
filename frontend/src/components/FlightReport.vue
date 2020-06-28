<template>
    <div>
        <h1>Reporte del vuelo {{ flight.name }}</h1>
    
        <b-alert variant="danger" v-if="error" show>{{error}}</b-alert>
    
        <b-row>
            <b-col class="d-flex">
                <b-form @submit="downloadReport" class="mx-auto">
                    <b-form-group>
                        <b-form-checkbox-group v-model="selected" :options="options" switches stacked></b-form-checkbox-group>
                    </b-form-group>
    
                    <b-button type="submit" variant="primary">Descargar</b-button>
                </b-form>
            </b-col>
        </b-row>
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
            selected: ["generaldata", "orthomosaic"],
            options: [
                { text: 'Datos generales', value: 'generaldata' },
                { text: 'Ortomosaico', value: 'orthomosaic' },
                { text: 'Nube de puntos', value: 'pointcloud', disabled: true },
                { text: 'Modelo 3D', value: '3dmodel', disabled: true },
                { text: 'Ortomosaico NDVI', value: 'ndviortho', disabled: true },
            ]
        };
    },
    computed: {
        selectedSections() {
            var dict = {}
            for (let section of this.selected) dict[section] = "true";
            return dict;
        },
    },
    methods: {
        link(index) {
            return baseUrl + this.flight.uuid + this.urls[index];
        },
        downloadReport(evt) {
            evt.preventDefault();

            axios.get("api/downloads/" + this.flight.uuid + "/report.pdf", {
                    responseType: "blob",
                    params: this.selectedSections
                })
                .then(response => {
                    var fileURL = window.URL.createObjectURL(new Blob([response.data]));
                    var fileLink = document.createElement('a');
                    fileLink.href = fileURL;
                    fileLink.setAttribute('download', 'report_' + this.flight.uuid + '.pdf');
                    document.body.appendChild(fileLink);
                    fileLink.click();
                })
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