Ext.require([
    'GeoExt.component.Map',
    'GeoExt.data.store.LayersTree'
]);

var mapComponent;
var mapPanel;
var treePanel, timeSlider;

// const TIMES = ["2019-10-15", "2019-10-23", "2019-10-28", "2019-10-30", "2019-11-06"];
var TIMES = [];

// fetch(window.location.protocol + "//" + window.location.host + "/geoserver/geoserver/project_a4029f71-835b-474c-92a3-ccc05ce5de2e/mainortho/wms?service=WMS&version=1.3.0&request=GetCapabilities")
fetch(window.location.protocol + "//" + window.location.host + "/geoserver/geoserver/" + project_path + "/mainortho/wms?service=WMS&version=1.3.0&request=GetCapabilities")
    .then(response => response.text())
    .then(str => (new window.DOMParser()).parseFromString(str, "text/xml"))
    .then(data => {
        let times;
        times = data.getElementsByTagName("WMS_Capabilities")[0].getElementsByTagName("Capability")[0].getElementsByTagName("Layer")[0].getElementsByTagName("Dimension")[0].innerHTML;
        TIMES = [];
        for (var time of times.split(",")) {
            TIMES.push(time.substring(0, 10));
        }
    })
    .then(() => initApp());

let olMap;
proj4.defs('EPSG:32617', '+proj=utm +zone=17 +datum=WGS84 +units=m +no_defs')
proj4.defs('EPSG:32717', '+proj=utm +zone=17 +south +datum=WGS84 +units=m +no_defs')
proj4.defs('EPSG:4326', '+proj=longlat +datum=WGS84 +no_defs')

function initApp() {
    Ext.application({
        name: 'BasicTree',
        launch: function () {
            var source1, source2, source3;
            var layer1, layer2, layer3, layer4, layer5;
            var group1, group2, group3;
            var treeStore;

            group3 = new ol.layer.Group({
                name: "Mapas base",
                layers: [
                    new ol.layer.Tile({
                        name: "Satélite (ArcGIS/ESRI)",
                        source: new ol.source.XYZ({
                            attributions: ['Powered by Esri',
                                'Source: Esri, DigitalGlobe, GeoEye, Earthstar Geographics, CNES/Airbus DS, USDA, USGS, AeroGRID, IGN, and the GIS User Community'],
                            attributionsCollapsible: false,
                            url: 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                            maxZoom: 23
                        })
                    }),
                    new ol.layer.Tile({
                        name: "OpenStreetMap",
                        source: new ol.source.OSM(),
                        visible: false
                    }),
                ],
            });

            layer5 = new ol.layer.Image({
                name: "Ortomosaico RGB",
                source: new ol.source.ImageWMS({
                    url: window.location.protocol + "//" + window.location.host + "/geoserver/geoserver/ows?version=1.3.0",
                    params: {"LAYERS": project_path + ":mainortho"}
                })
            });
            var vector = new ol.layer.Vector({
                name: "Polígono",
                source: new ol.source.Vector({
                    format: new ol.format.GeoJSON(),
                    projection: 'EPSG:4326',
                    url: window.location.protocol + "//" + window.location.host + "/geoserver/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=test:poly&maxFeatures=50&outputFormat=application/json&"
                    //url: window.location.protocol + "//" + window.location.host + "/geoserver/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=test:poly&maxFeatures=50&outputFormat=application/json&"
                })
            });

            group2 = new ol.layer.Group({
                name: "Imágenes",
                layers: [layer5, vector],
            });

            olMap = new ol.Map({
                layers: [group3, group2],
                view: new ol.View({
                    center: [0, 0],
                    zoom: 2,
                    minZoom: 2,
                    maxZoom: 19
                })
            });

            var zoomslider = new ol.control.ZoomSlider();
            olMap.addControl(zoomslider);


            mapComponent = Ext.create('GeoExt.component.Map', {
                map: olMap
            });

            timeSlider = Ext.create('Ext.slider.Single', {
                width: 200,
                value: TIMES.length - 1,
                increment: 1,
                minValue: 0,
                maxValue: TIMES.length - 1,
                useTips: true,
                tipText: function (thumb) {
                    return TIMES[thumb.value];
                },
            });

            var dateLabel = Ext.create('Ext.form.Label', {
                text: "None"
            });

            timeSlider.on("change", function (slider, newValue, thumb, eOpts) {
                updateTime(layer5, dateLabel, newValue);
            });
            updateTime(layer5, dateLabel, TIMES.length - 1);

            var timePanel;
            if (moreThanOneFlight) {
                timePanel = Ext.create('Ext.panel.Panel', {
                    bodyPadding: 5,  // Don't want content to crunch against the borders
                    width: 300,
                    title: 'Tiempo',
                    items: [timeSlider, dateLabel],
                    renderTo: Ext.getBody()
                });
            }

            mapPanel = Ext.create('Ext.panel.Panel', {
                region: 'center',
                border: false,
                layout: 'fit',
                items: [mapComponent]
            });

            treeStore = Ext.create('GeoExt.data.store.LayersTree', {
                layerGroup: olMap.getLayerGroup()
            });

            treePanel = Ext.create('Ext.tree.Panel', {
                title: project_name,
                viewConfig: {
                    plugins: {ptype: 'treeviewdragdrop'}
                },
                store: treeStore,
                rootVisible: false,
                flex: 1,
                border: false
            });

            var description = Ext.create('Ext.panel.Panel', {
                contentEl: 'description',
                title: 'Descripción',
                height: 200,
                border: false,
                bodyPadding: 5
            });

            Ext.create('Ext.Viewport', {
                layout: 'border',
                items: [
                    mapPanel,
                    {
                        xtype: 'panel',
                        region: 'west',
                        width: 400,
                        layout: {
                            type: 'vbox',
                            align: 'stretch'
                        },
                        items: moreThanOneFlight ? [treePanel, description, timePanel] : [treePanel, description]
                    }
                ]
            });
        }
    });

    fetch(window.location.protocol + "//" + window.location.host + "/mapper/" + uuid + "/bbox")
        .then(response => response.json())
        .then(data => {
            console.log(data);
            const minCoords = ol.proj.transform([data.bbox.minx, data.bbox.miny], data.srs, "EPSG:3857")
            console.log(minCoords);
            const maxCoords = ol.proj.transform([data.bbox.maxx, data.bbox.maxy], data.srs, "EPSG:3857")
            console.log(maxCoords);
            olMap.getView().fit(minCoords.concat(maxCoords), olMap.getSize());
        });
}

function updateTime(layer, label, val) {
    layer.getSource().updateParams({'TIME': TIMES[val]});
    label.setText(TIMES[val]);
}
