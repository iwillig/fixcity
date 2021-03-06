var map, layer;
var options = {
  projection: new OpenLayers.Projection("EPSG:900913"),
  // EPSG 900913 = Spheroid Mercator (used by Google)
  displayProjection: new OpenLayers.Projection("EPSG:4326"),
  // EPSG 4326 = lat,lon
  units: "m",
  numZoomLevels: 20,
  maxResolution: 156543.03390625,
  maxExtent: new OpenLayers.Bounds(-20037508.34, -20037508.34, 20037508.34, 20037508.34)
};

format = "image/png";

function loadMap(draggable) {
  var draggable = (draggable == null) ? true : draggable;
  map = new OpenLayers.Map('request-map', options);
  var osm = new OpenLayers.Layer.WMS("OpenStreetMap", "http://maps.opengeo.org/geowebcache/service/wms", {
    layers: "openstreetmap",
    format: "image/png",
    bgcolor: '#A1BDC4'
  },
  {
    wrapDateLine: true
  });

  var address_options = {
    projection: 'EPSG:4326',
    styleMap: new OpenLayers.StyleMap({
      "default": {
        pointRadius: pointRadius,
        externalGraphic: externalGraphic
      }
    })
  };

  var address_point = new OpenLayers.Layer.Vector("Location Marker", address_options);
  var geometry = new OpenLayers.Geometry.fromWKT(WKT);
  $("#location").val(WKT);

  geometry.transform(map.displayProjection, map.projection);
  var location = new OpenLayers.Feature.Vector(geometry);
  address_point.addFeatures([location]);
  map.addLayer(address_point);

  var dropHandler = function (address_point, pixel) {
    var xy = address_point.geometry.getBounds().getCenterLonLat();
    xy.transform(map.projection, map.displayProjection);
    getAddress(xy);
    var location_wkt = "POINT(" + xy.lon + " " + xy.lat + ")";
    $("#location").val(location_wkt);
    xy.transform(map.displayProjection, map.projection);
    map.setCenter(xy);
    if (map.getZoom() < 15) {
        map.zoomIn();
    }
  };
  var point_control = new OpenLayers.Control.DragFeature(
  address_point, {
    onComplete: dropHandler
  });

  if(draggable) {
    map.addControl(point_control);
    point_control.activate();
  }

  function getAddress(lonlat) {
    var lat = lonlat.lat;
    var lon = lonlat.lon;
    // Geocoding is asynchronous, so it might not complete
    // before the form submits. Set flags in the form in case
    // that happens, so the server can do the work after form submits.
    $("#geocoded").val(0);
    $.get("/reverse/", {
      lat: lat,
      lon: lon
    },
    function (data) {
      $("#address").val(data).change();
      $("#geocoded").val(1);
    });
  }
  function getPointsFromAddress(address) {
    $("#geocoded").val(0);
    $.get("/geocode/", {
      geocode_text: address
    },
    function (results) {
      // FIXME: handle multiple (or zero) results.
      var lon = results[0][1][1];
      var lat = results[0][1][0];
      var xy = new OpenLayers.LonLat(lon, lat);
      var location_wkt = "POINT(" + lon.toString() + " " + lat.toString() + ")";
      $("#location").val(location_wkt);
      $("#geocoded").val(1);
      address_point.destroyFeatures();
      var geometry = new OpenLayers.Geometry.fromWKT(location_wkt);
      geometry.transform(map.displayProjection, map.projection);
      var location = new OpenLayers.Feature.Vector(geometry);
      address_point.addFeatures([location]);
      address_point.refresh();
      xy.transform(map.displayProjection, map.projection);
      map.setCenter(xy, 16);
    },
    'json');
  }

  // For users with JS, we only want to be forced to check on the back end if there's an unprocessed change
  $("#geocoded").val(1);

  $("#address").bind("blur", function(event) {
    getPointsFromAddress($("#address").val());
  });

  $("#address").bind("focus change", function(event) {
    // Be paranoid and assume we're going to reverse-geocode...
    // For some reason, doing this on focus doesn't seem
    // to be enough.
    $("#geocoded").val(0);
  });

  var navControl = map.getControlsByClass('OpenLayers.Control.Navigation')[0];
  if (navControl) {
    navControl.disableZoomWheel();
  }

  map.addLayers([osm]);
  post_loadmap(map, geometry);
}
