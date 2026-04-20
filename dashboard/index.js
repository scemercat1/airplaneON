const express = require("express");
const session = require("express-session");
const { MongoClient } = require("mongodb");
const fetch = require("node-fetch");

const app = express();
const MONGO_URL = process.env.MONGO_URL;
const client = new MongoClient(MONGO_URL);

let settings_col, guilds_col;

async function initDB() {
    await client.connect();
    const db = client.db("aircraft_db");
    settings_col = db.collection("settings");
    guilds_col = db.collection("bot_presence");
    console.log("Dashboard connected to MongoDB");
}
initDB();

app.use(express.json());
app.use(express.static("public"));
app.use(session({
    secret: "aircraft-dashboard-secret",
    resave: false,
    saveUninitialized: false
}));

app.get("/login", (req, res) => {
    const url = `https://discord.com/api/oauth2/authorize?client_id=${process.env.CLIENT_ID}&redirect_uri=${encodeURIComponent(process.env.REDIRECT)}&response_type=code&scope=identify%20guilds`;
    res.redirect(url);
});

app.get("/callback", async (req, res) => {
    const code = req.query.code;
    if (!code) return res.send("No code");

    const params = new URLSearchParams({
        client_id: process.env.CLIENT_ID,
        client_secret: process.env.CLIENT_SECRET,
        grant_type: "authorization_code",
        code: code,
        redirect_uri: process.env.REDIRECT
    });

    const tokenRes = await fetch("https://discord.com/api/oauth2/token", {
        method: "POST",
        body: params,
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
    });
    const tokenData = await tokenRes.json();

    const guildsRes = await fetch("https://discord.com/api/users/@me/guilds", {
        headers: { Authorization: `Bearer ${tokenData.access_token}` }
    });
    const userGuilds = await guildsRes.json();

    const botData = await guilds_col.findOne({ _id: "bot_stats" });
    const botGuildIds = botData ? botData.active_guilds : [];

    const finalGuilds = userGuilds.filter(g => {
        const isAdmin = (BigInt(g.permissions) & 0x8n) === 0x8n || (BigInt(g.permissions) & 0x20n) === 0x20n;
        return isAdmin && botGuildIds.includes(g.id);
    });

    req.session.guilds = finalGuilds;
    res.redirect("/dashboard");
});

app.get("/dashboard", (req, res) => {
    if (!req.session.guilds) return res.redirect("/login");

    const options = req.session.guilds.map(g => `<option value="${g.id}">${g.name}</option>`).join("");

    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Aircraft Dashboard</title>
            <style>
                body { background: #0f0f0f; color: white; font-family: sans-serif; padding: 40px; }
                .card { background: #1a1a1a; padding: 20px; border-radius: 10px; max-width: 500px; margin-bottom: 20px; }
                input, select { width: 100%; padding: 10px; margin: 10px 0; background: #2a2a2a; color: white; border: none; border-radius: 5px; }
                button { background: #5865F2; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
            </style>
        </head>
        <body>
            <h1>Aircraft Dashboard</h1>
            <div class="card">
                <h3>Select Server</h3>
                <select id="guild">${options}</select>
            </div>
            <div class="card">
                <h3>Custom Mod Messages</h3>
                <input id="warn" placeholder="Warn message {reason}">
                <input id="kick" placeholder="Kick message {reason}">
                <button onclick="save()">Save to Cloud</button>
            </div>
            <script>
                async function save() {
                    const res = await fetch("/api/save", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            guild: document.getElementById("guild").value,
                            warn: document.getElementById("warn").value,
                            kick: document.getElementById("kick").value
                        })
                    });
                    if(res.ok) alert("Settings Synced to MongoDB!");
                }
            </script>
        </body>
        </html>
    `);
});

app.post("/api/save", async (req, res) => {
    await settings_col.updateOne(
        { guild_id: req.body.guild },
        { $set: { warn: req.body.warn, kick: req.body.kick } },
        { upsert: true }
    );
    res.json({ ok: true });
});

app.listen(process.env.PORT || 3000);
