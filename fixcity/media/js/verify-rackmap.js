var map, layer, select, select_vector, racks, bounds, selectControl;

if (jQuery.browser.msie) {
    jQuery(window).load(function () {
        loadMap();
    });
} else {
    jQuery(document).ready(function () {
        loadMap();
    });
}

var options = {
    projection: new OpenLayers.Projection("EPSG:900913"),
    displayProjection: new OpenLayers.Projection("EPSG:4326"),
    units: "m",
    numZoomLevels: 19,
    maxResolution: 156543.03390625,
    maxExtent: new OpenLayers.Bounds(-20037508.34, -20037508.34, 20037508.34, 20037508.34)
};

function loadMap() {
    map = new OpenLayers.Map('verify-map', options);

    var osm = new OpenLayers.Layer.WMS("OpenStreetMap", "http://maps.opengeo.org/geowebcache/service/wms", {
        layers: "openstreetmap",
        format: "image/png",
        bgcolor: '#A1BDC4'
    },
    {
        wrapDateLine: true
    });

    var style = new OpenLayers.Style({
        pointRadius: "12",
        externalGraphic: "/site_media/img/rack.png"

    });

    var li_template = $("#racklist li:first").clone();

    function isSelected(layer, feature) {
      for (var index=0; index<layer.selectedFeatures.length; ++index) {
        if (feature === layer.selectedFeatures[index]) {
	  return true;
	}
      }
      return false;
    }
    function updateRackList(evt) {

        layer = evt.object;
        $("#racklist").empty();
        if (layer.features.length == 0) {
            var this_li = li_template.clone();
            this_li.find("h3").text("No racks in this area.");
            this_li.show();
            $("#racklist").append(this_li);
        }
        for (var i = 0; i < layer.features.length; ++i) {
            var this_li = li_template.clone();
            this_li.show();
            var attrs = layer.features[i].attributes;
            this_li.attr("id", "rack_" + attrs.id);
            this_li.find("h4").text(attrs.address);
            this_li.find("h3 a").text(attrs.name);
            this_li.find("p").text(attrs.Snippet);
            this_li.find("a.rack-thumbnail").attr("href", "/rack/" + attrs.id + "/");
            this_li.find("h3 a").attr("href", "/rack/" + attrs.id + "/");
	    if (isSelected(layer, layer.features[i])) {
	      this_li.addClass('selected');
	    }

			// Once we support multiple statuses this will need to be updated
			this_li.addClass("new");
			
            if ( attrs.verified == null ) {
	          // XXX this always executes, even when the conditional is false!!
	          // why???
	      	  this_li.find("span.rack-verified").hide();
	    	};
			
            if (attrs.thumbnail != null) {
                this_li.find("a.rack-thumbnail img").attr("src", attrs.thumbnail.value);
            } else {
                this_li.find("a.rack-thumbnail img").attr("src", "/site_media/img/default-rack.jpg");
			};
        $("#racklist").append(this_li);

        };
        updatePagination(layer.features);
    };
    var load_rack_params = {
        'page_size': 10,
        // Make this user-controllable.
        'page_number': 1
    };

    function makeClickHandler(n) {
        // curry a function that loads the right page.
        return function (evt) {
            evt.preventDefault();
            load_rack_params.page_number = n;
            racks.events.triggerEvent("moveend");
        };
    };

    function updatePagination(features) {
        if (features.length == 0) {
            $("#pagination").hide();
            return;
        };
        var info = features[0].attributes;

        // Update params for the next data load by the layers' strategy.
        load_rack_params.page_number = parseInt(info.page_number.value);
        var num_pages = parseInt(info.num_pages.value);
        if (num_pages == 1) {
            $("#pagination").hide();
        } else if (num_pages > 1) {
            // Update links in the UI.
            $("#pagination").show();
            if (info.page_previous == null) {
                $("#pagination a[rel=prev]").hide();
            } else {
                $("#pagination a[rel=prev]").show();
                $("#pagination a[rel=prev]").click(makeClickHandler(info.page_previous.value));
            };

            if (info.page_next == null) {
                $("#pagination a[rel=next]").hide();
            } else {
                $("#pagination a[rel=next]").show();
                $("#pagination a[rel=next]").click(makeClickHandler(info.page_next.value));
            };

            // Simple pagination - just list all the pages.
            var link_template = $("#pagination span[class=sectionlink]:first").clone();
            $("#pagination span[class=sectionlink]").remove();
            for (var i = 1; i <= num_pages; i++) {
                var link = link_template.clone();
                var a = link.find("a");
                a.click(makeClickHandler(i));
                if (i == load_rack_params.page_number) {
                    a.removeAttr("href");
                } else {
                    a.attr("href", "#page_number=" + i.toString());
                };
                a.text(i.toString());
                link.insertBefore("#pagination a[rel=next]");
            };
        };
    };

    function replaceFeatures(layer, newfeatures) {
      // Remove old features
      for (var index=0; index<layer.features.length; ++index) {
          var oldf = layer.features[index];
          var found = false;
          for (var search=0; search<newfeatures.length; ++search) {
              var newf = newfeatures[search];
              if (newf.attributes.id == oldf.attributes.id) {
                // We found it... If the description changed, we'll remove it anyway.
                if (newf.attributes.description != oldf.attributes.description) {
                  break;
                }
                found = true;
                break;
              }
          }
          if (!found) {
            layer.removeFeatures(oldf);
          }
      }
      // Add new features
      for (var index=0; index<newfeatures.length; ++index) {
          var newf = newfeatures[index];
          var found = false;
          for (var search=0; search<layer.features.length; ++search) {
              var oldf = layer.features[search];
              if (newf.attributes.id == oldf.attributes.id) {
                // We've handled this already, skip it.
                found = true;
                break;
              }
          }
          if (!found) {
            layer.addFeatures(newf);
          }
      }
    }

    function loadRacks() {
        // We want the bbox to load only stuff that's actually
        // visible on the map. This is less efficient than the
        // default of pre-loading nearby stuff we're likely to pan to;
        // but we show the list of racks in HTML too, so we need the
        // real list of visible stuff.
        // But it's rumored that setting ratio to 1 triggers bugs.
        var bbox = new OpenLayers.Strategy.BBOX({
            ratio: 1.01
        });
        bbox.invalidBounds = function () {
            // Force loading ALL the time.
            return true;
        };
	var oldMerge = bbox.merge;
	bbox.merge = function(resp) {
	  var remote = this.layer.projection;
	  var local = this.layer.map.getProjectionObject();
          if(!local.equals(remote)) {
              var geom;
              for(var i=0, len=resp.features.length; i<len; ++i) {
                  geom = resp.features[i].geometry;
                  if(geom) {
                      geom.transform(remote, local);
                  }
              }
          }
	  
	
	  replaceFeatures(this.layer, resp.features);
	  this.layer.events.triggerEvent("loadend");
	}
        racks = new OpenLayers.Layer.Vector("Racks", {
            projection: map.displayProjection,
            strategies: [
            bbox],
            protocol: new OpenLayers.Protocol.HTTP({
                url: "./rack/requested.kml",
                params: load_rack_params,
                format: new OpenLayers.Format.KML()
            }),
            styleMap: new OpenLayers.StyleMap({
                "default": style,
                "select": {
                    fillColor: "#ff9e73",
                    strokeColor: "#80503b"
                }
            })
        });
        // Big dirty hack!!!
        var FixcityPopup = OpenLayers.Class(OpenLayers.Popup.FramedCloud, {
  	  fixedRelativePosition: true,
          relativePosition: "tl", 
  	  initialize: function(id, lonlat, contentSize, contentHTML, anchor, closeBox, closeBoxCallback) {
            OpenLayers.Popup.Framed.prototype.initialize.apply(this, arguments);
          }
        });
        var featureSelected = function(feature) {
	  $('ul#racklist li').removeClass('selected').filter('#rack_' + feature.attributes.id).addClass('selected');
          var popup = new FixcityPopup(null, feature.geometry.getBounds().getCenterLonLat(),
                                       null, '<strong>' + feature.attributes.name + '</strong><br />' + ((feature.attributes.description.length < 80 ) ? feature.attributes.description : feature.attributes.description.substr(0,80) + '…'),
                                       {size: new OpenLayers.Size(1, 1), offset: new OpenLayers.Pixel(-40, 48)},
                                       true, function() { selectControl.unselect(feature); });
          feature.popup = popup;
          map.addPopup(popup);
        };
        var featureUnselected = function(feature) {
          map.removePopup(feature.popup);
          feature.popup.destroy();
          feature.popup = null;
        };
        var selectControl = new OpenLayers.Control.SelectFeature(racks, {
          onSelect: featureSelected, onUnselect: featureUnselected
        });
        map.addControl(selectControl);
        selectControl.activate();
        return racks;
    };

    var bounds = new OpenLayers.Bounds(-8234063.45026893, 4968638.33081464, -8230209.19302436, 4973585.50729644);
    racks = loadRacks();
    map.addLayers([osm, racks]);

    // Every time we load new features (via the BBOX strategy
    // above), we want to update the html list of racks.
    racks.events.on({
        "loadend": updateRackList
    });
    map.zoomToExtent(bounds);

}
