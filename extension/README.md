# Assistant Injector extension (for sites you don't control)

Use this when you cannot add the `<script>` snippet to a product's HTML (e.g. a third-party demo such as
OrangeHRM). It removes the site's Content-Security-Policy for the configured hosts and injects `widget.js`.

1. Register the product in the dashboard (e.g. `prod_orangehrm`, URL `https://opensource-demo.orangehrmlive.com`,
   with login credentials if the product requires login) and wait for READY.
2. Edit `config.js`: backend URL and `host -> product id`.
3. Chrome → `chrome://extensions` → enable *Developer mode* → *Load unpacked* → select this `extension/` folder.
4. Open the site. The assistant appears bottom-right on every page load; SPA navigation keeps the chat alive.

Only for development/demos: stripping CSP weakens the site's protections in your own browser.
