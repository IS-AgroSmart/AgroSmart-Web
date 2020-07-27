<template>
    <div class="my-4">
        <h1>Solicitudes pendientes</h1>
        <b-form>
            <b-form-input v-model="opcionFilter" placeholder="Buscar usuarios por nombre o email..."></b-form-input>
        </b-form>
    
        <b-alert v-if="availableUsers.length === 0" show variant="info">
            ¡Ningún usuario demo tiene ese nombre o email!
        </b-alert>
    
        <div class="row">
            <b-card v-for="user in availableUsers" :key="user.pk" class="card">
                <b-card-title><strong>{{ user.username }}</strong></b-card-title>
                <b-card-text>
                    <p>Correo: {{user.email}}</p>
                    <p>Estado: El usuario aún <strong>no ha sido aceptado</strong></p>
    
                    <b-dropdown text="Acciones" ref="dropdown">
                        <b-dropdown-item-button v-for="accion in acciones" :key="accion.pk" @click='accionRequest(user,accion)'>
                            {{ accion }}
                        </b-dropdown-item-button>
                    </b-dropdown>
                </b-card-text>
            </b-card>
        </div>
        <b-alert variant="success" show v-if="alert">Acción realizada con éxito</b-alert>
    </div>
</template>

<script lang="js">
import axios from "axios";

export default {
    name: 'user-requests',

    data: function() {
        return {
            demoUser_img: "data:image/png;base64,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",
            users: [],
            acciones: ['Aceptar', 'Rechazar'],
            opcionFilter: '',
            alert: false,
        }
    },


    methods: {
        loadUsers() {
            axios.get('api/users', {
                    headers: { "Authorization": "Token " + this.storage.token }
                })
                .then(response => {
                    this.users = response.data
                })
                .catch(error => this.error = error);
        },
        patchUser(user, newType) {
            axios.patch("api/users/" + user.pk + "/", { type: newType, }, {
                    headers: { "Authorization": "Token " + this.storage.token },
                }).then(() => this.loadUsers())
                .catch(() => {
                    this.$bvToast.toast('Error al procesar la solicitud. Intente más tarde', {
                        title: "Error",
                        autoHideDelay: 3000,
                        variant: "danger",
                    });
                });
        },
        accionRequest(user, accion) {
            if (accion == "Rechazar") {
                this.$bvModal.msgBoxConfirm('Esta solicitud perteneciente a ' + user.username + " será eliminada", {
                        title: '¿Realmente desea eliminar la solicitud?',
                        okVariant: 'danger',
                        okTitle: 'Sí',
                        cancelTitle: 'No',
                        // hideHeaderClose: false
                    })
                    .then(value => {
                        if (value) this.patchUser(user, "DELETED");
                    });
            } else {
                this.patchUser(user, "ACTIVE");
            }
        },
    },
    computed: {
        availableUsers() {
            if (this.opcionFilter) {
                return this.users.filter(user => !user.is_staff &&
                    user.type == "DEMO_USER" &&
                    (user.username.toLowerCase().indexOf(this.opcionFilter) > -1 ||
                        user.email.toLowerCase().indexOf(this.opcionFilter) > -1));
            } else {
                // Mostrar sólo los usuarios que no son administradores
                return this.users.filter(user => !user.is_staff && user.type == "DEMO_USER");
            }
        },

    },
    created() {
        if (!this.$isLoggedIn()) {
            this.$router.push("/login");
        }
        this.loadUsers();
    },
}
</script>

<style scoped lang="css">
.button {
    padding: 5px;
    margin: 5px;
}

.user_requests {
    width: 100%;
    height: 100%;
}

.card {
    padding: 5px;
    margin: 30px;
    width: auto;
    height: auto;
}

.row {
    padding: 1px;
    margin: 1px;
}

.image {
    width: 200px;
    height: 180px;
    padding: 5px;
}
</style>
