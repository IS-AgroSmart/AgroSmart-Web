<template>
    <div class="my-4">
        <b-card title="" class="mb-2">
            <div class="text-center">
            <b-button :to="{name: 'newFlight'}" variant="primary">Crear nuevo</b-button></div>
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
    props: ["flight"]
}
</script>