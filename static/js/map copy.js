document.addEventListener("DOMContentLoaded", function () {
  const mapElement = document.getElementById("pothole-map");
  if (!mapElement) return;

  const latitudeElement = document.getElementById("latitude");
  const longitudeElement = document.getElementById("longitude");
  const messageElement = document.getElementById("location-message");
  const statusElement = document.querySelector(".location-status");
  const confirmButton = document.getElementById("confirm-location");

  const reportLatitude = document.getElementById("report-latitude");
  const reportLongitude = document.getElementById("report-longitude");
  const submitButton = document.getElementById("submit-report");
  const reportForm = document.getElementById("pothole-report-form");

  if (
    !latitudeElement ||
    !longitudeElement ||
    !messageElement ||
    !confirmButton ||
    !reportLatitude ||
    !reportLongitude ||
    !submitButton ||
    !reportForm
  ) {
    console.error("Map or report form elements are missing.");
    return;
  }

  submitButton.disabled = true;

    // Initialize map
    const map = L.map("pothole-map", {
        minZoom: 12,
        maxZoom: 19,
        maxBounds: [
        [13.45, 144.76],
        [13.59, 144.92],
        ],
        maxBoundsViscosity: 1.0,
    }).setView([13.5178, 144.8391], 14);

    // Street and place search using OpenStreetMap Nominatim
    const searchForm = document.getElementById("street-search-form");
    const searchInput = document.getElementById("street-search-input");
    const searchButton = document.getElementById("street-search-button");
    const searchMessage = document.getElementById("street-search-message");

    if (searchForm && searchInput && searchButton && searchMessage) {
    searchForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const query = searchInput.value.trim();

        if (!query) {
        searchMessage.textContent = "Please enter a street or place.";
        return;
        }

        searchButton.disabled = true;
        searchMessage.textContent = "Searching for streets and places...";

        try {
        const params = new URLSearchParams({
            q: `${query}, Dededo, Guam`,
            format: "jsonv2",
            limit: "10",
            addressdetails: "1",
            bounded: "1",
            viewbox: "144.76,13.59,144.92,13.45"
        });

        const response = await fetch(
            `https://nominatim.openstreetmap.org/search?${params.toString()}`,
            {
            headers: {
                Accept: "application/json"
            }
            }
        );

        if (!response.ok) {
            throw new Error("Location search is unavailable.");
        }

        const results = await response.json();

        const result = results.find(function (item) {
            const lat = Number(item.lat);
            const lng = Number(item.lon);

            return (
            Number.isFinite(lat) &&
            Number.isFinite(lng) &&
            lat >= 13.45 &&
            lat <= 13.59 &&
            lng >= 144.76 &&
            lng <= 144.92
            );
        });

        if (!result) {
            searchMessage.textContent =
            "No matching place found in the Dededo search area. Try another name.";
            return;
        }

        const latitude = Number(result.lat);
        const longitude = Number(result.lon);

      // Move the map without changing the selected pothole pin.
      map.setView([latitude, longitude], 17, {
        animate: true
      });

      searchMessage.textContent = "Map moved to: " + result.display_name;

    } catch (error) {
      console.error("Map search error:", error);

      searchMessage.textContent =
        "Unable to search right now. Please try again.";

    } finally {
      searchButton.disabled = false;
    }
  });
}


  // Street layer
  const streetLayer = L.tileLayer(
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">' +
        "OpenStreetMap</a> contributors",
    },
  );

  // Satellite layer
  const satelliteLayer = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 19,
      attribution: "Tiles &copy; Esri and its imagery providers",
    },
  );

  streetLayer.addTo(map);
  let boundaryGeoJSON = null;

  // Street search using OpenStreetMap Nominatim
  if (window.setupPlaceAutocomplete) {
    window.setupPlaceAutocomplete({
        map: map,
        formId: "street-search-form",
        inputId: "street-search-input",
        buttonId: "street-search-button",
        messageId: "street-search-message",
        suggestionsId: "street-search-suggestions",

        // Keep suggestions inside the actual Dededo boundary
        // whenever its GeoJSON has loaded.
        isAllowed: function (latitude, longitude) {
            return boundaryGeoJSON
                ? isInsideDededo(latitude, longitude)
                : (
                    latitude >= 13.45 &&
                    latitude <= 13.59 &&
                    longitude >= 144.76 &&
                    longitude <= 144.92
                );
        }
    });
}

  // Dededo boundary
  const boundaryUrl =
    "https://services2.arcgis.com/FPJlJZYRsD8OhCWA/" +
    "ArcGIS/rest/services/GUM_Boundaries_2020/" +
    "FeatureServer/1/query" +
    "?where=NAME%3D%27Dededo%27" +
    "&outFields=NAME&returnGeometry=true&outSR=4326&f=geojson";

  
  let marker = null;
  let selectedLocation = null;

  fetch(boundaryUrl)
    .then((response) => {
      if (!response.ok) throw new Error("Could not load boundary.");
      return response.json();
    })
    .then((geojson) => {
      if (!geojson.features || !geojson.features.length) {
        throw new Error("No Dededo boundary was returned.");
      }

      boundaryGeoJSON = geojson;

      const boundaryLayer = L.geoJSON(geojson, {
        style: {
          color: "#5145cd",
          weight: 3,
          fillColor: "#8175ef",
          fillOpacity: 0.08,
        },
      }).addTo(map);

      map.fitBounds(boundaryLayer.getBounds(), {
        padding: [20, 20],
      });

      map.setMaxBounds(boundaryLayer.getBounds().pad(0.1));
      map.setMaxZoom(19);
    })
    .catch((error) => {
      console.error("Dededo boundary loading error:", error);
      messageElement.textContent =
        "Could not load the Dededo boundary. Please refresh the page.";
    });

  // Check whether a point is inside a GeoJSON ring.
  function pointInRing(lat, lng, ring) {
    let inside = false;

    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const xi = ring[i][0];
      const yi = ring[i][1];
      const xj = ring[j][0];
      const yj = ring[j][1];

      const crosses =
        yi > lat !== yj > lat &&
        lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi;

      if (crosses) inside = !inside;
    }

    return inside;
  }

  function pointInGeometry(lat, lng, geometry) {
    if (!geometry) return false;

    const polygons =
      geometry.type === "Polygon"
        ? [geometry.coordinates]
        : geometry.type === "MultiPolygon"
          ? geometry.coordinates
          : [];

    return polygons.some((polygon) => {
      if (!polygon.length || !pointInRing(lat, lng, polygon[0])) {
        return false;
      }

      // Exclude any holes in the polygon.
      for (let i = 1; i < polygon.length; i++) {
        if (pointInRing(lat, lng, polygon[i])) return false;
      }

      return true;
    });
  }

  function isInsideDededo(lat, lng) {
    return Boolean(
      boundaryGeoJSON &&
      boundaryGeoJSON.features.some((feature) =>
        pointInGeometry(lat, lng, feature.geometry),
      ),
    );
  }

  function clearConfirmation() {
    reportLatitude.value = "";
    reportLongitude.value = "";
    submitButton.disabled = true;
    confirmButton.textContent = "Confirm Location";
  }

  function updateLocation(latlng) {
    selectedLocation = {
      latitude: latlng.lat,
      longitude: latlng.lng,
    };

    latitudeElement.textContent = latlng.lat.toFixed(6);
    longitudeElement.textContent = latlng.lng.toFixed(6);

    messageElement.textContent = "Location selected. Confirm it to continue.";

    if (statusElement) statusElement.classList.add("selected");

    clearConfirmation();
    confirmButton.disabled = false;
  }

  // Place or reposition the pin.
  map.on("click", function (event) {
    if (!boundaryGeoJSON) {
      messageElement.textContent =
        "Please wait for the Dededo boundary to load.";
      return;
    }

    const point = event.latlng;

    if (!isInsideDededo(point.lat, point.lng)) {
      messageElement.textContent = "Please select a location inside Dededo.";
      return;
    }

    if (!marker) {
      marker = L.marker(point, { draggable: true }).addTo(map);
      marker.bindPopup("Pothole location");

      marker.on("dragstart", function () {
        marker.previousValidPosition = marker.getLatLng();
      });

      marker.on("dragend", function () {
        const position = marker.getLatLng();

        if (!isInsideDededo(position.lat, position.lng)) {
          marker.setLatLng(marker.previousValidPosition || selectedLocation);

          messageElement.textContent =
            "That location is outside Dededo. The pin was moved back.";
          return;
        }

        updateLocation(position);
      });
    } else {
      marker.setLatLng(point);
    }

    selectedLocation = {
      latitude: point.lat,
      longitude: point.lng,
    };

    updateLocation(point);
  });

  // Confirm and copy coordinates to the form.
  confirmButton.addEventListener("click", function () {
    if (
      !selectedLocation ||
      !isInsideDededo(selectedLocation.latitude, selectedLocation.longitude)
    ) {
      messageElement.textContent =
        "Please select a valid location inside Dededo.";
      return;
    }

    reportLatitude.value = selectedLocation.latitude;
    reportLongitude.value = selectedLocation.longitude;

    submitButton.disabled = false;
    confirmButton.textContent = "Location Confirmed";

    messageElement.textContent =
      "Location confirmed! You can now submit your report.";

    if (marker) marker.openPopup();

    console.log("Confirmed pothole location:", selectedLocation);
  });

  // Require confirmed coordinates before submitting.
  reportForm.addEventListener("submit", function (event) {
    if (
      reportLatitude.value === "" ||
      reportLongitude.value === "" ||
      submitButton.disabled
    ) {
      event.preventDefault();
      messageElement.textContent =
        "Please select and confirm the pothole location first.";
    }
  });

  setTimeout(() => map.invalidateSize(), 100);
});

