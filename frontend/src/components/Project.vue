<template>
    <div>
        <h1>Mis Proyectos</h1>
    
        <div v-if="error">Error!</div>
        <div class="row">
            <project-partial v-for="project in projects" :project="project" :key="project.uuid"></project-partial>
        </div>
        <b-alert v-if="noProjects" variant="info" show>Aún no ha creado ningún proyecto</b-alert>
        <add-new-project/>
    </div>
</template>

<script>
import axios from 'axios';
import ProjectPartial from './ProjectPartial'
import AddNewProject from './AddNewProject'

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
                .get('api/projects', {
                    headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                })
                .then(response => (this.projects = response.data))
                .catch(error => this.error = error);
        }
    },
    created() {
        if (!this.$isLoggedIn()) {
            this.$router.push("/login");
        }

        this.updateProjects();
    },
    components: { ProjectPartial, AddNewProject }
}
</script>