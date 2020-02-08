<template>
  <div>
    <b-alert v-if="error" variant="danger" show>{{error}}</b-alert>
    <b-form @submit="onSubmit">
      <b-form-group id="input-group-1" label="Nombre:" label-for="input-1">
        <b-form-input
          id="input-1"
          v-model="form.name"
          type="text"
          required
          placeholder="Nombre del proyecto"
        ></b-form-input>
      </b-form-group>
      <b-form-group id="input-group-2" label="Descripción:" label-for="input-2">
        <b-form-textarea
          id="input-2"
          v-model="form.description"
          placeholder="Describa el proyecto"
          rows="4"
          required
        ></b-form-textarea>
      </b-form-group>
      <b-form-group id="input-group-3" label="Vuelos:" label-for="input-3">
        <b-form-select
          id="input-3"
          v-model="form.flights"
          :options="flights"
          value-field="uuid"
          text-field="name"
          multiple
        ></b-form-select>
        <small class="form-text text-muted">Seleccione uno o varios vuelos con Ctrl.</small>
      </b-form-group>
      <b-form-group id="input-group-4" label="Artefactos:" label-for="input-4">
        <b-form-select
          id="input-4"
          v-model="form.artifact"
          :options="artifacts"
          value-field="pk"
          text-field="type"
          multiple
          :select-size="2"
        ></b-form-select>
      </b-form-group>

      <b-button type="submit" variant="primary">Submit</b-button>
    </b-form>
  </div>
</template>

<script>
import axios from "axios";

export default {
  data() {
    return {
      form: {
        name: "",
        description: "",
        flights: {},
        artifacts: {}
      },
      error: "",
      flights: {},
      artifacts: {}
    };
  },
  methods: {
    onSubmit(evt) {
      evt.preventDefault();
      if (!this.$isLoggedIn()) {
        this.$router.push("/login");
      }
      var fd = new FormData();
      fd.set("name", this.form.name);
      fd.set("description", this.form.description);
      // HACK: DRF needs this for ManyToMany, otherwise it gets nervous
      for(var flight of this.form.flights){
        fd.append("flights", flight);
      }
      // TODO: artifacts

      axios
        .post("api/projects/", fd, {
          headers: { Authorization: "Token " + this.storage.token }
        })
        .then(response => {
          this.$router.push({
            name: "listProjects",
            params: { uuid: response.data.uuid }
          });
        })
        .catch(error => (this.error = "ERROR: " + error.response.data.name[0]));
    }
  },
  created() {
    axios
      .get("api/flights", {
        headers: { Authorization: "Token " + this.storage.token }
      })
      .then(response => (this.flights = response.data))
      .catch(error => (this.error = error));

    axios
      .get("api/artifacts", {
        headers: { Authorization: "Token " + this.storage.token }
      })
      .then(response => (this.artifacts = response.data))
      .catch(error => (this.error = error));
  }
};
</script>