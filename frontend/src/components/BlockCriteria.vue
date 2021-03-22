<template>
<div class="pt-3" style="padding-left:15px; padding-right:15px;">    
  <h1>Criterios de Bloqueo</h1>
    <b-form>
      <b-form-input v-model="opcionFilter" placeholder="Buscar criterios por nombre o valor..."></b-form-input>
    </b-form>
    <h2>Nuevo Criterio</h2>
    <b-form>
      <b-form-group id="input-group-1" label="Tipo de Criterio:" label-for="input-1">
        <b-form-select id="input-1" v-model="type" :options="block_types"></b-form-select>
      </b-form-group>
      <b-form-group
        id="input-group-1"
        label="Valor de criterio:"
        label-for="input-1"
        v-if="type !== 'IP'"
      >
        <b-form-input id="input-2" v-model=value placeholder="p. ej. fake.com"></b-form-input>
      </b-form-group>
      <b-form-group id="input-group-1" label="Valor IP:" label-for="input-3" v-if="type === 'IP'">
        <b-form-input v-model="ip" placeholder="p. ej. 127.0.0.1" id="input-3"></b-form-input>
      </b-form-group>
    </b-form>
    <p><b-button v-on:click="createBlock">Crear</b-button></p>
    <b-alert v-if="criterios.length === 0" show variant="info">¡No hay criterios creados!</b-alert>

    <div class="row">
      <b-card v-for="criteria in criterios" :key="criteria.pk" class="card">
        <b-card-title>
          <p>Si el {{criteria.type}} es:</p>
          <strong>{{ criteria.value }}</strong>
          <strong v-if="criteria.type === 'IP'">{{criteria.ip}}</strong>
        </b-card-title>
        <b-card-text>
          <b-button v-on:click="deleteBlock(criteria)">X</b-button>
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
            block_criterias: [],
            acciones: ['Aceptar', 'Rechazar', 'Bloquear'],
            opcionFilter: '',
            alert: false,
            block_types: [
              { value: null, text: 'Criterio de bloqueo' },
              { value: 'IP', text: 'IP' },
              { value: 'USER_NAME', text: 'UserName' },
              { value: 'EMAIL', text: 'Email' },
              { value: 'DOMAIN', text: 'Domain' }
            ],
            value: '',
            ip: null,
            type: null,
            newCriteria: false,
        }
    },

    methods: {
        clearForm() {
          this.value=null;
          this.ip=null;
          this.type=null;
        },
        loadCriteria() {
            axios.get('api/block_criteria/', {
                    headers: { "Authorization": "Token " + this.storage.token }
                })
                .then(response => {
                    this.block_criterias = response.data
                })
                .catch(error => this.error = error);
        },
        createBlock() {
            axios.post("api/block_criteria/", { type: this.type, ip: this.ip, value: this.value  }, {
                    headers: { "Authorization": "Token " + this.storage.token },
                }).then(() => this.loadCriteria())
                .catch(() => {
                    this.$bvToast.toast('Error al procesar la solicitud. Intente más tarde', {
                        title: "Error",
                        autoHideDelay: 3000,
                        variant: "danger",
                    });
                });
            this.clearForm();
        },
        deleteBlock(criteria) {
          axios.delete("api/block_criteria/" + criteria.pk + "/",  {
                    headers: { "Authorization": "Token " + this.storage.token },
                }).then(() => this.loadCriteria())
                .catch(() => {
                    this.$bvToast.toast('Error al procesar la solicitud. Intente más tarde', {
                        title: "Error",
                        autoHideDelay: 3000,
                        variant: "danger",
                    });
                });
        },
    },
    computed: {
        criterios() {
          if (this.opcionFilter) {
                return this.block_criterias.filter(block => 
                    (block.value? block.value.toLowerCase().indexOf(this.opcionFilter) > -1 : false ||
                      block.ip? block.ip.toLowerCase().indexOf(this.opcionFilter) > -1 : false));
            } else {
                // Mostrar sólo los usuarios que no son administradores
                return this.block_criterias;
            }
        },
    },
    created() {
        if (!this.$isLoggedIn()) {
            this.$router.push("/login");
        }
        this.loadCriteria();
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
