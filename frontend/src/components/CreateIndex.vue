<template>
    <div class="pt-3" style="padding-left:15px; padding-right:15px;">
        <b-alert variant="success" show v-if="indexOK">Índice correcto</b-alert>
        <b-alert variant="danger" show v-if="indexWrong">Error en la fórmula</b-alert>
        <b-alert variant="danger" show v-if="uploadError">{{ uploadError }}</b-alert>
    
        <div>
            <b-button-toolbar key-nav justify>
                <b-button @click="addText('red')" variant="danger">R</b-button>
                <b-button @click="addText('green')" variant="success">G</b-button>
                <b-button @click="addText('blue')" variant="primary">B</b-button>
                <b-button @click="addText('nir')" variant="secondary">NIR</b-button>
                <b-button @click="addText('rdedge')" variant="dark">Red Edge</b-button>
                <b-button @click="addText('(')" variant="info">(</b-button>
                <b-button @click="addText(')')" variant="info">)</b-button>
                <b-button @click="addText('+')" variant="info">+</b-button>
                <b-button @click="addText('-')" variant="info">-</b-button>
                <b-button @click="addText('/')" variant="info">/</b-button>
            </b-button-toolbar>
        </div>
        <div class="row">
            <div class="col my-3">
                <b-form @submit="onSubmit">
                    <b-form-group>
                        <b-input type="text" v-model="name" placeholder="Escriba el nombre del índice" required/>
                    </b-form-group>
                    <b-form-group>
                        <b-input v-debounce:1s="checkFormula" type="text" v-model="formula" placeholder="Escriba la fórmula" required/>
                    </b-form-group>
    
                    <b-button :disabled="!indexOK || uploading" type="submit" variant="primary">
                        <div class="spinner-border spinner-border-sm" role="status" v-if="uploading">
                            <span class="sr-only">Checking...</span>
                        </div>
                        Confirmar
                    </b-button>
                </b-form>
            </div>
        </div>
    
        <div class="row">
            <div class="col">
                <div role="tablist">
                    <b-card no-body class="mb-1">
                        <b-card-header header-tag="header" class="p-1" role="tab">
                            <b-button block v-b-toggle.accordion-1 variant="info">Ayuda</b-button>
                        </b-card-header>
                        <b-collapse id="accordion-1" visible accordion="my-accordion" role="tabpanel">
                            <b-card-body>
                                <b-card-text>
                                    <ul>
                                        <li>Las bandas se llaman "red", "green", "blue", "nir" y "rdedge".</li>
                                        <li>Las operaciones permitidas son +, -, *, / y ** (exponenciación).</li>
                                        <li>Asegure que el resultado esté en el rango [0, 255]</li>
                                    </ul>
                                </b-card-text>
                            </b-card-body>
                        </b-collapse>
                    </b-card>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import axios from "axios"
import forceLogin from './mixins/force_login'

export default {
    data() {
        return {
            name: "",
            formula: "",
            indexOK: false,
            indexWrong: false,
            uploadError: "",
            uploading: false,
        }
    },
    methods: {
        onSubmit(evt) {
            evt.preventDefault()

            var that = this;
            this.uploading = true;
            var data = new FormData();
            data.append("formula", this.formula);
            data.append("index", this.name);

            data.append("title", this.title);
            axios.post('/api/rastercalcs/' + this.$route.params.uuid, { formula: this.formula, index: this.name }, {
                    headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                })
                .then(function() {
                    window.history.back();
                })
                .catch(function(error) {
                    that.indexOK = false;
                    if(error.response?.status == 402)
                        that.uploadError = "Operación fallida. Su almacenamiento está lleno.";
                    else
                        that.uploadError = "Operación fallida.";
                    that.uploading = false;
                });
        },
        checkFormula() {
            var that = this;
            this.uploading = true;
            var formdata = new FormData();
            formdata.set("formula", this.formula);
            axios.post('/api/rastercalcs/check', formdata, {
                    headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
                })
                .then(function() {
                    that.uploading = false;
                    that.indexOK = true;
                    that.indexWrong = false;
                })
                .catch(function() {
                    that.indexOK = false;
                    that.indexWrong = true;
                    that.uploading = false;
                });
        },
        addText(band) { this.formula += band; }
    },
    mixins: [forceLogin]
}
</script>