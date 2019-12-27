<template>
    <div>
        <h1>
            {{ flight.name }}
            <small>{{ [flight.date, "YYYY-MM-DD"] | moment("dddd D [de] MMMM, YYYY") }}</small>
            <small class="mx-5"><b-button variant="danger" @click="deleteFlight">Eliminar</b-button></small>
        </h1>
    
    
        <div class="row my-5">
            <div class="col-sm-4">
                <h4>Notas</h4>
                <p>{{flight.annotations}}</p>
            </div>
            <div class="col-sm-4">
                <h4>Consola</h4>
                <b-form-textarea id="textarea" v-model="console" rows="15" readonly ref='consoleDisplay'></b-form-textarea>
            </div>
            <div class="col-sm-4">
                <b-list-group>
                    <b-list-group-item><span class="font-weight-bold">Cámara: </span>{{friendlyCamera}}</b-list-group-item>
                    <b-list-group-item>Dapibus ac facilisis in</b-list-group-item>
                    <b-list-group-item>Morbi leo risus</b-list-group-item>
                    <b-list-group-item>Porta ac consectetur ac</b-list-group-item>
                    <b-list-group-item>Vestibulum at eros</b-list-group-item>
                </b-list-group>
            </div>
        </div>
    </div>
</template>

<script>
import axios from 'axios'

export default {
    data() {
        return {
            flight: null,
            console: "",
            info: {}
        };
    },
    methods: {
        updateStatus() {
            axios.get("nodeodm/task/" + this.$route.params.uuid + "/output", {
                    headers: { "Authorization": "Token " + this.storage.token }
                })
                .then(response => (this.console = ("error" in response.data) ? response.data.error : response.data))
                .catch(error => this.error = error);

            axios.get("nodeodm/task/" + this.$route.params.uuid + "/info", {
                    headers: { "Authorization": "Token " + this.storage.token }
                })
                .then(response => (this.info = ("error" in response.data) ? response.data.error : response.data))
                .catch(error => this.error = error);
        },
        deleteFlight() {
            axios.delete("api/flights/" + this.flight.uuid, {
                    headers: { "Authorization": "Token " + this.storage.token }
                }).then(() => this.$router.push("/flights"))
        }
    },
    computed: {
        cameras() {
            let cams = {};
            this.$cameras.forEach(cam =>
                cams[cam.value] = cam.text
            );
            return cams;
        },
        friendlyCamera() {
            return this.cameras[this.flight.camera]
        }
    },
    watch: {
        flight: function() {
            if (this.flight.state == "WAITING") {
                this.$router.replace({ "name": "uploadImages", params: { "uuid": this.flight.uuid } })
            }
        },
    },
    created() {
        if (!this.$isLoggedIn()) {
            this.$router.push("/login");
        }

        axios
            .get("api/flights/" + this.$route.params.uuid, {
                headers: { "Authorization": "Token " + this.storage.token }
            })
            .then(response => (this.flight = response.data))
            .catch(error => this.error = error);

        this.$nextTick(function() {
            window.setInterval(() => {
                this.updateStatus();
            }, 1000);
        });
    }
}
</script>