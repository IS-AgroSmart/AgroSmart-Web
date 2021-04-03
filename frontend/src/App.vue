<template>
    <div id="app" style="display: flex; flex-flow: column; height: 100%; width: 100%">
        <navbar></navbar>
    
        <b-container fluid style="flex-grow: 1; padding:0">
            <router-view></router-view>
        </b-container>
    
        <b-alert style="height:100px; z-index: 2000;" v-if="this.storage.otherUserPk" class="position-fixed fixed-bottom m-0 rounded-0" variant="warning" show>
            Está trabajando como el usuario {{ this.storage.otherUserPk.username }}.
            <b-link @click="stopMasquerading">Terminar</b-link>
        </b-alert>
        <custom-footer/>
    </div>
</template>

<script>
import Navbar from './components/Navbar'
import CustomFooter from './components/CustomFooter'

export default {
    components: {
        Navbar,
        CustomFooter
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

<style>
html, 
body {
    height: 100%;
}
</style>