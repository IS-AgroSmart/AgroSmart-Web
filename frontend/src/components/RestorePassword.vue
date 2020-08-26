<template>
    <div class=" pt-3" style="padding-left:15px; padding-right:15px;">
        <h1>Resetar Contraseña</h1>
    
        <b-alert v-if="error" show variant="danger">
            Error! Verifique que el correo ingresado este vinculado con una cuenta de AgroSmart.
        </b-alert>
        <b-form @submit="onSubmit">
            <p>Recuerde usar el correo vinculado a su cuenta de AgroSmart.</p>
            <b-form-group id="input-group-2" label="E-mail:" label-for="input-2">
                <b-form-input id="input-2" type="email" v-model="form.email" required placeholder="E-mail para enviar notificaciones"></b-form-input>
            </b-form-group>
    
            <b-container>
                <b-row align-h="center">
                    <b-col cols="5" class="text-center">
                        <b-button type="submit" variant="primary">Enviar</b-button>
                    </b-col>
                    <b-col cols="5" class="text-center">
                        <b-button @click="goBack" variant="secondary">Cancelar</b-button>
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
                email: '',
            },
            error: false
        }
    },
    methods: {
        onSubmit(evt) {
            evt.preventDefault()
            axios.post("api/password_reset/", {
                    "email": this.form.email,
                })
                .then(() => this.goBack())
                .catch(error => {
                    this.error = error.response ? this.errorToLines(error.response.data) : error;
                });
        },
        goBack() {
            this.$router.go(-1);
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