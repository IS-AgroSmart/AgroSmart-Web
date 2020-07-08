<template>
    <div class="col-md-4">
        <b-card :title="flight.name" class="my-3">
    
            <b-card-text>
                <b-spinner variant="warning" type="grow" v-if="isWaiting" title="Suba imágenes al vuelo para comenzar"></b-spinner>
                <b-spinner variant="success" type="grow" v-if="isBusy" title="En proceso"></b-spinner>
                <span v-if="isBusy">{{progress}}</span>
                <b-spinner variant="danger" type="grow" v-if="isErrored" title="Error!"></b-spinner>
                <span style="white-space: pre;">{{flight.annotations}}</span>
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
import forceLogin from './mixins/force_login'

export default {
    data() {
        return {

        };
    },
    computed: {
        progress() {
            if (this.flight.state != "PROCESSING") {
                return ""
            }
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
                            headers: { "Authorization": "Token " + this.storage.token }
                        }).then(() => this.$emit("delete-confirmed"))
                        .catch(() => {
                            this.$bvToast.toast('Error al eliminar el vuelo', {
                                title: "Error",
                                autoHideDelay: 3000,
                                variant: "danger",
                            });
                        });
                })
        },
        restoreFlight() {
            axios.patch("api/flights/" + this.flight.uuid + "/", { deleted: false }, {
                    headers: { "Authorization": "Token " + this.storage.token }
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
    mixins: [forceLogin]
}
</script>