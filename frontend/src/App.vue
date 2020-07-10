<template>
    <div id="app">
        <navbar></navbar>
    
        <div class="container pt-3">
            <router-view></router-view>
        </div>
    
        <b-alert v-if="this.storage.otherUserPk" class="position-fixed fixed-bottom m-0 rounded-0" style="z-index: 2000;" variant="warning" show>
            Está trabajando como el usuario {{ this.storage.otherUserPk.username }}.
            <b-link @click="stopMasquerading">Terminar</b-link>
        </b-alert>
    </div>
</template>

<script>
import Navbar from './components/Navbar'
export default {
    components: {
        Navbar
    },
    computed: {
        masquerading: function() { return this.storage.otherUserPk },
    },
    methods: {
        stopMasquerading() {
            this.storage.otherUserPk = 0;
            this.$router.replace({ name: "adminHome" });
        }
    }
}
</script>
