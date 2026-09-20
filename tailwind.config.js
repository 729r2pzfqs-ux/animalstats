/** Compiled at build time into static/css/site.css and inlined into every page (no runtime CDN). */
module.exports = {
  content: ["./templates/**/*.html", "./static/js/*.js", "./build.py"],
  safelist: ["iucn-EX","iucn-EW","iucn-CR","iucn-EN","iucn-VU","iucn-NT","iucn-LC","iucn-DD","iucn-NE","iucn-DOM"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
      },
    },
  },
  plugins: [],
};
