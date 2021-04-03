<template>
    <div class=" pt-3" style="padding-left:15px; padding-right:15px;">
        <b-link href="#" @click="goBack()" class="mb-3">&lt; Volver al proyecto</b-link>
        <br><br>

        <b-alert variant="danger" show v-if="uploadError">{{ uploadError }}</b-alert>
    
        <b-form @submit="onSubmit">
            <b-form-group>
                <b-input type="text" v-model="title" placeholder="Escriba el nombre de la capa" required/>
            </b-form-group>
            <b-form-group>
                <b-form-file v-model="file" :file-name-formatter="formatName" :state="anyFile" placeholder="Escoja o arrastre un archivo GeoTIFF..." drop-placeholder="Arrastre imágenes aquí..." browse-text="Seleccionar" accept=".tiff, .tif, .geotiff"></b-form-file>
            </b-form-group>
            <div class="my-3 text-danger">{{ anyFile ? "" : '¡No hay un ortomosaico seleccionado!' }}</div>
    
            <b-button :disabled="!anyFile || uploading" type="submit" variant="primary">
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
            uploadError: false,
            uploading: false,
            uploadProgress: 0,
        }
    },
    computed: {
        anyFile() { return this.file != null; },
    },
    methods: {
        goBack() {
            window.history.back();
        },
        formatName(file) {
            return file[0].name;
        },
        onSubmit(evt) {
            evt.preventDefault()
            var data = new FormData();
            data.append("geotiff", this.file);
            data.append("title", this.title);

            var that = this;
            this.uploading = true;
            axios.post('/api/uploads/' + this.$route.params.uuid + '/geotiff', data, {
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