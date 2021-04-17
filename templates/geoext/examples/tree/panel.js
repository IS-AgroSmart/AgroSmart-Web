Ext.require([
    'GeoExt.component.Map',
    'GeoExt.data.store.LayersTree'
]);

let mapComponent;
let mapPanel;
let treePanel, timeSlider;

let selectClick;

let TIMES = [];
let shapefiles = [], indices = [];

let noCacheHeaders = new Headers(); // HACK: Force disable cache, otherwise timing problem when going back to screen
noCacheHeaders.append('pragma', 'no-cache');
noCacheHeaders.append('cache-control', 'no-cache');

fetch(`/geoserver/geoserver/${project_path}/mainortho/wms?service=WMS&version=1.3.0&request=GetCapabilities`,
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
                            attributions: ['Powered by Esri.',
                                'Map sources: Esri, DigitalGlobe, GeoEye, Earthstar Geographics, CNES/Airbus DS, USDA, USGS, AeroGRID, IGN, and the GIS User Community.',
                                'Icons from Wikimedia Commons',],
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

            rgbLayer = new ol.layer.Tile({
                name: "Ortomosaico RGB",
                source: new ol.source.TileWMS({
                    url: `/geoserver/geoserver/${project_path}/ows?version=1.3.0`,
                    params: {"LAYERS": project_path + ":mainortho", tiled: true}
                })
            });

            rasterGroup = new ol.layer.Group({
                name: "Imágenes",
                layers: [rgbLayer],
            });

            shapefilesGroup = new ol.layer.Group({
                name: "Vectores & GeoTIFFs",
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
                    maxZoom: 24
                }),
                target: 'map',
            });

            fitMap(); // Must happen after olMap is defined!
            addMeasureInteraction();

            let zoomslider = new ol.control.ZoomSlider();
            olMap.addControl(zoomslider);
            let PointControl = createPointControl();
            olMap.addControl(new PointControl());
            let MeasureLengthControl = createLengthControl();
            olMap.addControl(new MeasureLengthControl());
            let MeasureAreaControl = createAreaControl();
            olMap.addControl(new MeasureAreaControl());
            let SaveMeasurementsControl = createSaveControl();
            olMap.addControl(new SaveMeasurementsControl());
            let ClearMeasurementsControl = createClearControl();
            olMap.addControl(new ClearMeasurementsControl());

            // Add legend, only if there is at least one index
            if (indices.length > 0) {
                let LegendControl = function (opt_options) {
                    var options = opt_options || {};
                    var img = document.createElement('img');
                    var someIndexLayer = indices[0].getSource().getParams()["LAYERS"];
                    img.setAttribute("src", "/geoserver/geoserver/styles/gradient.png");
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
            selectClick = new ol.interaction.Select({
                condition: ol.events.condition.click,
                layers: (layer) => layer instanceof ol.layer.Vector,
                hitTolerance: 10,
            });
            selectClick.on('select', function (e) {
                if (delete_handler)
                    document.removeEventListener("keydown", delete_handler);

                if (e.selected.length === 0) {
                    popup.hide();
                    delete_handler = null;
                    return;
                }
                delete_handler = function (evt) {
                    var charCode = (evt.which) ? evt.which : evt.keyCode;
                    if (charCode === 46) { // Del key
                        let feature = e.selected[0];
                        if (interactionSource.getFeatures().includes(feature)) {
                            interactionSource.removeFeature(feature);
                            let id = feature.getId();
                            olMap.removeOverlay(measureTooltips[id]);
                            popup.hide();
                            delete measureTooltips[id];
                            selectClick.getFeatures().remove(feature);
                        }
                    }
                };
                document.addEventListener('keydown', delete_handler, false);
                let coordinate = e.mapBrowserEvent.coordinate;

                let message = "<p>";
                for (const [key, value] of Object.entries(e.selected[0].getProperties())) {
                    if (["bbox", "geometry"].includes(key)) continue;
                    message += key + " ⟶ " + value + "<br>";
                }
                message += "</p>";
                popup.setHtml(message);
                popup.position(coordinate);
                if (message !== "<p></p>") popup.show();
                else popup.hide();
            });
            olMap.addInteraction(selectClick);


            mapComponent = Ext.create('GeoExt.component.Map', {
                map: olMap
            });

            timeSlider = Ext.create('Ext.slider.Single', {
                width: 214,
                value: TIMES.length - 1,
                increment: 1,
                minValue: 0,
                maxValue: TIMES.length - 1,
                useTips: true,
                tipText: function (thumb) {
                    return TIMES[thumb.value];
                },
                componentCls: "slider-style",
            });

            const svgUrl = "data:image/svg+xml," + encodeURIComponent(composeSvgTicks(TIMES.length));
            console.log(svgUrl);
            setStyle('.slider-style { background-image:url(/mapper/ticks/' + TIMES.length + '); }');

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

            let treeLayers = olMap.getLayers().getArray().filter(layer => layer != interactionLayer);
            let treeLayerGroup = new ol.layer.Group();
            treeLayerGroup.setLayers(new ol.Collection(treeLayers));
            treeStore = Ext.create('GeoExt.data.store.LayersTree', {
                layerGroup: treeLayerGroup
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
                height: 300,
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
                                url: `/geoserver/geoserver/${project_path}/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=${art.layer}&outputFormat=application/json`
                            })
                        }));
                    else if (art.type === "ORTHOMOSAIC")
                        shapefiles.push(new ol.layer.Tile({
                            name: art.name,
                            source: new ol.source.TileWMS({
                                url: `/geoserver/geoserver/${project_path}/ows?version=1.3.0`,
                                params: {"LAYERS": art.layer, tiled: true}
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
                            url: `/geoserver/geoserver/${project_path}/ows?version=1.3.0`,
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

function _createControl(handler, buttonContent, buttonClass, buttonTooltip) {
    let controlClass = function (opt_options) {
        var options = opt_options || {};
        var button = document.createElement('button');
        button.innerHTML = buttonContent;
        button.setAttribute("type", "button");
        button.setAttribute("title", buttonTooltip);

        button.addEventListener('click', handler, false);
        button.addEventListener('touchstart', handler, false);

        var element = document.createElement('div');
        element.className = buttonClass + ' ol-unselectable ol-control';
        element.appendChild(button);

        ol.control.Control.call(this, {
            element: element,
            target: options.target
        });

    };
    ol.inherits(controlClass, ol.control.Control);
    return controlClass;
}

function createNorthControl() {
    return _createControl(() => olMap.getView().setRotation(olMap.getView().getRotation() == 0 ? 45 : 0),
        "N", "rotate-north", "Rotar mapa");
}

function createPointControl() {
    return _createControl(measurePointListener,
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50" width="90%" height="90%" version="1.1">' +
        '<circle cx="25" cy="25" r="10" stroke="#fff" stroke-width="6" fill="#00000000"></circle>' +
        '</svg>',
        "measure-point", "Anotar punto");
}

function createLengthControl() {
    return _createControl(measureLengthListener,
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 40" width="90%" height="90%">' +
        '  <path stroke="#fff" stroke-width="4" stroke-linejoin="round" stroke-linecap="round" fill="none" d="M5,20H45M12,12 4,20 12,28M38,12 46,20 38,28"/>' +
        '</svg>',
        "measure-length", "Medir distancias");
}

function createAreaControl() {
    return _createControl(measureAreaListener,
        '<svg xmlns="http://www.w3.org/2000/svg" viewbox="0 60 588 417" height="90%" width="90%">' +
        '  <path stroke="#fff" stroke-width="50" stroke-linejoin="round" stroke-linecap="round" fill="none" d="M 246.55624,445.55603 C 130.80587,418.39845 35.513972,395.59161 34.796512,394.87415 C 33.744472,393.82211 33.735832,393.25321 34.751832,391.93421 C 35.444712,391.03469 67.302832,366.53016 105.54765,337.4797 C 143.79247,308.42924 175.07668,284.21068 175.06812,283.66068 C 175.05955,283.11068 137.72969,267.03903 92.112862,247.9459 C 46.496032,228.85277 8.8093816,212.65277 8.3647316,211.9459 C 7.4317416,210.46268 204.30692,12.877091 206.05498,13.542291 C 208.09055,14.316891 577.03254,282.35001 578.28364,283.96311 C 578.98324,284.86521 579.30634,286.25314 579.00154,287.04739 C 577.51514,290.9209 462.03434,492.82834 460.68624,493.91068 C 459.82994,494.59818 458.65284,495.10955 458.07044,495.04706 C 457.48804,494.98458 362.30664,472.71361 246.55624,445.55603 z "/>' +
        '</svg>',
        "measure-area", "Medir áreas"
    );
}

function createSaveControl() {
    return _createControl(saveMeasurementsListener,
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -256 1792 1792" width="90%" height="90%">' +
        '<g transform="matrix(1,0,0,-1,129.08475,1270.2373)">' +
        '  <path fill="#fff" d="m 384,0 h 768 V 384 H 384 V 0 z m 896,0 h 128 v 896 q 0,14 -10,38.5 -10,24.5 -20,34.5 l -281,281 q -10,10 -34,20 -24,10 -39,10 V 864 q 0,-40 -28,-68 -28,-28 -68,-28 H 352 q -40,0 -68,28 -28,28 -28,68 v 416 H 128 V 0 h 128 v 416 q 0,40 28,68 28,28 68,28 h 832 q 40,0 68,-28 28,-28 28,-68 V 0 z M 896,928 v 320 q 0,13 -9.5,22.5 -9.5,9.5 -22.5,9.5 H 672 q -13,0 -22.5,-9.5 Q 640,1261 640,1248 V 928 q 0,-13 9.5,-22.5 Q 659,896 672,896 h 192 q 13,0 22.5,9.5 9.5,9.5 9.5,22.5 z m 640,-32 V -32 q 0,-40 -28,-68 -28,-28 -68,-28 H 96 q -40,0 -68,28 -28,28 -28,68 v 1344 q 0,40 28,68 28,28 68,28 h 928 q 40,0 88,-20 48,-20 76,-48 l 280,-280 q 28,-28 48,-76 20,-48 20,-88 z"/>' +
        '</g></svg>', "save-meas", "Guardar mediciones");
}

function createClearControl() {
    return _createControl(clearMeasurementsListener,
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">' +
        '<g>' +
        '  <path stroke="#fff" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" fill="none" d="m6 4v24h11v-1h-10v-22h11v7h7v7h1v-8l-7-7h-1z"/>' +
        '  <path stroke="#fff" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" fill="none" d="m18 20.707l3.293 3.293-3.293 3.293c.013.025.707.707.707.707l3.293-3.293 3.293 3.293.707-.707-3.293-3.293 3.293-3.293-.707-.707-3.293 3.293-3.293-3.293z"/>' +
        '</g></svg>',
        "clear-meas", "Eliminar mediciones (use Supr para eliminar una sola medición)")
}

let interactionLayer, interactionSource;
var featureType = 'LineString';
var helpTooltipElement, helpTooltip;
var measureTooltipElement, measureTooltip;
var numMeasurement = 0;
var measureTooltips = {};
var draw, listener, isDrawing = false;
var delete_handler;

function removeInteraction() {
    isDrawing = false;
    olMap.removeInteraction(draw);
    olMap.un('pointermove', pointerMoveHandler);
    deleteHelpTooltip();
}

function measurePointListener() {
    featureType = 'Point';
    if (isDrawing) removeInteraction();
    else addInteraction();
}

function measureLengthListener() {
    featureType = 'LineString';
    if (isDrawing) removeInteraction();
    else addInteraction();
}

function measureAreaListener() {
    featureType = 'Polygon';
    if (isDrawing) removeInteraction();
    else addInteraction();
}

function saveMeasurementsListener() {
    let serializer = new ol.format.GeoJSON();
    let features = interactionLayer.getSource().getFeatures();

    if (features.length === 0) {
        alert("Realice alguna medición antes de guardar");
        return;
    }

    let geojson = serializer.writeFeatures(features, {
        dataProjection: 'EPSG:4326',
        featureProjection: olMap.getView().getProjection()
    });

    let link = document.createElement('a');
    let filename = prompt("Escriba un nombre para el archivo (opcional)", "Mediciones " + project_name);
    if (filename !== null && filename.trim() !== "") link.download = filename + ".geojson";
    else link.download = "measurements.geojson";
    let blob = new Blob([geojson], {type: "application/geo+json;charset=utf-8"});

    link.href = URL.createObjectURL(blob);
    link.click();
    URL.revokeObjectURL(link.href);
}

function clearMeasurementsListener() {
    interactionSource.clear();
    Object.entries(measureTooltips).forEach((tt) => olMap.removeOverlay(tt[1]));
    selectClick.getFeatures().clear();
}

var drawingFeature = null;
var helpMsg;
var pointerMoveHandler = (evt) => {
    if (evt.dragging) return;
    if (drawingFeature) helpMsg = "Doble clic para terminar de dibujar";

    helpTooltipElement.innerHTML = helpMsg
    helpTooltip.setPosition(evt.coordinate)
    helpTooltipElement.classList.remove('hidden');
}

function formatLength(line) {
    let length = ol.Sphere.getLength(line);
    if (length > 100) return (length / 1000).toFixed(2) + ' km';
    else return length.toFixed(2) + ' m';
}

function formatArea(polygon) {
    let area = ol.Sphere.getArea(polygon);
    let hectares = area / 10000;
    if (area > 10000) return (area / 1000000).toFixed(2) + ' km<sup>2</sup> (' + hectares.toFixed(2) + ' ha)';
    else return area.toFixed(2) + ' m<sup>2</sup>'
}

function addInteraction() {
    helpMsg = 'Clic para comenzar a dibujar';
    isDrawing = true;

    olMap.getViewport().addEventListener('mouseout', () => {
        if (helpTooltipElement) helpTooltipElement.classList.add('hidden');
    });
    olMap.on('pointermove', pointerMoveHandler);

    draw = new ol.interaction.Draw({
        source: interactionSource,
        type: featureType,
        style: new ol.style.Style({
            fill: new ol.style.Fill({
                color: 'rgba(125, 125, 125, 0.2)'
            }),
            stroke: new ol.style.Stroke({
                color: 'rgba(0, 0, 0, 0.5)',
                lineDash: [10, 10],
                width: 2
            }),
            image: new ol.style.Circle({
                radius: 5,
                stroke: new ol.style.Stroke({
                    color: 'rgba(0, 0, 0, 0.7)'
                }),
                fill: new ol.style.Fill({
                    color: 'rgba(255, 255, 255, 0.2)'
                })
            })
        })
    })
    olMap.addInteraction(draw)

    try {
        createMeasureTooltip()
        createHelpTooltip()
    } catch (error) {
        console.log('error', error)
    }

    draw.on('drawstart', (evt) => {
        numMeasurement++;
        drawingFeature = evt.feature
        let tooltipCoord = evt.coordinate
        listener = drawingFeature.getGeometry().on('change', (evt) => {
            let geom = evt.target;
            let output;
            if (geom instanceof ol.geom.Polygon) {
                output = formatArea(geom);
                tooltipCoord = geom.getInteriorPoint().getCoordinates();
            } else if (geom instanceof ol.geom.LineString) {
                output = formatLength(geom);
                tooltipCoord = geom.getLastCoordinate();
            }
            measureTooltipElement.innerHTML = output;
            measureTooltip.setPosition(tooltipCoord);
            selectClick.getFeatures().clear();
        })
    }, this)
    draw.on('drawend', (evt) => {
        ans = prompt("Escriba el nombre de la medición (opcional)");
        if (ans !== null && ans.trim() !== "")
            drawingFeature.set("nombre", ans)
        measureTooltipElement.className = 'tooltip tooltip-static';
        measureTooltip.setOffset([0, -7]);
        drawingFeature.setId(numMeasurement);
        measureTooltips[numMeasurement] = measureTooltip;
        drawingFeature = null
        measureTooltipElement = null
        ol.Observable.unByKey(listener);
        removeInteraction();
        selectClick.getFeatures().clear();
    }, this)
}

function deleteHelpTooltip() {
    if (helpTooltipElement) {
        helpTooltipElement.parentNode.removeChild(helpTooltipElement);
        helpTooltipElement = null;
    }
}

function createHelpTooltip() {
    deleteHelpTooltip();
    helpTooltipElement = document.createElement('div')
    helpTooltipElement.className = 'tooltip hidden'
    helpTooltip = new ol.Overlay({
        element: helpTooltipElement,
        offset: [15, 0],
        positioning: 'center-left'
    })
    olMap.addOverlay(helpTooltip)
}

function createMeasureTooltip() {
    if (measureTooltipElement) {
        measureTooltipElement.parentNode.removeChild(measureTooltipElement)
    }
    measureTooltipElement = document.createElement('div')
    measureTooltipElement.className = 'tooltip tooltip-measure'
    measureTooltip = new ol.Overlay({
        element: measureTooltipElement,
        offset: [0, -15],
        positioning: 'bottom-center'
    })
    olMap.addOverlay(measureTooltip)
}

function addMeasureInteraction() {
    interactionSource = new ol.source.Vector();
    interactionLayer = new ol.layer.Vector({
        source: interactionSource,
        style: new ol.style.Style({
            fill: new ol.style.Fill({
                color: 'rgba(255, 255, 255, 0.2)'
            }),
            stroke: new ol.style.Stroke({
                color: '#ffcc33',
                width: 2
            }),
            image: new ol.style.Circle({
                radius: 5,
                fill: new ol.style.Fill({
                    color: '#ffcc33'
                }),
            }),
        }),
    });
    olMap.addLayer(interactionLayer);
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
        } else if (response.status === 402) {
            throw "Su almacenamiento está lleno, no puede crear nuevos índices";
        } else throw response.text();
    }).catch((msg) => alert(msg));
}

function composeSvgTicks(numTicks) {
    function _tick(pos) {
        return `<line x1="${pos}" y1="0" x2="${pos}" y2="10" style="stroke:black;stroke-width:1" />`
    }

    let svg = '<svg height="30px" width="214px">';
    // Interval [1, 213] must be divided in numTicks spaces, ends are included
    // Fence post problem! :)
    const MARGIN = 7;
    const START = MARGIN, END = 214 - MARGIN;
    const interval = ((END - START) / (numTicks - 1)).toFixed(); // Place tick every interval pixels
    for (var i = 0; i < numTicks; i++) {
        svg += _tick(interval * i + START);
    }
    svg += '</svg>';
    return svg;
}

// https://stackoverflow.com/a/19613731
function setStyle(cssText) {
    var sheet = document.createElement('style');
    sheet.type = 'text/css';
    /* Optional */
    window.customSheet = sheet;
    (document.head || document.getElementsByTagName('head')[0]).appendChild(sheet);
    return (setStyle = function (cssText, node) {
        if (!node || node.parentNode !== sheet)
            return sheet.appendChild(document.createTextNode(cssText));
        node.nodeValue = cssText;
        return node;
    })(cssText);
};
