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
    const map = L.map("map").setView([52.2, 5.1], 9);

    Tangram.leafletLayer({
      scene: 'scene.yaml'
    }).addTo(map);

    L.marker([52.2, 5.1]).addTo(map);
    L.marker([52.4, 5.1]).addTo(map);
    L.marker([52.4, 5.3]).addTo(map);
    L.marker([52.2, 5.3]).addTo(map);

    map.attributionControl.setPrefix("");
  }

  initializeMap();
}())
