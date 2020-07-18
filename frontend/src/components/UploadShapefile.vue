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
                <p class="small text-muted">Escoja los tres archivos .shp, .shx y .dbf</p>
                <b-form-file multiple v-model="files" :file-name-formatter="formatNames" :state="validFiles" placeholder="Escoja o arrastre un archivo shapefile..." drop-placeholder="Arrastre imágenes aquí..." browse-text="Seleccionar" accept=".shp,.dbf,.shx"></b-form-file>
            </b-form-group>
            <div class="my-3 text-danger">{{ validFiles ? "" : 'Seleccione tres archivos con el mismo nombre y extensiones .shp, .shx y .dbf' }}</div>
    
            <b-button :disabled="!validFiles || uploading" type="submit" variant="primary">
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
            files: [],
            title: "",
            uploadOK: false,
            uploadError: false,
            processingError: false,
            uploading: false,
            uploadProgress: 0,
        }
    },
    computed: {
        validFiles() {
            if (this.files.length != 3) return false;
            var filePaths = this.files.map(file => file.name);
            var fileNames = filePaths.map(path => path.substring(0, path.lastIndexOf("."))) // Filenames array (no extension)
            var extensions = filePaths.map(path => path.substring(path.lastIndexOf(".") + 1)); // Extensions array
            var fileNamesValid = fileNames.every(name => name === fileNames[0]); // True if all filenames are equal
            var fileExtensionsValid = extensions.every(extension => ["shp", "shx", "dbf"].includes(extension));
            return fileNamesValid && fileExtensionsValid;
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
            for (var file of this.files) {
                data.append("shapefile", file);
            }
            data.append("title", this.title);

            var that = this;
            this.uploading = true;
            axios.post('/api/uploads/' + this.$route.params.uuid + '/shapefile', data, {
                    headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
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