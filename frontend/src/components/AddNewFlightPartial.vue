<template>
    <div class="my-4">
        <b-card title="" class="mb-2">
            <div class="text-center">
            <b-button :to="{name: 'newFlight'}" variant="primary">Crear vuelo</b-button></div>
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
    props: ["flight"],
    mixins: [forceLogin]
}
</script>