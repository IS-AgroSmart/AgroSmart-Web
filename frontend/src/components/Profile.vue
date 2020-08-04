<template>
    <div>
        <div class=" container py-5">
            <b-img :src="require('../assets/person-circle.svg')" class="mb-1 col-md-3" fluid center></b-img>
        </div>
        <div class="container pt-5 pb-3">
            <h3 class="container py-2">
                Nombre: {{ storage.loggedInUser.first_name }}
            </h3>
            <h3 class="container py-2">
                Usuario: {{ storage.loggedInUser.username }}
            </h3>
            <h3 class="container py-2">
                Organización: {{ storage.loggedInUser.organization }}
            </h3>
            <h3 class="container py-2">
                Correo Electrónico: {{ storage.loggedInUser.email }}
            </h3>
            <b-container fuild="sm">
                <b-row>
                    <b-col>
                        <h3 class="py-2">
                        Contraseña: ********
                        </h3>
                    </b-col>
                    <b-col class="text-center">
                        <b-button to="changePassword" variant="primary">Cambiar </b-button>
                    </b-col>
                 </b-row>
            </b-container>
        </div>
    </div> 
</template>

