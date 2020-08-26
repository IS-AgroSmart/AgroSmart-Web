<template>
    <div class=" pt-3" style="padding-left:15px; padding-right:15px;">
        <b-alert v-if="error" variant="danger" show>{{error}}</b-alert>
        <b-form @submit="onSubmit">
            <b-form-group id="input-group-1" label="Nombre:" label-for="input-1">
                <b-form-input id="input-1" v-model="form.name" type="text" required placeholder="Nombre del vuelo"></b-form-input>
            </b-form-group>
            <b-form-group id="input-group-2" label="Fecha:" label-for="input-2">
                <b-form-datepicker id="input-2" v-model="form.date"></b-form-datepicker>
            </b-form-group>
            <b-form-group id="input-group-3" label="Cámara:" label-for="input-3" description="Escoja RGB si no está seguro">
                <b-form-select id="input-3" v-model="form.camera" :options="cameras" required></b-form-select>
            </b-form-group>
            <b-form-group id="input-group-4" label="Anotaciones:" label-for="input-4">
                <b-form-textarea id="input-4" v-model="form.annotations" placeholder="Escriba notas del vuelo..." rows="5" required></b-form-textarea>
            </b-form-group>
    
            <b-button type="submit" variant="primary">Submit</b-button>
        </b-form>
    </div>
</template>

<script>
import axios from 'axios'
import forceLogin from './mixins/force_login'

export default {
    data() {
        return {
            form: {
                name: '',
                date: this.$moment().format("YYYY-MM-DD"),
                camera: "RGB",
                multispectral: false,
                annotations: "",
                state: "WAITING",
            },
            error: "",
            cameras: this.$cameras,
        }
    },
    methods: {
        onSubmit(evt) {
            evt.preventDefault()
            if (!this.$isLoggedIn()) {
                this.$router.push("/login");
            }

            axios
                .post("api/flights/", this.form, {
                    headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                })
                .then(response => {
                    this.$router.replace({ "name": "uploadImages", params: { "uuid": response.data.uuid } })
                })
                .catch(() => this.error = "ERROR: Verifique que no exista un vuelo con el mismo nombre");
        }
    },
    mixins: [forceLogin]
}
</script>