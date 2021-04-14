<template>
    <div class=" pt-3" style="padding-left:15px; padding-right:15px;">
        <b-alert v-if="error" show variant="danger" data-cy="alert">
            Error! Usuario o contraseña incorrectos
        </b-alert>
        <b-form @submit="onSubmit">
            <b-form-group id="input-group-1" label="Usuario:" label-for="input-1">
                <b-form-input id="input-1" v-model="form.username" type="text" required placeholder="Nombre de usuario" data-cy="username"></b-form-input>
            </b-form-group>
    
            <b-form-group id="input-group-2" label="Contraseña:" label-for="input-2">
                <b-form-input id="input-2" type="password" v-model="form.password" required placeholder="Contraseña" data-cy="password"></b-form-input>
            </b-form-group>
    
            <b-container>
                <b-row align-h="center">
                    <b-col cols="3" class="text-center">
                        <b-button type="submit" variant="primary" data-cy="login">Iniciar sesión</b-button>
                    </b-col>
                    <b-col cols="3" class="text-center">
                        <b-button to="signUp" variant="secondary">Crear cuenta</b-button>
                    </b-col>
                    <b-col cols="3" class="text-center">
                        <b-button to="restorePassword" variant="warning">Olvidé mi contraseña</b-button>
                    </b-col>
                </b-row>
            </b-container>
        </b-form>
    </div>
</template>

<script>
import axios from "axios";
import { getUserInfo } from "../api/users"

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
                .then((tokenResponse) => {
                    this.storage.token = tokenResponse.data.token;
                    return getUserInfo(this.storage.token, this.form.username);
                }).then(([user, err]) => {
                    if (err != null) {
                        this.error = err;
                    } else {
                        this.storage.loggedInUser = user;
                        this.$router.back();
                    }
                })
                .catch(error => this.error = error);
        },
    }
}
</script>
