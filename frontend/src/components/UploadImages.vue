<template>
    <div>
        <b-alert variant="success" show v-if="uploadOK">Subida exitosa. Procesando...</b-alert>
        <b-alert variant="danger" show v-if="uploadError">Subida fallida</b-alert>
        <b-alert variant="danger" show v-if="processingError">No pudo iniciarse el procesamiento</b-alert>
    
        <b-form @submit="onSubmit">
            <b-form-file multiple v-model="files" :file-name-formatter="formatNames" :state="anyFiles" placeholder="Escoja o arrastre imágenes..." drop-placeholder="Arrastre imágenes aquí..." browse-text="Seleccionar" accept="image/jpeg, image/png"></b-form-file>
            <div class="mt-3">{{ anyFiles ? "" : '¡No hay archivos seleccionados!' }}</div>
    
            <b-button :disabled="!anyFiles || uploading" type="submit" variant="primary">
                Subir <span v-if="uploading">({{uploadProgress}} %)</span>
            </b-button>
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
            uploading: false,
            uploadProgress: 0,
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
            this.uploading = true;
            axios.post('/api/upload-files/' + this.$route.params.uuid, data, {
                    headers: { "Authorization": "Token " + this.storage.token },
                    onUploadProgress: function(progressEvent) {
                        var percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                        that.uploadProgress = percentCompleted;
                    }
                })
                .then(function() {
                    that.$router.replace({ "name": "flightDetails", params: { "uuid": that.$route.params.uuid } })
                })
                .catch(function() {
                    that.uploadError = true;
                    that.uploading = false;
                });
        },
    }
}
</script>