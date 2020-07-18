<template>
    <div class="my-4">
        <h1>Administración</h1>
        <b-row class="my-4">
            <b-col align="center">
                <h4 class="my-2">Administración de usuarios</h4>
                <b-row class="my-1">
                    <b-col>
                        <b-button>Solicitudes de cuenta</b-button>
                    </b-col>
                </b-row>
                <b-row class="my-1">
                    <b-col>
                        <b-dropdown text="Emular usuario" ref="dropdown" class="m-2">
                            <b-dropdown-form>
                                <b-form-group class="mb-0">
                                    <b-form-input v-model="search" id="tag-search-input" type="search" size="sm" autocomplete="off" placeholder="Buscar usuarios..."></b-form-input>
                                </b-form-group>
                            </b-dropdown-form>
                            <b-dropdown-divider></b-dropdown-divider>
                            <b-dropdown-item-button v-for="user in availableUsers" :key="user.pk" @click="onUserClick(user)">
                                {{ user.username }} ({{ user.email }})
                            </b-dropdown-item-button>
                            <b-dropdown-text v-if="availableUsers.length === 0">
                                ¡Ningún usuario tiene este username o email!
                            </b-dropdown-text>
                        </b-dropdown>
                    </b-col>
                </b-row>
            </b-col>
            <b-col align="center">
                <h4 class="my-2">Administración de vuelos</h4>
            </b-col>
        </b-row>
    </div>
</template>

<script>
import axios from "axios";

export default {
    data() {
        return {
            search: "",
            users: [],
        }
    },
    // https://bootstrap-vue.org/docs/components/form-tags#advanced-custom-rendering-usage for the live search
    computed: {
        criteria() {
            return this.search.trim().toLowerCase()
        },
        availableUsers() {
            const criteria = this.criteria;
            if (criteria) {
                return this.users.filter(user => user.username.toLowerCase().indexOf(criteria) > -1 ||
                    user.email.toLowerCase().indexOf(criteria) > -1);
            }
            return this.users;
        },
    },
    methods: {
        onUserClick(user) {
            this.storage.otherUserPk = user;
            this.$router.push("/flights");
        }
    },
    created() {
        axios
            .get('api/users', {
                headers: { "Authorization": "Token " + this.storage.token }
            })
            .then(response => (this.users = response.data))
            .catch(error => this.error = error);
    },
}
</script>