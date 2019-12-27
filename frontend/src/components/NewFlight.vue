<template>
    <div>
        <b-form @submit="onSubmit">
            <b-form-group id="input-group-1" label="Nombre:" label-for="input-1">
                <b-form-input id="input-1" v-model="form.name" type="text" required placeholder="Nombre del vuelo"></b-form-input>
            </b-form-group>
            <b-form-group id="input-group-2" label="Fecha:" label-for="input-2">
                <b-form-input id="input-2" v-model="form.date" type="date" required></b-form-input>
            </b-form-group>
            <b-form-group id="input-group-3" label="Cámara:" label-for="input-3">
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

export default {
    data() {
        return {
            form: {
                name: '',
                date: null,
                camera: "",
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
                    headers: { "Authorization": "Token " + this.storage.token },
                })
                .then(response => {
                    window.console.log(response);
                    this.$router.push({ "name": "uploadImages", params: { "uuid": response.data.uuid } })
                })
                .catch(error => this.error = error)
        }
    }
}
</script>