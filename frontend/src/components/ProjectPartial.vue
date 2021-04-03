<template>
    <div class="col-md-4">
        <b-card :title="projectName" class="my-3">
    
            <b-card-text>
                <p class="white-space: pre-wrap;">{{ project.description }}</p>
            </b-card-text>
            <div v-if="!deleted">
                <b-button :to="{name: 'projectMap', params: {uuid: project.uuid}}" variant="primary" class="mx-1 my-1">Ver mapa</b-button>
                <b-button @click="deleteProject" :value="deleted" variant="danger" class="mx-1 my-1">Eliminar</b-button>
            </div>
            <div v-else>
                <b-button @click="finalDeleteProject" variant="danger" class="mx-1 my-1">Eliminar</b-button>
                <b-button @click="restoreProject" variant="success" class="mx-1 my-1">Restaurar</b-button>
            </div>
        </b-card>
    </div>
</template>

<script>
// import forceLogin from './mixins/force_login';
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
        finalDeleteProject() {
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
        restoreProject() {
            axios.patch("api/projects/" + this.project.uuid + "/", { deleted: false }, {
                    headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                }).then(() => this.$emit("restore-confirmed"))
                .catch(() => {
                    this.$bvToast.toast('Error al restaurar el proyecto', {
                        title: "Error",
                        autoHideDelay: 3000,
                        variant: "danger",
                    });
                });
        },
        deleteProject() {
            this.$bvModal.msgBoxConfirm(this.project.is_demo ?
                    'Este proyecto no podrá ser recuperado.' :
                    'Este proyecto podrá ser recuperado durante 30 días.', {
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
                        }).then(() => this.$router.replace(this.project.is_demo ? "/projects" : "/projects/deleted"))
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
    props: {
        project: { type: Object },
        deleted: { type: Boolean, default: false }
    },
    // mixins: [forceLogin] // forceLogin not required, this will only be instantiated from page components
}
</script>