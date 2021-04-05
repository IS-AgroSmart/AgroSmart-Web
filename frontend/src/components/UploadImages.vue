<template>
    <div class=" pt-3" style="padding-left:15px; padding-right:15px;">
        <b-alert variant="danger" show v-if="uploadError">{{ uploadError }}</b-alert>
    
        <b-form @submit="onSubmit">
            <p class="small text-muted">{{ validFormats }}</p>
            <b-form-file multiple v-model="files" :file-name-formatter="formatNames" :state="enoughFiles && !tooManyFiles" placeholder="Escoja o arrastre imágenes..." drop-placeholder="Arrastre imágenes aquí..." browse-text="Seleccionar" :accept="validFormats"></b-form-file>
            <div class="my-3 text-danger" v-if="!enoughFiles">¡No hay suficientes archivos seleccionados!</div>
            <div class="my-3 text-danger" v-if="tooManyFiles">Ha seleccionado demasiadas imágenes. Puede subir hasta {{ maxNumberFiles }} imágenes.</div>
    
            <b-button :disabled="!enoughFiles || tooManyFiles || uploading" type="submit" variant="primary">
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
            flight: {},
            flightLoaded: false,
            files: [],
            uploadError: "",
            uploading: false,
            uploadProgress: 0,
            maxImagesPerFlight: 1000
        }
    },
    computed: {
        enoughFiles() { return this.files.length >= 3; },
        maxNumberFiles()  { return Math.min(this.$effectiveUser().remaining_images, this.maxImagesPerFlight) },
        tooManyFiles() { return this.files.length > this.maxNumberFiles; },
        validFormats() { return this.flight.camera == "RGB" ? "image/jpeg, image/png" : "image/tiff"; },
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
                    headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                    onUploadProgress: function(progressEvent) {
                        var percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                        that.uploadProgress = percentCompleted;
                    }
                })
                .then(function() {
                    that.$router.replace({ "name": "flightDetails", params: { "uuid": that.$route.params.uuid } })
                })
                .catch(function(error) {
                    if (error.response?.status == 402)
                        that.uploadError = error.response.data;
                    else
                        that.uploadError = "Subida fallida.";
                    that.uploading = false;
                });
        },
    },
    created() {
        axios
            .get("api/flights/" + this.$route.params.uuid, {
                headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
            })
            .then(response => {
                this.flight = response.data;
                this.flightLoaded = true;
            })
            .catch(error => this.error = error);

    },
    mixins: [forceLogin]
}
</script>