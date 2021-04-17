<template>
    <div class=" pt-3" style="padding-left:15px; padding-right:15px;">
        <h1>
            {{ flight.name }}
            <small v-if="flightDate">{{ flightDate }}</small>
            <small class="mx-5"><b-button v-if="isStopped" variant="danger" @click="deleteFlight">Eliminar</b-button></small>
            <small class="mx-7"><b-button v-if="isBusy" variant="danger" @click="cancelFlight">Cancelar</b-button></small>
        </h1>
    
    
        <div v-if="flightLoaded" class="row my-5">
            <div class="col-sm-4">
                <b-progress v-if="isBusy" height="0.3rem">
                    <b-progress-bar :value="info.progress" animated></b-progress-bar>
                </b-progress>
    
                <b-link v-if="isDoneSuccessfully" :to="{name: 'flightOrthoPreview', params: {uuid: flight.uuid}}">
                    <b-img v-if="isDoneSuccessfully" :src="orthomosaicThumbUrl" fluid rounded="circle" @error="thumbnailLoadError" /></b-link>
                <h4 class="my-3 text-center">Notas</h4>
                <span style="white-space: pre-wrap;">{{flight.annotations}}</span>
            </div>
    
            <div class="col-sm-4">
                <h4>Consola
                    <button id="tooltip-target-1" class="btn btn-info mx-3" type="button" v-clipboard:copy="console" v-clipboard:success="onCopySuccess" v-clipboard:error="onCopyError">Copiar</button>
                    <b-tooltip ref="tooltip" target="tooltip-target-1" :variant="tooltipVariant" triggers="manual">{{tooltipText}}</b-tooltip>
                </h4>
                <b-form-textarea id="textarea" v-model="consoleToText" rows="15" readonly v-chat-scroll></b-form-textarea>
            </div>
    
            <div class="col-sm-4">
                <b-list-group>
                    <b-list-group-item><span class="font-weight-bold">Fecha: </span>{{flightDate}}</b-list-group-item>
                    <b-list-group-item><span class="font-weight-bold">Cámara: </span>{{friendlyCamera}}</b-list-group-item>
                    <b-list-group-item><span class="font-weight-bold">Estado: </span>{{processingState}}{{progress}}</b-list-group-item>
                    <b-list-group-item><span class="font-weight-bold">Imágenes: </span>{{info.imagesCount}}</b-list-group-item>
                    <b-list-group-item><span class="font-weight-bold">Tiempo: </span>{{processingTimeFriendly}}</b-list-group-item>
                    <b-list-group-item v-if="isBusy"><span class="font-weight-bold">Tiempo restante (estimado): </span>{{remainingTimeFriendly}}</b-list-group-item>
                </b-list-group>
    
                <div v-if="flightLoaded" class="text-center">
                    <b-button v-if="isDoneSuccessfully" class="my-3 mx-auto" variant="outline-primary" :to="{name: 'flightResults', params: {uuid: flight.uuid}}">Resultados</b-button>
                </div>
    
            </div>
        </div>
    </div>
</template>

<script>
import axios from 'axios'
import forceLogin from './mixins/force_login'

const baseUrl = window.location.protocol + "//" + window.location.hostname + "/api/downloads/";
export default {
    data() {
        return {
            flight: {},
            flightLoaded: false,
            error: "",
            console: [],
            info: { status: {} },
            polling: null,
            tooltipText: "",
            tooltipVariant: "",
            orthomosaicGeoserverPreviewUrl: "",
        };
    },
    methods: {
        updateStatus() {
            axios.get(`/nodeodm/task/${this.$route.params.uuid}/output`, {
                    headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                })
                .then(response => (this.console = ("error" in response.data) ? response.data.error : response.data))
                .then(() => {
                    var textarea = document.getElementById('textarea');
                    textarea.scrollTop = textarea.scrollHeight;
                })
                .catch(error => this.error = error);

            axios.get(`/nodeodm/task/${this.$route.params.uuid}/info`, {
                    headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                })
                .then(response => (this.info = ("error" in response.data) ? response.data.error : response.data))
                .catch(error => this.error = error);
        },
        deleteFlight() {
            this.$bvModal.msgBoxConfirm(this.flight.is_demo ?
                    'Este vuelo no podrá ser recuperado.' :
                    'Este vuelo podrá ser recuperado durante 30 días.', {
                        title: '¿Realmente desea eliminar el vuelo?',
                        okVariant: 'danger',
                        okTitle: 'Sí',
                        cancelTitle: 'No',
                        // hideHeaderClose: false
                    })
                .then(value => {
                    if (value)
                        axios.delete("api/flights/" + this.flight.uuid, {
                            headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                        }).then(() => this.$router.replace(this.flight.is_demo ? "/flights" : "/flights/deleted"))
                        .catch(() => {
                            this.$bvToast.toast('Error al eliminar el vuelo', {
                                title: "Error",
                                autoHideDelay: 3000,
                                variant: "danger",
                            });
                        });
                });
        },
        cancelFlight() {
            this.$bvModal.msgBoxConfirm('¿Realmente desea cancelar el procesamiento del vuelo?', {
                    okVariant: 'danger',
                    okTitle: 'Sí',
                    cancelTitle: 'No',
                    // hideHeaderClose: false
                })
                .then(value => {
                    if (value)
                        axios.post("/nodeodm/task/cancel", { uuid: this.flight.uuid },
                            {
                                headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                            });
                });

        },
        onCopySuccess: function() {
            this.$refs.tooltip.$emit("open");
            this.tooltipVariant = "success";
            this.tooltipText = "Contenido copiado";
            this.prepareHideTooltip();
        },
        onCopyError: function() {
            this.$refs.tooltip.$emit("open");
            this.tooltipVariant = "danger";
            this.tooltipText = "No se pudo copiar el texto";
            this.prepareHideTooltip();
        },
        prepareHideTooltip: function() {
            setTimeout(() => {
                this.$refs.tooltip.$emit("close");
            }, 500);
        },
        formatDuration(millis) {
            if (!millis) {
                return ""
            }
            const duration = this.$moment.duration(millis)
            if (duration.days() == 0) { // No days
                return this.$moment.utc(duration.as('milliseconds')).format('HH [h] mm [min] ss [s]')
            } else { // At least one day, add day format
                return this.$moment.utc(duration.as('milliseconds')).format('DDD [d] HH [h] mm [min] ss [s]')
            }
        },
        thumbnailLoadError(e) {
            // After two seconds, try to reload the image
            window.setTimeout(() => {
                // eslint-disable-next-line no-self-assign
                e.target.src = e.target.src;
            }, 2000);
        }
    },
    computed: {
        cameras() {
            let cams = {};
            this.$cameras.forEach(cam =>
                cams[cam.value] = cam.text
            );
            return cams;
        },
        friendlyCamera() {
            return this.cameras[this.flight.camera]
        },
        processingState() {
            return this.$processingStepsODM[this.info.status?.code] ?? this.$processingStepsDjango[this.flight.state];
        },
        processingTimeFriendly() {
            return this.formatDuration(Math.max(this.flight.processing_time, this.info.processingTime));
        },
        remainingTimeFriendly() {
            return this.info.progress == 0 ? "-" : this.formatDuration(this.estimatedRemainingTime);
        },
        estimatedRemainingTime() {
            const millisPassed = this.info.processingTime;
            const progress = this.info.progress;
            const estimatedTotalTime = millisPassed / (progress / 100);
            return estimatedTotalTime - millisPassed;
        },
        progress() {
            return this.isBusy ? " (" + this.info.progress.toFixed(0) + "%)" : "";
        },
        isBusy() { return this.info.status?.code == 20; },
        isDoneSuccessfully() { return this.info.status?.code == 40 || this.flight.state == "COMPLETE"; },
        isDoneError() { return this.info.status?.code == 30 || this.flight.state == "ERROR"; },
        isDoneCanceled() { return this.info.status?.code == 50 || this.flight.state == "CANCELED"; },
        isStopped() {
            return this.isDoneSuccessfully || this.isDoneCanceled || this.isDoneError;
        },
        flightDate() {
            return this.flight.date ? this.$moment(this.flight.date, "YYYY-MM-DD").format("dddd D [de] MMMM, YYYY") : ""
        },
        consoleToText() {
            return typeof this.console == "string" ? this.console : this.console.join("\n");
        },
        orthomosaicThumbUrl() {
            return baseUrl + this.flight.uuid + "/thumbnail"
        },
    },
    watch: {
        flight: function() {
            if (this.flight.state == "WAITING") {
                this.$router.replace({ "name": "uploadImages", params: { "uuid": this.flight.uuid } })
            }

            if (this.flight.state == "COMPLETE") {
                axios.get("/api/preview/" + this.flight.uuid, {
                        headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                    })
                    .then(response => {
                        this.orthomosaicGeoserverPreviewUrl = response.data.url;
                    });
            }
        }
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

        this.updateStatus();
        this.polling = setInterval(() => {
            this.updateStatus();
        }, 1000);
    },
    beforeDestroy() {
        clearInterval(this.polling)
    },
    mixins: [forceLogin]
}
</script>