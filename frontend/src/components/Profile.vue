<template>
    <div class="pt-3" style="padding-left:15px; padding-right:15px;">
        <h1>Perfil</h1>
    
        <b-container>
            <b-container class="py-2">
                Nombre: {{ storage.loggedInUser.first_name }}
            </b-container>
            <b-container class="py-2">
                Usuario: {{ storage.loggedInUser.username }}
            </b-container>
            <b-container class="py-2">
                Organización: {{ storage.loggedInUser.organization }}
            </b-container>
            <b-container class="py-2">
                Correo Electrónico: {{ storage.loggedInUser.email }}
            </b-container>
            <b-container class="py-2">
                Contraseña: ********
                <b-button to="changePassword" variant="outline-primary">Cambiar</b-button>
            </b-container>
        </b-container>
    </div>
</template>

