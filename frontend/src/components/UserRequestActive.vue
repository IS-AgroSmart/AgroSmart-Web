<template>
  <div class="pt-3" style="padding-left:15px; padding-right:15px;">
    <h1>Usuarios Activos
            <b-dropdown ref="dropdown">
              <b-dropdown-item-button
              @click="onAdminClickUserDeleted()">
              <strong>Usuarios Eliminados</strong></b-dropdown-item-button>
            </b-dropdown>
    </h1>
    <b-form>
      <b-form-input v-model="opcionFilter" placeholder="Buscar usuarios por nombre o email..."></b-form-input>
    </b-form>

    <b-alert
      v-if="availableUsers.length === 0"
      show
      variant="info"
    >¡Ningún usuario activo tiene ese nombre o email!</b-alert>

    <div class="row">
      <b-card v-for="user in availableUsers" :key="user.pk" class="card">
        <img class="image" :src="image" />

        <b-card-title>
          <strong>{{ user.username }}</strong>
        </b-card-title>
        <b-card-text>
          <p>Correo: {{user.email}}</p>
          <p>
            Estado:
            <strong>{{user.type}}</strong>
          </p>

          <b-dropdown text="Acciones" ref="dropdown">
            <b-dropdown-item-button
              v-for="accion in acciones"
              :key="accion.pk"
              @click="accionRequest(user,accion)"
            >{{ accion }}</b-dropdown-item-button>
          </b-dropdown>
        </b-card-text>
      </b-card>
    </div>
    <b-alert variant="success" show v-if="alert">Acción realizada con éxito</b-alert>
  </div>
</template>

<script lang="js">
import axios from "axios";
import image from "../assets/icon-user-Demo.png"

export default {
    name: 'user-active-requests',

    data: function() {
        return {
            image:image,
            users: [],
            acciones: ['Eliminar'],
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
        },onAdminClickUserDeleted(){
            this.$router.push("/admin/userDeleted")
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
            let acciong='';
            if (accion == "Eliminar") {
                acciong='eliminado.'
                
            } else {
                acciong='restaurada y lista para ser aceptada';
            }
            this.$bvModal.msgBoxConfirm('El/la usuario ' + '"'+user.username + '"'+" será "+acciong, {
                        title: '¿Realmente desea '+accion+' la solicitud?',
                        okVariant: 'danger',
                        okTitle: 'Sí',
                        cancelTitle: 'No',
                        // hideHeaderClose: false
                    })
                    .then(value => {
                        if (value) this.patchUser(user, "DELETED");
                    });
        },
    },
    computed: {
        availableUsers() {
            if (this.opcionFilter) {
                return this.users.filter(user => (user.type == "ACTIVE" || user.type == "ADMIN") &&
                    (user.username.toLowerCase().indexOf(this.opcionFilter) > -1 ||
                        user.email.toLowerCase().indexOf(this.opcionFilter) > -1));
            } else {
                // Mostrar sólo los usuarios activos y administradores
                return this.users.filter(user => (user.type == "ACTIVE" || user.type == "ADMIN") && this.storage.loggedInUser.username != user.username);
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
  width: 150px;
  height: 150px;
  padding: 5px;
}
</style>
