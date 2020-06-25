<template>
    <div>
        <b-alert v-if="error" show variant="danger">
            <p>Error en la creación de cuenta</p>
            {{ error }}
        </b-alert>
        <b-form @submit="onSubmit">
            <b-form-group id="input-group-1" label="Usuario:" label-for="input-1">
                <b-form-input id="input-1" v-model="form.username" :state="usernameState" type="text" required placeholder="Nombre de usuario. Usado para iniciar sesión."></b-form-input>
                <b-form-invalid-feedback id="input-live-feedback">
                    El nombre de usuario no puede contener espacios.
                </b-form-invalid-feedback>
            </b-form-group>
    
            <b-form-group id="input-group-2" label="Contraseña:" label-for="input-2">
                <b-form-input id="input-2" type="password" v-model="form.password" :state="passwordState" required placeholder="Contraseña"></b-form-input>
                <b-form-invalid-feedback id="input-live-feedback">
                    Escriba una contraseña de al menos 8 caracteres
                </b-form-invalid-feedback>
            </b-form-group>
    
            <b-form-group id="input-group-2" label="E-mail:" label-for="input-3">
                <b-form-input id="input-3" type="email" v-model="form.email" required placeholder="E-mail para enviar notificaciones"></b-form-input>
            </b-form-group>
    
            <b-container>
                <b-row align-h="center">
                    <b-col cols="5" class="text-center">
                        <b-button type="submit" variant="primary">Crear cuenta</b-button>
                    </b-col>
                </b-row>
            </b-container>
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
                email: '',
            },
            error: false
        }
    },
    computed: {
        usernameState() {
            if (this.form.username.length == 0) return null;
            return this.form.username.indexOf(" ") == -1;
        },
        passwordState() {
            if (this.form.password.length == 0) return null;
            return this.form.password.length >= 8;
        },
    },
    methods: {
        onSubmit(evt) {
            evt.preventDefault()
            axios.post("api/users/", {
                    "username": this.form.username,
                    "password": this.form.password,
                    "email": this.form.email,
                })
                .then(response => {
                    if (response.status == 201)
                        this.$router.go(-1);
                    else
                        this.error = response.body;
                })
                .catch(error => {
                    window.console.log(error);
                    this.error = error.response.data;
                });
        },
    }
}
</script>