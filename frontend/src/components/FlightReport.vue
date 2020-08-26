<template>
    <div class=" pt-3" style="padding-left:15px; padding-right:15px;">
        <h1>Reporte del vuelo {{ flight.name }}</h1>
    
        <b-alert variant="danger" v-if="error" show>{{error}}</b-alert>
    
        <b-row>
            <b-col class="d-flex">
                <b-form @submit="downloadReport" class="mx-auto">
                    <b-form-group>
                        <b-form-checkbox-group v-model="selected" switches stacked>
                            <!-- Wrap on div to show Disabled tooltip -->
                            <div v-for="option in options" :key="option.value" :title="option.disabled ? 'Esta sección no está disponible en este vuelo' : ''" b-v-tooltip>
                                <b-form-checkbox :value="option.value" :disabled="option.disabled">{{option.text}}</b-form-checkbox>
                            </div>
                        </b-form-checkbox-group>
                    </b-form-group>
    
                    <b-button :disabled="!someSectionsSelected" type="submit" variant="primary" :title="downloadButtonTooltip" b-v-tooltip>Descargar</b-button>
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
                { text: 'Modelo de elevación', value: 'dsm' },
                { text: 'Nube de puntos', value: 'pointcloud', disabled: true },
                { text: 'Modelo 3D', value: '3dmodel', disabled: true },
                { text: 'Ortomosaico NDVI', value: 'ndviortho', disabled: true },
            ]
        };
    },
    computed: {
        selectedSections() {
            var dict = {};
            for (let section of this.selected) dict[section] = "true";
            return dict;
        },
        someSectionsSelected() { return this.selected.length > 0; },
        downloadButtonTooltip() { return this.someSectionsSelected ? "" : "Seleccione al menos una sección" }
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
                .catch(error => this.error = error);
        }
    },
    created() {
        axios
            .get("api/flights/" + this.$route.params.uuid, {
                headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
            })
            .then(response => (this.flight = response.data))
            .catch(error => this.error = error);

    },
    mixins: [forceLogin]
}
</script>