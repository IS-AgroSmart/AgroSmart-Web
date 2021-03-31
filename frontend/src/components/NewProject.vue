<template>
    <div class=" pt-3" style="padding-left:15px; padding-right:15px;">
        <b-alert v-if="error" variant="danger" show>{{error}}</b-alert>
        <b-form @submit="onSubmit">
            <b-form-group id="input-group-1" label="Nombre:" label-for="input-1">
                <b-form-input id="input-1" v-model="form.name" type="text" required placeholder="Nombre del proyecto"></b-form-input>
            </b-form-group>
            <b-form-group id="input-group-2" label="Descripción:" label-for="input-2">
                <b-form-textarea id="input-2" v-model="form.description" placeholder="Describa el proyecto" rows="4" required></b-form-textarea>
            </b-form-group>
            <b-form-group id="input-group-3" label="Vuelos:" label-for="input-3">
                <div :class="{ 'invalid': !sameCamera }">
                    <multiselect id="input-3" v-model="form.flights" :options="flights" label="name" :custom-label="flightLabel" track-by="uuid" value-field="uuid" placeholder="Escoja al menos un vuelo" multiple :state="sameCamera"></multiselect>
                    <small class="form-text text-danger" v-if="!sameCamera">Todos los vuelos de un mismo proyecto deben haber usado la misma cámara</small>
                    <small class="form-text text-muted">Seleccione uno o varios vuelos con Ctrl.</small>
                </div>
            </b-form-group>
    
            <b-button type="submit" variant="primary" :disabled="!anyFlights || !sameCamera">Submit</b-button>
        </b-form>
    </div>
</template>

<style src="vue-multiselect/dist/vue-multiselect.min.css">

</style>

<style>
.invalid .multiselect__tags {
    border-color: red;
}
</style>

<script>
import axios from "axios";

export default {
    data() {
        return {
            form: {
                name: "",
                description: "",
                flights: [],
                artifacts: {}
            },
            error: "",
            flights: [],
            artifacts: {},
        };
    },
    methods: {
        onSubmit(evt) {
            evt.preventDefault();
            if (!this.$isLoggedIn()) {
                this.$router.push("/login");
                return;
            }
            var fd = new FormData();
            fd.set("name", this.form.name);
            fd.set("description", this.form.description);
            // HACK: DRF needs this for ManyToMany, otherwise it gets nervous
            for (var flight of this.form.flights) {
                fd.append("flights", flight.uuid);
            }
            axios
                .post("api/projects/", fd, {
                    headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                })
                .then(() => this.$router.push("/projects"))
                .catch(error => this.error = "ERROR: " + error.response.data.name[0]);
        },
        flightLabel(flight) {
            let cameraName = this.$cameras.find((x) => x.value == flight.camera).text;
            return `${flight.name} (${cameraName})`
        },
        _isCandidate(flight) {
            return flight.state == "COMPLETE" && !flight.is_demo
        }
    },
    computed: {
        anyFlights: function() {
            return this.form.flights.length > 0;
        },
        sameCamera: function() {
            if (!this.anyFlights) return true;
            return this.form.flights.every((flight) => flight.camera == this.form.flights[0].camera);
        }
    },
    created() {
        axios
            .get("api/flights", {
                headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
            })
            .then(response => (this.flights = response.data.filter(this._isCandidate)))
            .catch(error => (this.error = error));
    }
};
</script>