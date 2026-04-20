const express = require("express");
const session = require("express-session");
const fetch = require("node-fetch");
const fs = require("fs");
const path = require("path");

const app = express();

const CLIENT_ID = process.env.CLIENT_ID;
const CLIENT_SECRET = process.env.CLIENT_SECRET;
const REDIRECT = process.env.REDIRECT;

const DATA_PATH = "/data";

app.use(express.json());
app.use(express.static("public"));

app.use(session({
    secret: "aircraft-dashboard-secret",
    resave: false,
    saveUninitialized: false
}));

function read(file) {
    try {
        return JSON.parse(fs.readFileSync(path.join(DATA_PATH, file), "utf8"));
    } catch {
        return {};
    }
}

function write(file, data) {
    fs.writeFileSync(
        path.join(DATA_PATH, file),
        JSON.stringify(data, null, 2)
    );
}

app.get("/login", (req, res) => {
    const url =
        `https://discord.com/api/oauth2/authorize` +
        `?client_id=${CLIENT_ID}` +
        `&redirect_uri=${encodeURIComponent(REDIRECT)}` +
        `&response_type=code` +
        `&scope=identify%20guilds`;

    res.redirect(url);
});

app.get("/callback", async (req, res) => {
    const code = req.query.code;

    const params = new URLSearchParams();
    params.append("client_id", CLIENT_ID);
    params.append("client_secret", CLIENT_SECRET);
    params.append("grant_type", "authorization_code");
    params.append("code", code);
    params.append("redirect_uri", REDIRECT);

    try {
        const tokenRes = await fetch("https://discord.com/api/oauth2/token", {
            method: "POST",
            body: params,
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            }
        });

        const token = await tokenRes.json();

        const guildsRes = await fetch("https://discord.com/api/users/@me/guilds", {
            headers: {
                Authorization: `Bearer ${token.access_token}`
            }
        });

        const guilds = await guildsRes.json();

        req.session.guilds = guilds;

        res.redirect("/");
    } catch (err) {
        console.error("OAuth error:", err);
        res.send("OAuth failed");
    }
});

app.get("/api/guilds", (req, res) => {
    if (!req.session.guilds) return res.json([]);

    const adminGuilds = req.session.guilds.filter(g =>
        (g.permissions & 0x8) === 0x8
    );

    res.json(adminGuilds);
});

app.get("/api/config/:guild", (req, res) => {
    const config = read("config.json");
    const logs = read("logs.json");

    res.json({
        roles: config[req.params.guild] || [],
        logs: logs[req.params.guild] || null
    });
});

app.post("/api/config/:guild", (req, res) => {
    const config = read("config.json");
    const logs = read("logs.json");

    config[req.params.guild] = req.body.roles || [];
    logs[req.params.guild] = req.body.logs || null;

    write("config.json", config);
    write("logs.json", logs);

    res.json({ success: true });
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
    console.log("Dashboard running on port " + PORT);
});
