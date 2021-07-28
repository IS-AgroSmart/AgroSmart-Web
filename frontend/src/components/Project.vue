<template>
    <div class="pt-3 px-3">
        <h1>Mis Proyectos</h1>
    
        <b-skeleton-wrapper :loading="loading">
            <template #loading>
                <b-row>
                    <b-col v-for="i in 3" :key="i">
                        <b-card class="my-3">
                            <b-skeleton width="85%" height="40%"></b-skeleton>
                            <b-skeleton width="100%"></b-skeleton>
                            <b-skeleton width="100%"></b-skeleton>
                            <b-skeleton type="button"></b-skeleton>
                        </b-card>
                    </b-col>
                </b-row>
            </template>

            <div v-if="error">Error!</div>
            <div class="row">
                <project-partial v-for="project in projects" :project="project" :key="project.uuid" @delete-confirmed="deleted"></project-partial>
            </div>
            <b-alert v-if="noProjects" variant="info" show>Aún no ha creado ningún proyecto</b-alert>
        </b-skeleton-wrapper>
        
        <add-new-project/>
    </div>
</template>

<script>
import axios from 'axios';
import ProjectPartial from './ProjectPartial'
import AddNewProject from './AddNewProject'
import forceLogin from './mixins/force_login'

export default {
    data() {
        return {
            projects: [],
            error: "",
            loading: true,
        }
    },
    computed: {
        noProjects() {
            return this.projects.length == 0;
        }
    },
    methods: {
        updateProjects() {
            return axios
                .get('api/projects', {
                    headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                })
                .then(response => this.projects = response.data)
                .catch(error => this.error = error);
        },
        deleted() { this.updateProjects(); },
    },
    created() {
        this.updateProjects().then(() => this.loading = false);
    },
    components: { ProjectPartial, AddNewProject },
    mixins: [forceLogin]
}
</script>