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
import forceLogin from './mixins/force_login'

export default {
    data() {
        return {

        };
    },
    computed: {
        mapper_url() {
            return "/mapper/" + this.project.uuid;
        }
        
    },
    props: ["project"],
    mixins: [forceLogin]
}
</script>