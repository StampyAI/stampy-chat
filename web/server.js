const { createServer: createHttpsServer } = require("https");
const { createServer: createHttpServer } = require("http");
const { parse } = require("url");
const next = require("next");
const fs = require("fs");

const dev = process.env.NODE_ENV !== "production";
const port = parseInt(process.env.PORT) || 3000;
const sslCert = process.env.SSL_CRT_FILE;
const sslKey = process.env.SSL_KEY_FILE;
const host = process.env.HOST || "127.0.0.1";

const app = next({ dev });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  const requestHandler = (req, res) => {
    const parsedUrl = parse(req.url, true);
    handle(req, res, parsedUrl);
  };

  // Use HTTPS if cert files are provided, otherwise HTTP
  if (sslCert && sslKey) {
    const httpsOptions = {
      cert: fs.readFileSync(sslCert),
      key: fs.readFileSync(sslKey),
    };
    createHttpsServer(httpsOptions, requestHandler).listen(port, host, (err) => {
      if (err) throw err;
      console.log(`> Server started on https://${host}:${port}`);
    });
  } else {
    createHttpServer(requestHandler).listen(port, host, (err) => {
      if (err) throw err;
      console.log(`> Server started on http://${host}:${port}`);
    });
  }
});
