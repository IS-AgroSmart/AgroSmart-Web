<template>
    <div>
        <b-navbar toggleable="lg" type="dark" variant="info">
            <b-navbar-brand to="/">AgroSmart</b-navbar-brand>
    
            <b-navbar-toggle target="nav-collapse"></b-navbar-toggle>
    
            <b-collapse id="nav-collapse" is-nav>
                <b-navbar-nav v-if="isLoggedIn">
                    <b-nav-item to="/flights" data-cy="navbar-flights">Vuelos</b-nav-item>
                    <b-nav-item to="/flights/deleted">Vuelos eliminados</b-nav-item>
                    <b-nav-item to="/projects">Proyectos</b-nav-item>
                    <b-nav-item to="/projects/deleted">Proyectos eliminados</b-nav-item>
                </b-navbar-nav>
    
                <!-- Right aligned nav items -->
                <b-navbar-nav class="ml-auto">
                    <div v-if="isLoggedIn">
                        <b-nav-item-dropdown right>
                            <!-- Using 'button-content' slot -->
                            <template v-slot:button-content><em>Mi cuenta</em>
                            </template>
                        <b-dropdown-item to="/profile">Perfil</b-dropdown-item>
                        <b-dropdown-item v-if="isAdmin" to="/admin">Administración</b-dropdown-item>
                        <b-dropdown-item to="/logout">Cerrar sesión</b-dropdown-item>
                    </b-nav-item-dropdown>
                    </div>
                    <div v-else>
                        <b-nav-item to="/login" data-cy="navbar-login">Iniciar sesión</b-nav-item>
                    </div>
    
                </b-navbar-nav>
            </b-collapse>
        </b-navbar>
    </div>
</template>

<script>
export default {
    data: function() {
        return {

        };
    },
    computed: {
        isLoggedIn() { return this.storage.token != ""; },
        isAdmin() { return this.storage.loggedInUser != null && this.storage.loggedInUser.type == "ADMIN"; },
    },
}
</script>