<template>
    <div>
        <h1>Nueva Contraseña</h1>

        <b-alert v-if="error" show variant="danger">
            <p>Error al recuperar contraseña</p>
            <span style="white-space: pre;">{{ error }}</span>
        </b-alert>
        <b-form @submit="onSubmit">
            <p>Recuerde escribir una contraseña con mas de 8 caracteres</p>
            <b-form-group id="input-group-1" label="Nueva Contraseña:" label-for="input-1">
                <b-form-input id="input-1" v-model="form.password" type="password" required placeholder="Escriba su nueva contraseña"></b-form-input>
            </b-form-group>
        
            <b-container>
                <b-row align-h="center">
                    <b-col cols="5" class="text-center">
                        <b-button type="submit" variant="primary">Enviar</b-button>
                    </b-col>
                    <b-col cols="5" class="text-center">
                        <b-button @click="goToLogin" variant="secondary">Cancelar</b-button>
                    </b-col>
                </b-row>
            </b-container>
        </b-form>
    </div> 
</template>>

<script>
import axios from "axios";

export default {
    data() {
        return {
            form: {
                password: '',
            },
            error: false
        }
    },
    computed: {
        usernameState() {
            if (this.form.password.length < 8) return null;
            return this.form.password.indexOf(" ") == -1;
        },
    },
    methods: {
        onSubmit(evt) {
            evt.preventDefault()
            axios.post("/api/password_reset/confirm/", {
                    "token": this.$route.query.token, 
                    "password": this.form.password,
                })
                .then(response => {
                    if (response.status == 200)
                        this.goToLogin();                         
                    else
                        this.error = this.errorToLines(response.body);
                })
                .catch(error => {
                    this.error = error.response ? this.errorToLines(error.response.data) : error;
                });
        },
        goToLogin() {
            this.$router.replace({ path: '/login' });
        },
        errorToLines(body) {
            var err = "";
            for (var field in body) {
                for (var error of body[field]) {
                    err += field + ": " + error + "\n";
                }
            }
            return err;
        }
    }
}
</script>