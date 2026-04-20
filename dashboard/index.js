const express = require("express");
const session = require("express-session");
const { MongoClient } = require("mongodb");
const fetch = require("node-fetch");
const path = require("path");

const app = express();
const client = new MongoClient(process.env.MONGO_URL);
let settings_col, guilds_col;

async function init() {
    await client.connect();
    const db = client.db("aircraft_db");
    settings_col = db.collection("settings");
    guilds_col = db.collection("bot_presence");
    console.log("Connected to MongoDB");
}
init();

app.use(express.json());

// ==========================================
//          HOMEPAGE & STATIC FIX
// ==========================================

// This specifically fixes the "Not Found" error for the main site
app.get("/", (req, res) => {
    res.sendFile(path.join(__dirname, "dashboard", "public", "index.html"));
});

// This serves your CSS and other files in that folder
app.use(express.static(path.join(__dirname, "dashboard", "public")));

app.use(session({ secret: "aircraft-dashboard", resave: false, saveUninitialized: false }));

// ==========================================
//              OAUTH2 & LOGIN
// ==========================================
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

    const tokenRes = await fetch("https://discord.com/api/oauth2/token", { method: "POST", body: params, headers: { "Content-Type": "application/x-www-form-urlencoded" } });
    const tokenData = await tokenRes.json();

    if (tokenData.error) return res.send(`Auth Error: ${tokenData.error_description}`);

    const guildsRes = await fetch("https://discord.com/api/users/@me/guilds", { headers: { Authorization: `Bearer ${tokenData.access_token}` } });
    const userGuilds = await guildsRes.json();

    const botData = await guilds_col.findOne({ _id: "bot_stats" });
    const botGuildIds = botData ? botData.active_guilds : [];

    const finalGuilds = userGuilds.filter(g => {
        const isAdmin = (BigInt(g.permissions) & 0x8n) === 0x8n || (BigInt(g.permissions) & 0x20n) === 0x20n;
        return isAdmin && botGuildIds.includes(g.id);
    });

    req.session.token = tokenData.access_token;
    req.session.guilds = finalGuilds;
    res.redirect("/dashboard");
});

// ==========================================
//          DASHBOARD ROUTING LOOP
// ==========================================
app.get("/dashboard", (req, res) => {
    if (!req.session.guilds) return res.redirect("/login");
    res.send(renderServerList(req.session.guilds));
});

app.get("/dashboard/:guildId", async (req, res) => {
    if (!req.session.guilds) return res.redirect("/login");
    
    const guildId = req.params.guildId;
    const guild = req.session.guilds.find(g => g.id === guildId);
    if (!guild) return res.status(403).send("Forbidden: You do not own this server.");

    const settings = await settings_col.findOne({ guild_id: guildId }) || {};
    res.send(renderServerConfig(guild, settings));
});

// ==========================================
//                API ENDPOINTS
// ==========================================
app.post("/api/save", async (req, res) => {
    const { guild, warn, kick } = req.body;
    await settings_col.updateOne({ guild_id: guild }, { $set: { warn, kick } }, { upsert: true });
    res.json({ ok: true });
});

app.post("/api/announce", async (req, res) => {
    const { channel, message } = req.body;
    try {
        const discordRes = await fetch(`https://discord.com/api/v10/channels/${channel}/messages`, {
            method: "POST",
            headers: {
                "Authorization": `Bot ${process.env.DISCORD_TOKEN}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ content: message })
        });
        
        const data = await discordRes.json();
        if (discordRes.ok) {
            res.json({ ok: true });
        } else {
            res.json({ ok: false, error: data });
        }
    } catch (e) {
        res.json({ ok: false, error: "Internal Error" });
    }
});

// ==========================================
//              HTML RENDERERS
// ==========================================
const BASE_STYLE = `
<style>
    body { background: #0f0f0f; color: white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; margin: 0; }
    .container { max-width: 1000px; margin: 0 auto; }
    h1 { text-align: center; color: #5865F2; }
    .server-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; padding: 20px 0; }
    .server-card { background: #1a1a1a; padding: 20px; border-radius: 12px; text-align: center; cursor: pointer; transition: transform 0.2s, background 0.2s; border: 2px solid transparent; text-decoration: none; color: white; display: block; }
    .server-card:hover { transform: translateY(-5px); background: #2a2a2a; border-color: #5865F2; }
    .server-icon { width: 80px; height: 80px; border-radius: 50%; background: #2a2a2a; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center; font-size: 30px; font-weight: bold; color: #aaa; overflow: hidden;}
    .server-icon img { width: 100%; height: 100%; object-fit: cover; }
    .server-name { font-weight: bold; font-size: 1.1em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .header-bar { display: flex; align-items: center; justify-content: space-between; background: #1a1a1a; padding: 15px 30px; border-radius: 12px; margin-bottom: 20px; }
    .back-btn { background: #333; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; text-decoration: none; font-size: 0.9em; }
    .current-server { display: flex; align-items: center; gap: 15px; }
    .current-icon { width: 40px; height: 40px; border-radius: 50%; background: #2a2a2a; overflow: hidden; display: flex; align-items: center; justify-content: center;}
    .current-icon img { width: 100%; height: 100%; object-fit: cover; }
    .panels { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
    .card { background: #1a1a1a; padding: 25px; border-radius: 12px; }
    h2 { border-bottom: 2px solid #333; padding-bottom: 10px; margin-top: 0; }
    label { display: block; margin-top: 15px; color: #aaa; font-size: 0.9em; }
    input, textarea { width: 100%; padding: 12px; margin-top: 5px; background: #2a2a2a; color: white; border: 1px solid #333; border-radius: 6px; box-sizing: border-box; }
    textarea { height: 100px; resize: vertical; }
    .btn-group { margin-top: 20px; display: flex; gap: 10px; }
    button { padding: 12px 24px; border-radius: 6px; cursor: pointer; border: none; font-weight: bold; transition: background 0.2s; }
    .btn-save { background: #5865F2; color: white; }
    .btn-save:hover { background: #4752c4; }
    .btn-ann { background: #2ecc71; color: white; width: 100%; margin-top: 10px;}
    .btn-ann:hover { background: #27ae60; }
</style>
`;

function getIconUrl(guild) {
    if (guild.icon) return `https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.png`;
    return null;
}

function renderServerList(guilds) {
    const cards = guilds.map(g => {
        const iconUrl = getIconUrl(g);
        const iconHtml = iconUrl ? `<img src="${iconUrl}" alt="${g.name}">` : g.name.charAt(0);
        return `
            <a href="/dashboard/${g.id}" class="server-card">
                <div class="server-icon">${iconHtml}</div>
                <div class="server-name">${g.name}</div>
            </a>
        `;
    }).join("");
    return `<!DOCTYPE html><html><head><title>Select Server | Aircraft</title>${BASE_STYLE}</head><body><div class="container"><h1>🔥 Aircraft Dashboard</h1><h2>Select a Server to Configure</h2><div class="server-grid">${cards}</div></div></body></html>`;
}

function renderServerConfig(guild, settings) {
    const iconUrl = getIconUrl(guild);
    const iconHtml = iconUrl ? `<img src="${iconUrl}">` : guild.name.charAt(0);
    return `
<!DOCTYPE html>
<html>
<head><title>Config | ${guild.name}</title>${BASE_STYLE}</head>
<body>
    <div class="container">
        <div class="header-bar">
            <div class="current-server">
                <div class="current-icon">${iconHtml}</div>
                <h3>${guild.name}</h3>
            </div>
            <a href="/dashboard" class="back-btn">← Back to Servers</a>
        </div>
        <div class="panels">
            <div class="card">
                <h2>Moderation Custom Messages</h2>
                <p><small>Use <code>{reason}</code> to insert the reason.</small></p>
                <label>Warn Message</label>
                <input id="warn" value="${settings.warn || ''}">
                <label>Kick Message</label>
                <input id="kick" value="${settings.kick || ''}">
                <div class="btn-group"><button class="btn-save" onclick="saveSettings()">Save Mod Settings</button></div>
            </div>
            <div class="card">
                <h2>Send Announcement</h2>
                <label>Channel ID</label>
                <input id="annChannel" placeholder="1234567890">
                <label>Message</label>
                <textarea id="annMsg"></textarea>
                <button class="btn-ann" onclick="sendAnn()">Send Announcement</button>
            </div>
        </div>
    </div>
    <script>
        const guildId = "${guild.id}";
        async function saveSettings() {
            await fetch("/api/save", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ guild: guildId, warn: document.getElementById("warn").value, kick: document.getElementById("kick").value }) });
            alert("Saved!");
        }
        async function sendAnn() {
            const res = await fetch("/api/announce", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ channel: document.getElementById("annChannel").value, message: document.getElementById("annMsg").value }) });
            const data = await res.json();
            if(data.ok) alert("Sent!"); else alert("Error: " + JSON.stringify(data.error));
        }
    </script>
</body></html>`;
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, "0.0.0.0");
