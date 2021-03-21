<template>
    <div class="pt-3" style="padding-left:15px; padding-right:15px;">
        <b-alert v-if="error" show variant="danger">
            Error al cambiar contraseña: las contraseñas no coindicen o no se cumplen las condiciones requeridas
        </b-alert>
        <b-form @submit="onSubmit">
            <b-form-group id="input-group-1" label="Nueva Contraseña:" label-for="input-1">
                <b-form-input id="input-1" v-model="form.password" :state="passwordState" type="password" required placeholder="Escriba su nueva contraseña"></b-form-input>
                <b-form-invalid-feedback id="input-live-feedback">
                    Escriba una contraseña de al menos 8 caracteres
                </b-form-invalid-feedback>
            </b-form-group>
    
            <b-form-group id="input-group-2" label="Repetir Contraseña Nueva:" label-for="input-2">
                <b-form-input id="input-2" v-model="form.repeatedPassword" :state="passwordRepeatedState" type="password" required placeholder="Confirme su nueva contraseña"></b-form-input>
                <b-form-invalid-feedback id="input-live-feedback">
                    Las contraseñas no coinciden
                </b-form-invalid-feedback>
            </b-form-group>
    
            <b-container>
                <b-row align-h="center">
                    <b-col cols="5" class="text-center">
                        <b-button type="submit" variant="primary">Aceptar</b-button>
                    </b-col>
                    <b-col cols="5" class="text-center">
                        <b-button @click="goToProfile" variant="secondary">Cancelar</b-button>
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
                password: '',
                repeatedPassword: '',
            },
            error: false,
            errorConfirmation: false,
        }
    },
    computed: {
        passwordState() {
            if (this.form.password.length == 0) return null;
            return this.form.password.length >= 8;
        },
        passwordRepeatedState() {
            if (this.form.repeatedPassword.length == 0) return null;
            return this.form.password == this.form.repeatedPassword;
        },
    },
    methods: {
        onSubmit(evt) {
            if (this.form.password != this.form.repeatedPassword || this.form.password.length < 8) {
                this.error = true;
            } else {
                evt.preventDefault()
                axios.post("api/users/" + this.storage.loggedInUser.pk + "/set_password/", {
                        "password": this.form.repeatedPassword,
                    }, { headers: { "Authorization": "Token " + this.storage.token } })
                    .then(() => this.goToProfile())
                    .catch(error => this.error = error.response ? this.errorToLines(error.response.data) : error);
            }
        },
        goToProfile() {
            this.$router.replace({ path: '/profile' });
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