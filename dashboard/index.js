const express = require("express");
const session = require("express-session");
const fetch = require("node-fetch");
const fs = require("fs");

const app = express();
app.use(express.json());
app.use(express.static("public"));

app.use(session({
    secret: "secret",
    resave: false,
    saveUninitialized: false
}));

const CLIENT_ID = "YOUR_CLIENT_ID";
const CLIENT_SECRET = "YOUR_SECRET";
const REDIRECT = "https://YOUR-APP.up.railway.app/callback";

function read(file) {
    try { return JSON.parse(fs.readFileSync("/data/" + file)); }
    catch { return {}; }
}

function write(file, data) {
    fs.writeFileSync("/data/" + file, JSON.stringify(data, null, 2));
}

app.get("/login", (req, res) => {
    res.redirect(`https://discord.com/api/oauth2/authorize?client_id=${CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT)}&response_type=code&scope=identify%20guilds`);
});

app.get("/callback", async (req, res) => {
    const code = req.query.code;

    const params = new URLSearchParams();
    params.append("client_id", CLIENT_ID);
    params.append("client_secret", CLIENT_SECRET);
    params.append("grant_type", "authorization_code");
    params.append("code", code);
    params.append("redirect_uri", REDIRECT);

    const token = await fetch("https://discord.com/api/oauth2/token", {
        method: "POST",
        body: params,
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
    }).then(r => r.json());

    const guilds = await fetch("https://discord.com/api/users/@me/guilds", {
        headers: { Authorization: `Bearer ${token.access_token}` }
    }).then(r => r.json());

    req.session.guilds = guilds;
    res.redirect("/");
});

app.get("/api/guilds", (req, res) => {
    if (!req.session.guilds) return res.json([]);
    res.json(req.session.guilds);
});

app.post("/api/config/:guild", (req, res) => {
    const cfg = read("config.json");
    cfg[req.params.guild] = req.body.roles;
    write("config.json", cfg);
    res.json({ ok: true });
});

app.listen(3000);
