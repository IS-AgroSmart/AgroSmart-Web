<template>
    <div>
        <b-alert v-if="error" show variant="danger">
            Error! 
        </b-alert>
        <b-form @submit="onSubmit">
            <b-form-group id="input-group-1" label="Nueva Contraseña:" label-for="input-1">
                <b-form-input id="input-1" v-model="form.password" type="password" required placeholder="Escriba su nueva contraseña"></b-form-input>
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
                password: '',
            },
            error: false
        }
    },
    computed: {
        usernameState() {
            if (this.form.password.length == 0) return null;
            return this.form.password.indexOf(" ") == -1;
        },
    },
    methods: {
        onSubmit(evt) {
            evt.preventDefault()
            axios.post("/api/password_reset/reset_password/confirm/", {
                    "token": this.$route.query.token, 
                    "password": this.form.password,
                })
                .then(response => {
                    if (response.status == 200)
                        this.goBack();
                    else
                        this.error = this.errorToLines(response.body);
                })
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