<template>
    <div class=" pt-3" style="padding-left:15px; padding-right:15px;">
        <vl-map v-if="flightLoaded" :load-tiles-while-animating="true" :load-tiles-while-interacting="true" style="height: 800px" ref="map" :data-projection="projection">
            <vl-view :zoom.sync="zoom" :center.sync="center" :rotation.sync="rotation" ref="mapView" :projection="projection"></vl-view>
    
            <vl-layer-tile id="satellite">
                <vl-source-xyz url="https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"></vl-source-xyz>
            </vl-layer-tile>
            <vl-layer-tile id="mosaic">
                <vl-source-wms :url="geoserverWorkspaceUrl" :layers="layerName" serverType="geoserver" ref="mySource"></vl-source-wms>
            </vl-layer-tile>
    
        </vl-map>
    
        <model-obj v-if="flightLoaded" :src="modelUrl"></model-obj>
    </div>
</template>

<script>
import axios from 'axios'
import forceLogin from './mixins/force_login'
import { register } from 'ol/proj/proj4'
import proj4 from 'proj4'
import { ModelObj } from 'vue-3d-model';

proj4.defs('EPSG:32617', '+proj=utm +zone=17 +datum=WGS84 +units=m +no_defs')
proj4.defs('EPSG:32717', '+proj=utm +zone=17 +south +datum=WGS84 +units=m +no_defs')
proj4.defs('EPSG:32634', '+proj=utm +zone=34 +datum=WGS84 +units=m +no_defs')
proj4.defs('EPSG:4326', '+proj=longlat +datum=WGS84 +no_defs')
register(proj4)

export default {
    components: { ModelObj },
    data() {
        return {
            zoom: 2,
            center: [0, 0],
            rotation: 0,
            flight: {},
            flightLoaded: false,
            projection: "EPSG:4326",
        }
    },
    computed: {
        workspaceName() {
            return `flight_${this.flight.uuid}`;
        },
        layerName() {
            return  `${this.workspaceName}:odm_orthophoto`;
        },
        modelUrl() {
            return "/api/downloads/" + this.flight.uuid + "/3dmodel_texture"
        },
        geoserverWorkspaceUrl() {
            return `/geoserver/geoserver/${this.workspaceName}/wms`;
        }
    },
    methods: {
        parseExtents() {
            axios.get("/api/preview/" + this.flight.uuid)
                .then((response) => {
                    this.projection = response.data.srs;
                    //this.$refs.mapView.$view.projection = response.data.srs;
                    let newExtents = [response.data.bbox.minx, response.data.bbox.miny, response.data.bbox.maxx, response.data.bbox.maxy]
                    window.setTimeout(() => this.$refs.mapView.$view.fit(newExtents, {
                        size: this.$refs.map.$map.getSize(),
                        duration: 1000
                    }), 1000);


                })
        }
    },
    created() {
        axios
            .get("api/flights/" + this.$route.params.uuid, {
                headers: Object.assign({ "Authorization": "Token " + this.storage.token }, this.storage.otherUserPk ? { TARGETUSER: this.storage.otherUserPk.pk } : {}),
            })
            .then(response => {
                this.flight = response.data;
                this.flightLoaded = true;
                this.parseExtents();
            })
            .catch(error => this.error = error);
    },
    mixins: [forceLogin]
}
</script>
