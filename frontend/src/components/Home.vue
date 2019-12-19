<template>
    <div>

    </div>
</template>

<script>
export default {
    name: "Home",

    props: {

    },

    data() {
        return {
            
        }
    },

    methods: {
        readNews(newsNum){
            this.$emit('read', newsNum);
        }
    }
}
</script>