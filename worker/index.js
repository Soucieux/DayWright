export default {
  /**
   * Serve the built interface: each request's asset, or, for a page the assets don't hold, the app's index.html, so
   * a route the interface draws itself opens on a reload or a link.
   * @param {Request} request - The request.
   * @param {{ASSETS: {fetch: (request: Request) => Promise<Response>}}} env - The site's bound assets.
   * @returns {Promise<Response>} The asset; index.html for a missing HTML page asked with GET or HEAD; else the 404.
   */
  async fetch(request, env) {
    const response = await env.ASSETS.fetch(request);
    const acceptsHtml = request.headers.get("accept")?.includes("text/html");

    if (response.status !== 404 || !acceptsHtml || !["GET", "HEAD"].includes(request.method)) {
      return response;
    }

    const indexUrl = new URL(request.url);
    indexUrl.pathname = "/index.html";
    indexUrl.search = "";
    return env.ASSETS.fetch(new Request(indexUrl, request));
  },
};
