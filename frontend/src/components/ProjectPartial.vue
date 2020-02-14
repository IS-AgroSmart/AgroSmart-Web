<template>
    <div class="col-md-4">
        <b-card :title="project.name" class="my-3">
    
            <b-card-text>
                <p class="white-space: pre;">{{ project.description }}</p>
            </b-card-text>
    
            <b-button :href="mapper_url" variant="primary">Ver mapa</b-button>
        </b-card>
    </div>
</template>

<script>
export default {
    created() {
        if (!this.$isLoggedIn()) {
            this.$router.push("/login");
        }
    },
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
        mapper_url() {
            return "/mapper/" + this.project.uuid;
        }
        
    },
    props: ["project"]
}
</script>