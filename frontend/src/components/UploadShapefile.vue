<template>
    <div class=" pt-3" style="padding-left:15px; padding-right:15px;">
        <b-link href="#" @click="goBack()" class="mb-3">&lt; Volver al proyecto</b-link>
        <br><br>

        <b-alert variant="danger" show v-if="uploadError">{{ uploadError }}</b-alert>
    
        <b-form @submit="onSubmit">
            <b-form-group>
                <b-form-radio-group v-model="datatype" :options="fileFormatOptions" buttons></b-form-radio-group>
            </b-form-group>
    
            <b-form-group>
                <b-input type="text" v-model="title" placeholder="Escriba el nombre de la capa" required/>
            </b-form-group>
            <b-form-group>
                <p class="small text-muted">{{ helpMessage }}</p>
                <b-form-file :multiple="shouldBeMultiSelect" v-model="files" :file-name-formatter="formatNames" :state="validFiles" :placeholder="placeholderMessage" browse-text="Seleccionar" :accept="acceptedExtensions"></b-form-file>
            </b-form-group>
            <div class="my-3 text-danger">{{ validFiles ? "" : errorMessage }}</div>
    
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
            datatype: "shp",
            fileFormatOptions: [
                { text: 'Shapefile', value: 'shp' },
                { text: 'Archivo KML', value: 'kml' },
            ],
            files: [],
            title: "",
            uploadError: "",
            uploading: false,
            uploadProgress: 0,
        }
    },
    computed: {
        validFiles() {
            switch (this.datatype) {
                case "shp":
                    return this.validFilesShp;
                case "kml":
                    return this.validFilesKml;
                default:
                    return false;
            }
        },
        shouldBeMultiSelect() {
            return ["shp"].includes(this.datatype);
        },
        validFilesShp() {
            if (this.files.length != 3) return false;
            var filePaths = this.files.map(file => file.name);
            var fileNames = filePaths.map(path => path.substring(0, path.lastIndexOf("."))) // Filenames array (no extension)
            var extensions = filePaths.map(path => path.substring(path.lastIndexOf(".") + 1)); // Extensions array
            var fileNamesValid = fileNames.every(name => name === fileNames[0]); // True if all filenames are equal
            var fileExtensionsValid = extensions.every(extension => ["shp", "shx", "dbf"].includes(extension));
            return fileNamesValid && fileExtensionsValid;
        },
        validFilesKml() {
            if (!(this.files instanceof File)) return false;
            var filePath = this.files.name;
            return filePath.substr(-4) === ".kml";
        },
        helpMessage() {
            return {
                shp: "Escoja los tres archivos .shp, .shx y .dbf",
                kml: "Escoja un único archivo .kml"
            }[this.datatype];
        },
        errorMessage() {
            return {
                shp: 'Seleccione tres archivos con el mismo nombre y extensiones .shp, .shx y .dbf',
                kml: 'Seleccione un archivo con extensión .kml'
            }[this.datatype];
        },
        placeholderMessage() {
            return {
                shp: "Escoja un archivo shapefile...",
                kml: "Escoja un archivo KML..."
            }[this.datatype];
        },
        acceptedExtensions() {
            return {
                shp: ".shp,.dbf,.shx",
                kml: ".kml"
            }[this.datatype];
        },
    },
    methods: {
        goBack() {
            window.history.back();
        },
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
            if (this.files instanceof Array)
                for (var file of this.files) {
                    data.append("file", file);
                }
            else if (this.files instanceof File)
                data.append("file", this.files)
            data.append("title", this.title);
            data.append("datatype", this.datatype);

            var that = this;
            this.uploading = true;
            axios.post('/api/uploads/' + this.$route.params.uuid + '/vectorfile', data, {
                    headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                })
                .then(() => this.goBack())
                .catch(function(error) {
                    if(error.response?.status == 402)
                        that.uploadError = "Subida fallida. Su almacenamiento está lleno.";
                    else
                        that.uploadError = "Subida fallida.";
                    that.uploading = false;
                });
        },
    },
    mixins: [forceLogin]
}
</script>