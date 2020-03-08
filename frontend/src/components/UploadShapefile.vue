<template>
    <div>
        <b-alert variant="success" show v-if="uploadOK">Subida exitosa. Procesando...</b-alert>
        <b-alert variant="danger" show v-if="uploadError">Subida fallida</b-alert>
        <b-alert variant="danger" show v-if="processingError">No pudo iniciarse el procesamiento</b-alert>
    
        <b-form @submit="onSubmit">
            <b-form-group>
                <b-input type="text" v-model="title" placeholder="Escriba el nombre de la capa" required/>
            </b-form-group>
            <b-form-group>
                <b-form-file v-model="file" :file-name-formatter="formatNames" :state="anyFiles" placeholder="Escoja o arrastre un archivo shapefile..." drop-placeholder="Arrastre imágenes aquí..." browse-text="Seleccionar" accept=".shp"></b-form-file>
            </b-form-group>
            <div class="my-3 text-danger">{{ anyFiles ? "" : '¡No hay un shapefile seleccionado!' }}</div>
    
            <b-button :disabled="!anyFiles || uploading" type="submit" variant="primary">
                Subir <span v-if="uploading">({{uploadProgress}} %)</span>
            </b-button>
        </b-form>
    </div>
</template>

<script>
import axios from "axios"
import forceLogin from './mixins/force_login'

export default {
    data() {
        return {
            file: null,
            title: "",
            uploadOK: false,
            uploadError: false,
            processingError: false,
            uploading: false,
            uploadProgress: 0,
        }
    },
    computed: {
        anyFiles() {
            return this.file != null;
        },
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
            data.append("shapefile", this.file);
            data.append("title", this.title);


            var that = this;
            this.uploading = true;
            axios.post('/api/uploads/' + this.$route.params.uuid + '/shapefile', data, {
                    headers: { "Authorization": "Token " + this.storage.token },
                })
                .then(function() {
                    alert("Redirecting...");
                })
                .catch(function() {
                    that.uploadError = true;
                    that.uploading = false;
                });
        },
    },
    mixins: [forceLogin]
}
</script>