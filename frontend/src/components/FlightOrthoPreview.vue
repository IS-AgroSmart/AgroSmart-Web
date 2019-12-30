<template>
    <div>
        <h1>
            {{ flight.name }}
            <small>{{ flightDate }}</small>
        </h1>
        <vl-map :load-tiles-while-animating="true" :load-tiles-while-interacting="true" style="height: 400px">
            <vl-view :zoom.sync="zoom" :center.sync="center" :rotation.sync="rotation"></vl-view>
    
            <vl-layer-tile id="osm">
                <vl-source-osm></vl-source-osm>
            </vl-layer-tile>

            <vl-layer-image>
                <!--<vl-source-image-wms url="https://ahocevar.com/geoserver/wms" layers="topp:states" serverType="geoserver"></vl-source-image-wms>-->
                <vl-source-image-wms url="/geoserver/geoserver/ows" layers="flight_bf923e98-b5f7-47ef-88a0-3fdf865520b7:odm_orthophoto" serverType="geoserver"></vl-source-image-wms>
            </vl-layer-image>

            
    
            
        </vl-map>
    </div>
</template>

<script>
import axios from 'axios'
//import VueLayers from 'vuelayers'

// create custom projection for image 
// NOTE: VueLayers.olExt available only in UMD build
// in ES build it should be imported explicitly from 'vuelayers/lib/ol-ext'
/* let customProj = VueLayers.olExt.createProj({
    code: 'xkcd-image',
    units: 'pixels',
    extent,
})
// add it to the list of known projections
VueLayers.olExt.addProj(customProj) */

export default {
    data() {
        return {
            zoom: 2,
            center: [0,0],
            rotation: 0,
            flight: {}
        }
    },
    computed: {
        flightDate() {
            return this.$moment(this.flight.date, "YYYY-MM-DD").format("dddd D [de] MMMM, YYYY")
        },
    },
    created() {
        if (!this.$isLoggedIn()) {
            this.$router.push("/login");
        }

        axios
            .get("api/flights/" + this.$route.params.uuid, {
                headers: { "Authorization": "Token " + this.storage.token }
            })
            .then(response => {
                this.flight = response.data;
                this.flightLoaded = true;
            })
            .catch(error => this.error = error);
    }
}
</script>