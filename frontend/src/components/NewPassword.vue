<template>
    <div class=" pt-3" style="padding-left:15px; padding-right:15px;">
        <h1>Nueva Contraseña</h1>
    
        <b-alert v-if="error" show variant="danger">
            <p>Error al recuperar contraseña</p>
            <span style="white-space: pre;">{{ error }}</span>
        </b-alert>
        <b-form @submit="onSubmit">
            <b-form-group id="input-group-1" label="Nueva Contraseña:" label-for="input-1">
                <b-form-input id="input-1" v-model="form.password" type="password" :state="passwordState" required placeholder="Escriba su nueva contraseña"></b-form-input>
                <b-form-invalid-feedback>
                    Escriba una contraseña de al menos 8 caracteres
                </b-form-invalid-feedback>
            </b-form-group>
    
            <b-container>
                <b-row align-h="center">
                    <b-col cols="5" class="text-center">
                        <b-button type="submit" variant="primary" :disabled="!everythingValid">Enviar</b-button>
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
        passwordState() {
            if (this.form.password.length == 0) return null;
            return this.form.password.length >= 8;
        },
        everythingValid() {
            return !!this.passwordState;
        },
    },
    methods: {
        onSubmit(evt) {
            evt.preventDefault()
            axios.post("/api/password_reset/confirm/", {
                    "token": this.$route.query.token,
                    "password": this.form.password,
                })
                .then(() => this.goToLogin())
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