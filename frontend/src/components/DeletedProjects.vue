<template>
    <div>
        <h1>Mis proyectos eliminados</h1>
    
        <div v-if="error">Error!</div>
        <div class="row">
            <project-partial v-for="project in projects" :project="project" :key="project.uuid" deleted @delete-confirmed="updateProjects"  @restore-confirmed="updateProjects"></project-partial>
        </div>
        <b-alert v-if="noProjects" variant="info" show>No tiene proyectos eliminados</b-alert>
    </div>
</template>

<script>
import axios from 'axios';
import ProjectPartial from './ProjectPartial'
import forceLogin from './mixins/force_login'

export default {
    data() {
        return {
            projects: [],
            error: "",
        }
    },
    computed: {
        noProjects() {
            return this.projects.length == 0;
        }
    },
    methods: {
        updateProjects() {
            axios
                .get('api/projects/deleted', {
                    headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                })
                .then(response => (this.project = response.data))
                .catch(error => this.error = error);
        },
    },
    created() {
        this.updateProjects();
    },
    components: { ProjectPartial },
    mixins: [forceLogin]
}
</script>