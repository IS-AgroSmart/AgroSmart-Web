<template>
    <div>
        <p>{{ project.uuid }}</p>
    </div>
</template>


<script>

import axios from 'axios'

export default {
    data(){
        return {
            project: {},

        }
    },
    created(){
        if (!this.$isLoggedIn()) {
            this.$router.push("/login");
        }
        axios
            .get("api/projects/" + this.$route.params.uuid, {
                headers: { "Authorization": "Token " + this.storage.token }
            })
            .then(response => {
                this.project = response.data;
            })
            .catch(error => this.error = error);
    },
    methods:{

    },
    compute:{

    },
}


</script>