const express = require("express");
const session = require("express-session");
const fetch = require("node-fetch");
const fs = require("fs");
const path = require("path");

const app = express();

const CLIENT_ID = process.env.CLIENT_ID;
const CLIENT_SECRET = process.env.CLIENT_SECRET;
const REDIRECT = process.env.REDIRECT;
const TOKEN = process.env.DISCORD_TOKEN;

const DATA_PATH = "/data";

app.use(express.json());
app.use(express.static("public"));

app.use(session({
    secret: "aircraft-dashboard-secret",
    resave: false,
    saveUninitialized: false
}));

/* =========================
   FILE HELPERS
========================= */

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

/* =========================
   LOGIN
========================= */

app.get("/login", (req, res) => {
    const url =
        `https://discord.com/api/oauth2/authorize` +
        `?client_id=${CLIENT_ID}` +
        `&redirect_uri=${encodeURIComponent(REDIRECT)}` +
        `&response_type=code` +
        `&scope=identify%20guilds`;

    res.redirect(url);
});

/* =========================
   CALLBACK + GUILD FILTER
========================= */

app.get("/callback", async (req, res) => {
    const code = req.query.code;

    try {
        const params = new URLSearchParams();
        params.append("client_id", CLIENT_ID);
        params.append("client_secret", CLIENT_SECRET);
        params.append("grant_type", "authorization_code");
        params.append("code", code);
        params.append("redirect_uri", REDIRECT);

        const tokenRes = await fetch("https://discord.com/api/oauth2/token", {
            method: "POST",
            body: params,
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            }
        });

        const token = await tokenRes.json();

        const userGuildsRes = await fetch("https://discord.com/api/users/@me/guilds", {
            headers: {
                Authorization: `Bearer ${token.access_token}`
            }
        });

        let userGuilds = await userGuildsRes.json();

        const botGuildsRes = await fetch("https://discord.com/api/users/@me/guilds", {
            headers: {
                Authorization: `Bot ${TOKEN}`
            }
        });

        const botGuilds = await botGuildsRes.json();

        const botGuildIds = botGuilds.map(g => g.id);

        // 🔥 FILTER: only mutual servers
        userGuilds = userGuilds.filter(g => botGuildIds.includes(g.id));

        req.session.guilds = userGuilds;

        res.redirect("/dashboard");
    } catch (err) {
        console.log(err);
        res.send("OAuth failed");
    }
});

/* =========================
   DASHBOARD UI
========================= */

app.get("/dashboard", (req, res) => {
    if (!req.session.guilds) return res.redirect("/login");

    const guildOptions = req.session.guilds
        .map(g => `<option value="${g.id}">${g.name}</option>`)
        .join("");

    res.send(`
<!DOCTYPE html>
<html>
<head>
<title>Aircraft Dashboard</title>
<style>
body {margin:0;font-family:Arial;background:#0f0f0f;color:white}
.container {padding:20px}
.card {background:#1a1a1a;padding:15px;margin:10px 0;border-radius:10px}
input,select,textarea {width:100%;padding:8px;margin-top:5px;border-radius:6px;border:none;background:#2a2a2a;color:white}
button {padding:10px;background:#5865F2;border:none;color:white;border-radius:6px;cursor:pointer}
button:hover {background:#4752c4}
h2 {margin-top:0}
</style>
</head>
<body>

<div class="container">

<h1>🔥 Aircraft Dashboard</h1>

<div class="card">
<h2>🔥 Server Select</h2>
<select id="guild">${guildOptions}</select>
</div>

<div class="card">
<h2>🛡 Moderation Messages</h2>

<label>Warn</label>
<input id="warn" placeholder="You were warned for {reason}">

<label>Mute</label>
<input id="mute" placeholder="You were muted for {reason}">

<label>Ban</label>
<input id="ban" placeholder="You were banned for {reason}">

<label>Kick</label>
<input id="kick" placeholder="You were kicked for {reason}">
</div>

<div class="card">
<h2>📢 Announcement</h2>

<label>Channel ID</label>
<input id="channel" placeholder="channel id">

<label>Message</label>
<textarea id="message" placeholder="announcement text"></textarea>

<button onclick="sendAnn()">Send</button>
</div>

<button onclick="save()">💾 Save</button>

</div>

<script>
async function save(){
    const guild=document.getElementById("guild").value;

    await fetch("/api/save",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            guild,
            warn:warn.value,
            mute:mute.value,
            ban:ban.value,
            kick:kick.value
        })
    });

    alert("Saved");
}

async function sendAnn(){
    await fetch("/api/announce",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            guild:document.getElementById("guild").value,
            channel:document.getElementById("channel").value,
            message:document.getElementById("message").value
        })
    });

    alert("Sent");
}
</script>

</body>
</html>
    `);
});

/* =========================
   SAVE MOD SETTINGS
========================= */

app.post("/api/save", (req, res) => {
    const mod = read("mod_messages.json");

    mod[req.body.guild] = {
        warn: req.body.warn,
        mute: req.body.mute,
        ban: req.body.ban,
        kick: req.body.kick
    };

    write("mod_messages.json", mod);

    res.json({ ok: true });
});

/* =========================
   ANNOUNCEMENTS
========================= */

app.post("/api/announce", async (req, res) => {
    try {
        await fetch(`https://discord.com/api/v10/channels/${req.body.channel}/messages`, {
            method: "POST",
            headers: {
                "Authorization": `Bot ${TOKEN}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                content: req.body.message
            })
        });

        res.json({ ok: true });
    } catch (e) {
        console.log(e);
        res.json({ ok: false });
    }
});

/* =========================
   START SERVER
========================= */

const PORT = process.env.PORT;

app.listen(PORT, "0.0.0.0", () => {
    console.log("Dashboard running on " + PORT);
});
