<template>
<div>
    <p>Vuelos</p>

    {{info}}</div>
</template>

<script>
import axios from 'axios';

export default {
    data() {
        return {info: null}
    },
    created() {
        axios
            .get('nodeodm/info')
            .then(response => (this.info = response));
        window.console.log("Ping")
    }
}
</script>