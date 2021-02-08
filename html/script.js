(function () {
  // Cognito Identity Pool ID
  const identityPoolId = "eu-west-1:d052d9d8-8b6d-4154-aef4-968d084f2fc0";

  AWS.config.region = identityPoolId.split(":")[0];

  // instantiate a credential provider
  credentials = new AWS.CognitoIdentityCredentials({
    IdentityPoolId: identityPoolId,
  });

  /**
   * Register a service worker that will rewrite and sign requests using Signature Version 4.
   */
  async function registerServiceWorker() {
    if ("serviceWorker" in navigator) {
      try {
        const reg = await navigator.serviceWorker.register("./sw.js");

        // refresh credentials from Amazon Cognito
        await credentials.refreshPromise();

        await reg.active.ready;

        if (navigator.serviceWorker.controller == null) {
          // trigger a navigate event to active the controller for this page
          window.location.reload();
        }

        // pass credentials to the service worker
        reg.active.postMessage({
          credentials: {
            accessKeyId: credentials.accessKeyId,
            secretAccessKey: credentials.secretAccessKey,
            sessionToken: credentials.sessionToken,
          },
          region: AWS.config.region,
        });
      } catch (error) {
        console.error("Service worker registration failed:", error);
      }
    } else {
      console.warn("Service Worker support is required for this example");
    }
  }

  /**
   * Initialize a map.
   */
  async function initializeMap() {
    // register the service worker to handle requests to https://amazon.location
    await registerServiceWorker();

    // actually initialize the map
    map = L.map("map").setView([52.2, 5.1], 9);

    Tangram.leafletLayer({
      scene: "scene.yaml"
    }).addTo(map);
    map.attributionControl.setPrefix("");

    loadMarkers()
    setInterval(loadMarkers, 1000)
  }

  function loadMarkers() {
    $.ajax({
      dataType: "json",
      url: "https://d2590et6sh3gqo.cloudfront.net/aircraft/",
      success: function(aircrafts) {
        const currentAircrafts = []

        aircrafts.forEach(function(aircraft) {
          icaoAddress = aircraft["IcaoAddress"]
          latLng = [
            aircraft["Latitude"],
            aircraft["Longitude"]
          ]

          // Substract 45 as the Twemoji as a default heading o 45 degree
          angle = parseInt(aircraft["Heading"])  - 45

          currentAircrafts.push(icaoAddress)

          // Either create a new marker or update the existing one
          if (!(icaoAddress in markers)) {
            markers[icaoAddress] = L.marker(latLng, {icon: icon, rotationAngle: angle}).addTo(map);

            // Add FlightCode later
            markers[icaoAddress].bindPopup(icaoAddress)
          } else {
            markers[icaoAddress].setLatLng(latLng);
            markers[icaoAddress].setRotationAngle(angle);
          }
        });

        // Remove any markers with address that are not in the current response
        for (icaoAddress in markers) {
          if (!currentAircrafts.includes(icaoAddress)) {
            map.removeLayer(markers[icaoAddress])
            delete markers[icaoAddress]
          }
        }
      }
    });
  }

  const icon = L.icon({
      iconUrl: 'twemoji/2708.svg',
      iconSize: [40, 40],
      iconAnchor: [20, 20],
      popupAnchor: [0, -20]
  });

  let map;
  const markers = {};
  initializeMap();
}())
