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
//          HOMEPAGE & STATIC FILES
// ==========================================

// Serve static assets from the nested folder and the standard root public folder
app.use(express.static(path.join(__dirname, "dashboard", "public")));
app.use(express.static("public")); 

// Explicit homepage route
app.get("/", (req, res) => {
    // Tries to send the dashboard index, falls back to a simple string if not found
    const indexPath = path.join(__dirname, "dashboard", "public", "index.html");
    if (require('fs').existsSync(indexPath)) {
        res.sendFile(indexPath);
    } else {
        res.send("Dashboard running");
    }
});

// Health check endpoint from your old example
app.get("/health", (req, res) => {
    res.send("OK");
});

app.use(session({ secret: "aircraft-dashboard", resave: false, saveUninitialized: false }));

// ==========================================
//               OAUTH2 & LOGIN
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
//           DASHBOARD ROUTING
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
//                API ACTIONS
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
    body { background: #0f0f0f; color: white; font-family: 'Segoe UI', sans-serif; padding: 20px; margin: 0; }
    .container { max-width: 1000px; margin: 0 auto; }
    h1 { text-align: center; color: #5865F2; }
    .server-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; padding: 20px 0; }
    .server-card { background: #1a1a1a; padding: 20px; border-radius: 12px; text-align: center; text-decoration: none; color: white; display: block; border: 2px solid transparent; transition: 0.2s; }
    .server-card:hover { transform: translateY(-5px); background: #2a2a2a; border-color: #5865F2; }
    .server-icon { width: 80px; height: 80px; border-radius: 50%; background: #2a2a2a; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center; overflow: hidden;}
    .server-icon img { width: 100%; height: 100%; object-fit: cover; }
    .panels { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
    .card { background: #1a1a1a; padding: 25px; border-radius: 12px; }
    input, textarea { width: 100%; padding: 12px; margin-top: 5px; background: #2a2a2a; color: white; border: 1px solid #333; border-radius: 6px; box-sizing: border-box; }
    button { padding: 12px 24px; border-radius: 6px; cursor: pointer; border: none; font-weight: bold; background: #5865F2; color: white; }
</style>
`;

function getIconUrl(guild) {
    return guild.icon ? `https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.png` : null;
}

function renderServerList(guilds) {
    const cards = guilds.map(g => {
        const icon = getIconUrl(g);
        return `<a href="/dashboard/${g.id}" class="server-card"><div class="server-icon">${icon ? `<img src="${icon}">` : g.name[0]}</div><div class="server-name">${g.name}</div></a>`;
    }).join("");
    return `<html><head><title>Dashboard</title>${BASE_STYLE}</head><body><div class="container"><h1>🔥 Aircraft Dashboard</h1><div class="server-grid">${cards}</div></div></body></html>`;
}

function renderServerConfig(guild, settings) {
    return `<html><head><title>${guild.name}</title>${BASE_STYLE}</head><body>
    <div class="container">
        <h2>Configuring ${guild.name}</h2>
        <div class="panels">
            <div class="card">
                <h3>Moderation</h3>
                <label>Warn Message</label><input id="warn" value="${settings.warn || ''}">
                <label>Kick Message</label><input id="kick" value="${settings.kick || ''}">
                <button onclick="save()">Save</button>
            </div>
            <div class="card">
                <h3>Announce</h3>
                <input id="ch" placeholder="Channel ID"><textarea id="msg"></textarea>
                <button style="background:#2ecc71" onclick="ann()">Send</button>
            </div>
        </div>
    </div>
    <script>
        async function save(){
            await fetch("/api/save", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({guild:"${guild.id}", warn:document.getElementById("warn").value, kick:document.getElementById("kick").value})});
            alert("Saved");
        }
        async function ann(){
            const res = await fetch("/api/announce", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({channel:document.getElementById("ch").value, message:document.getElementById("msg").value})});
            const data = await res.json();
            alert(data.ok ? "Sent" : "Error");
        }
    </script>
    </body></html>`;
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, "0.0.0.0", () => {
    console.log("Running on", PORT);
});
