<template>
    <b-dropdown :text="title" ref="dropdown" class="m-2">
        <b-dropdown-form>
            <b-form-group class="mb-0">
                <b-form-input v-model="search" type="search" size="sm" autocomplete="off" :placeholder="placeholder"></b-form-input>
            </b-form-group>
        </b-dropdown-form>
        <b-dropdown-divider></b-dropdown-divider>
        <b-dropdown-item-button v-for="elem in availableElems" :key="elem[keyField]" @click="$emit('element-clicked', elem)">
            {{ nameFunc(elem) }}
        </b-dropdown-item-button>
        <b-dropdown-text v-if="availableElems.length === 0">
            {{ emptyMessage }}
        </b-dropdown-text>
    </b-dropdown>
</template>

<script>
export default {
    data() {
        return {
            search: ""
        };
    },
    computed: {
        elemsCriteria() {
            return this.search.trim().toLowerCase()
        },
        availableElems() {
            if (this.elemsCriteria) {
                let filterLambda = (e) => this.filterCriteria(e, this.elemsCriteria);
                return this.elements.filter(filterLambda);
            }
            return this.elements;
        },
    },
    props: ["elements", "title", "placeholder", "nameFunc", "filterCriteria", "keyField", "emptyMessage"],
}
</script>