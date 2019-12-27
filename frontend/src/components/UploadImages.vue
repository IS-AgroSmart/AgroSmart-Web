<template>
    <div>
        <b-alert variant="success" show v-if="uploadOK">Subida exitosa. Procesando...</b-alert>
        <b-alert variant="danger" show v-if="uploadError">Subida fallida</b-alert>
        <b-alert variant="danger" show v-if="processingError">No pudo iniciarse el procesamiento</b-alert>
    
        <b-form @submit="onSubmit">
            <b-form-file multiple v-model="files" :file-name-formatter="formatNames" :state="anyFiles" placeholder="Escoja o arrastre imágenes..." drop-placeholder="Arrastre imágenes aquí..." browse-text="Seleccionar"></b-form-file>
            <div class="mt-3">{{ anyFiles ? "" : '¡No hay archivos seleccionados!' }}</div>
    
            <b-button type="submit" variant="primary">Subir</b-button>
        </b-form>
    </div>
</template>

<script>
import axios from "axios"

export default {
    data() {
        return {
            files: [],
            uploadOK: false,
            uploadError: false,
            processingError: false,
        }
    },
    computed: {
        anyFiles() {
            return this.files.length > 0;
        }
    },
    methods: {
        formatNames(files) {
            if (files.length === 1) {
                return files[0].name
            } else {
                return `${files.length} archivos seleccionados`
            }
        },
        onSubmit(evt) {
            evt.preventDefault()
            var data = new FormData();
            for (var file of this.files) {
                data.append("images", file);
            }

            var that = this;
            axios.post('/api/upload-files/' + this.$route.params.uuid, data, {
                    headers: { "Authorization": "Token " + this.storage.token },
                })
                .then(function() {
                    window.console.log("Redirecting to flight details")
                    this.$router.replace({ "name": "flightDetails", params: { "uuid": this.$route.params.uuid } })
                })
                .catch(function() {
                    window.console.log("Error!")
                    that.uploadError = true;
                });
        },
    }
}
</script>