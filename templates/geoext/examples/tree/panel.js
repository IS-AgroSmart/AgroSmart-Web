Ext.require([
    'GeoExt.component.Map',
    'GeoExt.data.store.LayersTree'
]);

let mapComponent;
let mapPanel;
let treePanel, timeSlider;

let TIMES = [];
let shapefiles = [], indices = [];

let noCacheHeaders = new Headers(); // HACK: Force disable cache, otherwise timing problem when going back to screen
noCacheHeaders.append('pragma', 'no-cache');
noCacheHeaders.append('cache-control', 'no-cache');

// fetch(window.location.protocol + "//" + window.location.host + "/geoserver/geoserver/project_a4029f71-835b-474c-92a3-ccc05ce5de2e/mainortho/wms?service=WMS&version=1.3.0&request=GetCapabilities")
fetch(window.location.protocol + "//" + window.location.host + "/geoserver/geoserver/" + project_path + "/mainortho/wms?service=WMS&version=1.3.0&request=GetCapabilities",
    {headers: noCacheHeaders})
    .then(response => response.text())
    .then(str => (new window.DOMParser()).parseFromString(str, "text/xml"))
    .then(data => {
        let times;
        times = data.getElementsByTagName("WMS_Capabilities")[0].getElementsByTagName("Capability")[0].getElementsByTagName("Layer")[0].getElementsByTagName("Dimension")[0].innerHTML;
        TIMES = [];
        for (let time of times.split(",")) {
            TIMES.push(time.substring(0, 10));
        }
    })
    .then(fillShapefiles)
    .then(fillRasters)
    .then(initApp);

let olMap;
proj4.defs('EPSG:32617', '+proj=utm +zone=17 +datum=WGS84 +units=m +no_defs');
proj4.defs('EPSG:32717', '+proj=utm +zone=17 +south +datum=WGS84 +units=m +no_defs');
proj4.defs('EPSG:32634', '+proj=utm +zone=34 +datum=WGS84 +units=m +no_defs')
proj4.defs('EPSG:4326', '+proj=longlat +datum=WGS84 +no_defs');

let popup;

function initApp() {
    Ext.application({
        launch: function () {
            let rgbLayer;
            let rasterGroup, basemapsGroup, shapefilesGroup, indicesGroup;
            let treeStore;

            basemapsGroup = new ol.layer.Group({
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

            rgbLayer = new ol.layer.Image({
                name: "Ortomosaico RGB",
                source: new ol.source.ImageWMS({
                    url: window.location.protocol + "//" + window.location.host + "/geoserver/geoserver/ows?version=1.3.0",
                    params: {"LAYERS": project_path + ":mainortho"}
                })
            });

            rasterGroup = new ol.layer.Group({
                name: "Imágenes",
                layers: [rgbLayer],
            });

            shapefilesGroup = new ol.layer.Group({
                name: "Shapefiles & GeoTIFFs",
                layers: shapefiles,
            });

            indicesGroup = new ol.layer.Group({
                name: "Índices",
                layers: indices,
            });

            olMap = new ol.Map({
                layers: [basemapsGroup, rasterGroup, shapefilesGroup].concat(isMultispectral ? [indicesGroup] : []),
                view: new ol.View({
                    center: [0, 0],
                    zoom: 2,
                    minZoom: 2,
                    maxZoom: 19
                }),
                target: 'map',
            });

            fitMap(); // Must happen after olMap is defined!

            let zoomslider = new ol.control.ZoomSlider();
            let RotateNorthControl = function (opt_options) {

                var options = opt_options || {};

                var button = document.createElement('button');
                button.innerHTML = 'N';

                var this_ = this;
                var handleClick = function () {
                    this_.getMap().getView().setRotation(this_.getMap().getView().getRotation() == 0 ? 45 : 0);
                };

                button.addEventListener('click', handleClick, false);
                button.addEventListener('touchstart', handleClick, false);

                var element = document.createElement('div');
                element.className = 'rotate-north ol-unselectable ol-control';
                element.appendChild(button);

                ol.control.Control.call(this, {
                    element: element,
                    target: options.target
                });

            };
            ol.inherits(RotateNorthControl, ol.control.Control);
            olMap.addControl(zoomslider);
            olMap.addControl(new RotateNorthControl());

            // Add legend, only if there is at least one index
            if (indices.length > 0) {
                let LegendControl = function (opt_options) {
                    var options = opt_options || {};
                    var img = document.createElement('img');
                    var someIndexLayer = indices[0].getSource().getParams()["LAYERS"];
                    img.setAttribute("src", window.location.protocol + "//" + window.location.host + "/geoserver/geoserver/ows?service=wms&version=1.3.0&request=GetLegendGraphic&format=image/png&layer=" + someIndexLayer);
                    var element = document.createElement('div');
                    element.className = 'legend ol-unselectable ol-control';

                    element.appendChild(img);

                    ol.control.Control.call(this, {
                        element: element,
                        target: options.target
                    });
                };
                ol.inherits(LegendControl, ol.control.Control);
                olMap.addControl(new LegendControl());
            }

            popup = Ext.create('GeoExt.component.Popup', {
                map: olMap,
                width: 140
            });
            var selectClick = new ol.interaction.Select({
                condition: ol.events.condition.click,
                layers: (layer) => layer instanceof ol.layer.Vector,
            });
            selectClick.on('select', function (e) {
                if (e.selected.length == 0) {
                    popup.hide();
                    return;
                }
                let coordinate = e.mapBrowserEvent.coordinate;

                let message = "<p>";
                for (const [key, value] of Object.entries(e.selected[0].getProperties())) {
                    if (["bbox", "geometry"].includes(key)) continue;
                    message += key + " ⟶ " + value + "<br>";
                }
                message += "</p>";
                popup.setHtml(message);
                popup.position(coordinate);
                popup.show();
            });
            olMap.addInteraction(selectClick);


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

            let dateLabel = Ext.create('Ext.form.Label', {
                text: "None"
            });

            timeSlider.on("change", function (slider, newValue, thumb, eOpts) {
                updateTime(rgbLayer, dateLabel, newValue);
                for (let index of indices) {
                    updateTime(index, dateLabel, newValue);
                }
            });
            updateTime(rgbLayer, dateLabel, TIMES.length - 1);
            for (let index of indices) {
                updateTime(index, dateLabel, TIMES.length - 1);
            }

            let timePanel;
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

            let description = Ext.create('Ext.panel.Panel', {
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
        },
        name: 'BasicTree'
    });
}

function fillShapefiles() {
    return fetch(window.location.protocol + "//" + window.location.host + "/mapper/" + uuid + "/artifacts",
        {headers: noCacheHeaders})
        .then(response => response.json())
        .then(data => {
                for (let art of data.artifacts) {
                    if (art.type === "SHAPEFILE")
                        shapefiles.push(new ol.layer.Vector({
                            name: art.name,
                            source: new ol.source.Vector({
                                format: new ol.format.GeoJSON(),
                                projection: 'EPSG:4326',
                                url: window.location.protocol + "//" + window.location.host + "/geoserver/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=" + art.layer + "&maxFeatures=50&outputFormat=application/json&"
                                //url: window.location.protocol + "//" + window.location.host + "/geoserver/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=test:poly&maxFeatures=50&outputFormat=application/json&"
                            })
                        }));
                    else if (art.type === "ORTHOMOSAIC")
                        shapefiles.push(new ol.layer.Image({
                            name: art.name,
                            source: new ol.source.ImageWMS({
                                url: window.location.protocol + "//" + window.location.host + "/geoserver/geoserver/ows?version=1.3.0",
                                params: {"LAYERS": art.layer}
                            })
                        }));
                }
            }
        );
}

function fillRasters() {
    return fetch(window.location.protocol + "//" + window.location.host + "/mapper/" + uuid + "/indices",
        {headers: noCacheHeaders})
        .then(response => response.json())
        .then(data => {
                for (let index of data.indices) {
                    indices.push(new ol.layer.Image({
                        name: index.title,
                        source: new ol.source.ImageWMS({
                            url: window.location.protocol + "//" + window.location.host + "/geoserver/geoserver/ows?version=1.3.0",
                            params: {"LAYERS": index.layer}
                        })
                    }));
                }
            }
        );
}

function fitMap() {
    fetch(window.location.protocol + "//" + window.location.host + "/mapper/" + uuid + "/bbox",
        {headers: noCacheHeaders,})
        .then(response => response.json())
        .then(data => {
            const minCoords = ol.proj.transform([data.bbox.minx, data.bbox.miny], data.srs, "EPSG:3857");
            const maxCoords = ol.proj.transform([data.bbox.maxx, data.bbox.maxy], data.srs, "EPSG:3857");
            olMap.getView().fit(minCoords.concat(maxCoords), olMap.getSize());
            olMap.getView().fit(minCoords.concat(maxCoords), olMap.getSize());
        });
}

function updateTime(layer, label, val) {
    layer.getSource().updateParams({'TIME': TIMES[val]});
    label.setText(TIMES[val]);
}

function addIndex(index) {
    fetch(window.location.protocol + "//" + window.location.host + "/api/rastercalcs/" + uuid, {
        method: "POST",
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({index: index})
    }).then(function (response) {
        if (response.status === 200) {
            window.location.reload(true); // Reload page if index created successfully
        } else throw response.text();
    }).catch((msg) => alert(msg));
}
