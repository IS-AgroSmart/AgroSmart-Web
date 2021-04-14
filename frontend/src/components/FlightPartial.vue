<template>
    <div class="col-md-4">
        <b-card :title="flightName" class="my-3" data-cy="flight-card">
    
            <b-card-text>
                <b-spinner variant="warning" type="grow" v-if="isWaiting" title="Suba imágenes al vuelo para comenzar"></b-spinner>
                <b-spinner variant="success" type="grow" v-if="isBusy" title="En proceso"></b-spinner>
                <span v-if="isBusy">{{progress}}</span>
                <b-spinner variant="danger" type="grow" v-if="isErrored" title="Error!"></b-spinner>
                <span style="white-space: pre-wrap;">{{flight.annotations}}</span>
            </b-card-text>
    
            <b-button v-if="!deleted" :to="{name: 'flightDetails', params: {uuid: flight.uuid}}" variant="primary">Ver detalles</b-button>
            <div v-else>
                <b-button @click="deleteFlight" variant="danger" class="mx-1 my-1">Eliminar</b-button>
                <b-button @click="restoreFlight" variant="success" class="mx-1 my-1">Restaurar</b-button>
            </div>
        </b-card>
    </div>
</template>

<script>
import axios from 'axios'
// import forceLogin from './mixins/force_login'

export default {
    data() {
        return {

        };
    },
    computed: {
        progress() {
            // Will only be called when this.flight.state == "PROCESSING"
            return " (" + this.flight.nodeodm_info.progress.toFixed(0) + "%) ";
        },
        isWaiting() {
            return this.flight.state == "WAITING"
        },
        isBusy() {
            return this.flight.state == "PROCESSING"
        },
        isErrored() {
            return this.flight.state == "ERROR"
        },
        flightName() {
            return this.flight.name + (this.flight.is_demo ? " (DEMO)" : "");
        }
    },
    methods: {
        deleteFlight() {
            this.$bvModal.msgBoxConfirm('Este vuelo NO podrá ser recuperado.', {
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
                        }).then(() => this.$emit("delete-confirmed"))
                        .catch(() => {
                            this.$bvToast.toast('Error al eliminar el vuelo', {
                                title: "Error",
                                autoHideDelay: 3000,
                                variant: "danger",
                            });
                        });
                });
        },
        restoreFlight() {
            axios.patch("api/flights/" + this.flight.uuid + "/", { deleted: false }, {
                    headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                }).then(() => this.$emit("restore-confirmed"))
                .catch(() => {
                    this.$bvToast.toast('Error al restaurar el vuelo', {
                        title: "Error",
                        autoHideDelay: 3000,
                        variant: "danger",
                    });
                });
        }
    },
    props: {
        flight: { type: Object },
        deleted: { type: Boolean, default: false }
    },
    //mixins: [forceLogin] // forceLogin not required, this will only be instantiated from page components
}
</script>