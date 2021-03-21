<template>
    <div class=" pt-3" style="padding-left:15px; padding-right:15px;">
        <b-alert v-if="error" show variant="danger">
            <p>Error en la creación de cuenta</p>
            <span style="white-space: pre;">{{ error }}</span>
        </b-alert>
        <b-form @submit="onSubmit">
            <b-form-group id="input-group-1" label="Usuario:" label-for="input-1">
                <b-form-input id="input-1" v-model="form.username" :state="usernameState" type="text" required placeholder="Nombre de usuario. Usado para iniciar sesión."></b-form-input>
                <b-form-invalid-feedback id="input-live-feedback">
                    El nombre de usuario no puede contener espacios.
                </b-form-invalid-feedback>
            </b-form-group>
    
            <b-form-group id="input-group-2" label="Nombres:" label-for="input-2">
                <b-form-input id="input-2" type="text" v-model="form.first_name" :state="firstNameState" required placeholder="Nombres y Apellidos"></b-form-input>
                <b-form-invalid-feedback id="input-live-feedback">
                    El nombre y apellido no puede superar los 150 caracteres
                </b-form-invalid-feedback>
            </b-form-group>
    
            <b-form-group id="input-group-2" label="Contraseña:" label-for="input-3">
                <b-form-input id="input-3" type="password" v-model="form.password" :state="passwordState" required placeholder="Contraseña"></b-form-input>
                <b-form-invalid-feedback id="input-live-feedback">
                    Escriba una contraseña de al menos 8 caracteres
                </b-form-invalid-feedback>
            </b-form-group>
    
            <b-form-group id="input-group-2" label="E-mail:" label-for="input-4">
                <b-form-input id="input-4" type="email" v-model="form.email" required placeholder="E-mail para enviar notificaciones"></b-form-input>
            </b-form-group>
    
            <b-form-group id="input-group-2" label="Organización:" label-for="input-5">
                <b-form-input id="input-5" type="text" v-model="form.organization" :state="organizationState" required placeholder="Nombre Organización"></b-form-input>
                <b-form-invalid-feedback id="input-live-feedback">
                    Escriba el nombre de su Organización en menos de 20 caracteres
                </b-form-invalid-feedback>
            </b-form-group>
    
            <b-container>
                <b-row align-h="center">
                    <b-col cols="5" class="text-center">
                        <b-button type="submit" variant="primary" :disabled="!everythingValid">Crear cuenta</b-button>
                    </b-col>
                    <b-col cols="5" class="text-center">
                        <b-button @click="goBack" variant="secondary">Cancelar</b-button>
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
                first_name: '',
                organization: '',
            },
            error: false
        }
    },
    computed: {
        usernameState() {
            if (this.form.username.length == 0) return null;
            return this.form.username.indexOf(" ") == -1;
        },
        firstNameState() {
            if (this.form.first_name.length == 0) return null;
            return this.form.first_name.length <= 150;
        },
        passwordState() {
            if (this.form.password.length == 0) return null;
            return this.form.password.length >= 8;
        },
        organizationState() {
            if (this.form.organization.length == 0) return null;
            return this.form.organization.length <= 20;
        },
        everythingValid() {
            return this.usernameState && this.firstNameState && this.passwordState && this.organizationState;
        },
    },
    methods: {
        onSubmit(evt) {
            evt.preventDefault();
            axios.post("api/users/", {
                    "username": this.form.username,
                    "password": this.form.password,
                    "email": this.form.email,
                    "first_name": this.form.first_name,
                    "organization": this.form.organization,
                })
                .then(response => {
                    if (response.status == 201)
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