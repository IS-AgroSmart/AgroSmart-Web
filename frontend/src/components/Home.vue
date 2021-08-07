<template>
    <div>
        <div class="custom-jumbotron">
            <b-container class="text-white">
                <b-img class="bg" fluid alt="ortomosaico" src="/field.jpg" />
                <b-row align-content="center">
                    <b-col md="8" lg="7" order-md="1">
                        <h1 >AgroSmart</h1>
                        <p class="lead">Procesamiento de imágenes de drones</p>
                        <p>Genere mapas, nubes de puntos y modelos de elevación a partir de imágenes aéreas.</p>
                    </b-col>
    
                </b-row>
                <b-button variant="primary" to="flights" v-if="loggedIn">Mi cuenta</b-button>
                <b-button variant="primary" to="signup" v-else>Crear cuenta</b-button>
            </b-container>
        </div>
    
        <div class="bg-white">
            <b-container class="pb-5">
                <b-row align-h="center" class="py-5">
                    <h1>Características</h1>
                </b-row>
                <b-row class="text-center">
                    <b-col md>
                        <div class="mb-2">
                            <b-img width="160" height="160" src="/orthomosaic.png" rounded="circle" thumbnail/>
                        </div>
                        <div>
                            <h5>Ortomosaicos</h5>
                            <p>Mapas georreferenciados del terreno, en formatos PNG y GeoTIFF</p>
                        </div>
                    </b-col>
                    <b-col md>
                        <div class="mb-2">
                            <b-img width="160" height="160" src="/pointcloud.png" rounded="circle" thumbnail/>
                        </div>
                        <div>
                            <h5>Nubes de puntos</h5>
                            <p>Nubes de puntos georreferenciadas</p>
                        </div>
                    </b-col>
                    <b-col md>
                        <div class="mb-2">
                            <b-img width="160" height="160" src="https://www.opendronemap.org/wp-content/uploads/2018/07/dem-130x130.png" rounded="circle" thumbnail/>
                        </div>
                        <div>
                            <h5>Modelos de elevación</h5>
                            <p>Modelos de elevación (DEM) y de superficie (DSM)</p>
                        </div>
                    </b-col>
                </b-row>
                <b-row class="text-center">
                    <b-col md>
                        <div class="mb-2">
                            <b-img width="160" height="160" src="https://www.opendronemap.org/wp-content/uploads/2020/02/ndvi.jpg" rounded="circle" thumbnail/>
                        </div>
                        <div>
                            <h5>Índices de vegetación</h5>
                            <p>NDVI, NDRE e índices personalizados</p>
                        </div>
                    </b-col>
                    <b-col md>
                        <div class="mb-2">
                            <b-img width="160" height="160" src="/measurements.jpg" rounded="circle" thumbnail/>
                        </div>
                        <div>
                            <h5>Mediciones</h5>
                            <p>Mediciones de longitud y área</p>
                        </div>
                    </b-col>
                    <b-col md>
                        <div class="mb-2">
                            <b-img width="160" height="160" src="/corn_colorized.jpg" rounded="circle" thumbnail/>
                        </div>
                        <div>
                            <h5>Imágenes multiespectrales</h5>
                            <p>Procese imágenes multiespectrales tomadas con Micasense Rededge</p>
                        </div>
                    </b-col>
                </b-row>
                <b-row align-h="center" class="py-5">
                    <h1>Precios</h1>
                </b-row>
                <b-row class="text-center">
                    <b-col>
                        <b-card header="Demo" header-tag="h4" title-tag="title">
                            <b-card-body>
                                <b-card-title title-tag="h1">
                                    $0<small class="text-muted">/mes</small>
                                </b-card-title>
                                <ul class="list-unstyled">
                                    <li>Acceso a vuelos y proyectos demo</li>
                                    <li>Sin límite de tiempo</li>
                                </ul>
                                <b-button variant="outline-primary" to="signup" v-if="!loggedIn">Crear cuenta</b-button>
                            </b-card-body>
                        </b-card>
                    </b-col>
                    <b-col>
                        <b-card header="Básico" header-tag="h4" title-tag="title">
                            <b-card-body>
                                <b-card-title title-tag="h1">
                                    $65<small class="text-muted">/mes</small>
                                </b-card-title>
                                <ul class="list-unstyled">
                                    <li>3000 imágenes mensuales</li>
                                    <li>Vuelos y proyectos ilimitados</li>
                                    <li>45 GB de almacenamiento</li>
                                </ul>
                                <b-button variant="primary" to="login" v-if="!loggedIn">Iniciar sesión</b-button>
                                <b-button variant="primary" to="flights" v-else>Mis vuelos</b-button>
                            </b-card-body>
                        </b-card>
                    </b-col>
                </b-row>
            </b-container>
        </div>
    </div>
</template>

<style scoped>
.custom-jumbotron {
    padding: 4rem 2rem;
    margin-bottom: 2rem;
    background-color: #e9ecef00;
    border-radius: .3rem;
}

.bg {
    position: fixed;
    right: 0;
    top: 0;
    left: 0;
    z-index: -1;
}
</style>

<script>
export default {
    computed: {
        loggedIn() {
            return this.$isLoggedIn()
        }
    },
}
</script>