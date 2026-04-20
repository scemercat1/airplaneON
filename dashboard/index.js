const express = require("express");
const session = require("express-session");
const fs = require("fs");
const path = require("path");

const app = express();

const PORT = process.env.PORT;

app.use(express.json());
app.use(express.static("public"));

app.use(session({
    secret: "aircraft",
    resave: false,
    saveUninitialized: false
}));

const DATA_PATH = "/data";

function read(file) {
    try {
        return JSON.parse(fs.readFileSync(path.join(DATA_PATH, file), "utf8"));
    } catch {
        return {};
    }
}

function write(file, data) {
    try {
        fs.writeFileSync(path.join(DATA_PATH, file), JSON.stringify(data, null, 2));
    } catch (e) {
        console.log("Write error:", e);
    }
}

app.get("/", (req, res) => {
    res.send("Dashboard running");
});

app.get("/health", (req, res) => {
    res.send("OK");
});

app.listen(PORT, "0.0.0.0", () => {
    console.log("Running on", PORT);
});
