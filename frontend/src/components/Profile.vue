<template>
    <div>
        <div class=" container py-5">
            <b-img :src="require('../assets/person-circle.svg')" class="mb-1 col-md-3" fluid center></b-img>
        </div>
        <div class="container pt-5 pb-3">
            <h3 class="container py-2">
                Nombre: 
            </h3>
            <h3 class="container py-2">
                Usuario: 
            </h3>
            <h3 class="container py-2">
                Organización: 
            </h3>
            <h3 class="container py-2">
                Correo Electrónico:
            </h3>
            <b-container fuild="sm">
                <b-row>
                    <b-col>
                        <h3 class="py-2">
                        Contraseña:
                        </h3>
                    </b-col>
                    <b-col class="text-center">
                        <b-button to="signUp" variant="primary">Cambiar </b-button>
                    </b-col>
                 </b-row>
            </b-container>
        </div>
    </div> 
</template>

<script>
//import axios from 'axios';
export default{
    data() {
        return {
            username: '',
            password: '',
            email: '',
            users: [],
        }
    },
}

