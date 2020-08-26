<template>
    <div class="col-md-4">
        <b-card :title="projectName" class="my-3">
    
            <b-card-text>
                <p class="white-space: pre;">{{ project.description }}</p>
            </b-card-text>
    
            <b-button :to="{name: 'projectMap', params: {uuid: project.uuid}}" variant="primary" class="mx-1 my-1">Ver mapa</b-button>
            <b-button @click="onDelete" variant="danger" class="mx-1 my-1">Eliminar</b-button>
        </b-card>
    </div>
</template>

<script>
import forceLogin from './mixins/force_login';
import axios from 'axios';

export default {
    data() {
        return {

        };
    },
    computed: {
        mapper_url() {
            return "/mapper/" + this.project.uuid;
        },
        projectName() {
            return this.project.name + (this.project.is_demo ? " (DEMO)" : "");
        }
    },
    methods: {
        onDelete() {
            this.$bvModal.msgBoxConfirm('Este proyecto NO podrá ser recuperado.', {
                    title: '¿Realmente desea eliminar el proyecto?',
                    okVariant: 'danger',
                    okTitle: 'Sí',
                    cancelTitle: 'No',
                    // hideHeaderClose: false
                })
                .then(value => {
                    if (value)
                        axios.delete("api/projects/" + this.project.uuid, {
                            headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                        }).then(() => this.$emit("delete-confirmed"))
                        .catch(() => {
                            this.$bvToast.toast('Error al eliminar el proyecto', {
                                title: "Error",
                                autoHideDelay: 3000,
                                variant: "danger",
                            });
                        });
                });
        },
    },
    props: ["project"],
    mixins: [forceLogin]
}
</script>