<template>
    <div>
        <div v-if="error">Error! Usuario o contraseña incorrectos</div>
        <b-form @submit="onSubmit">
            <b-form-group id="input-group-1" label="Usuario:" label-for="input-1">
                <b-form-input id="input-1" v-model="form.username" type="text" required placeholder="Nombre de usuario"></b-form-input>
            </b-form-group>
    
            <b-form-group id="input-group-2" label="Contraseña:" label-for="input-2">
                <b-form-input id="input-2" type="password" v-model="form.password" required placeholder="Contraseña"></b-form-input>
            </b-form-group>
    
            <b-button type="submit" variant="primary">Iniciar</b-button>
        </b-form>
    </div>
</template>

<script>
import axios from "axios";

export default {
    data() {
        return {
            form: {
                username: '',
                password: '',
            },
            error: false
        }
    },
    methods: {
        onSubmit(evt) {
            evt.preventDefault()
            axios.post("api/api-auth", {
                    "username": this.form.username,
                    "password": this.form.password
                })
                .then(response => {
                    this.storage.token = response.data.token;
                    this.$forceUpdate;
                    this.$router.go(-1);
                })
                .catch(error => this.error = error);
        },
    }
}
</script>