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
    secret: "aircraft-dashboard",
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
    fs.writeFileSync(path.join(DATA_PATH, file), JSON.stringify(data, null, 2));
}

/* =========================
   🔐 LOGIN
========================= */

app.get("/login", (req, res) => {
    const url =
        `https://discord.com/api/oauth2/authorize` +
        `?client_id=${CLIENT_ID}` +
        `&redirect_uri=${encodeURIComponent(REDIRECT)}` +
        `&response_type=code&scope=identify%20guilds`;

    res.redirect(url);
});

/* =========================
   🔁 CALLBACK
========================= */

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

        req.session.guilds = await guildsRes.json();

        res.redirect("/dashboard");
    } catch (e) {
        console.log(e);
        res.send("OAuth failed");
    }
});

/* =========================
   🌐 DASHBOARD
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
body {background:#0f0f0f;color:white;font-family:Arial;margin:0}
.container{padding:20px}
.card{background:#1a1a1a;padding:15px;margin:10px 0;border-radius:10px}
input,select,textarea{width:100%;padding:8px;margin-top:5px;border-radius:6px;border:none}
button{padding:10px;background:#5865F2;border:none;color:white;border-radius:6px;cursor:pointer}
button:hover{background:#4752c4}
h2{margin-top:0}
</style>
</head>
<body>

<div class="container">

<h1>🔥 Aircraft Dashboard</h1>

<div class="card">
<h2>🔥 Select Server</h2>
<select id="guild">${guildOptions}</select>
</div>

<div class="card">
<h2>🛡 Moderation Messages</h2>

<label>Warn Message</label>
<input id="warn" placeholder="You were warned for {reason}">

<label>Mute Message</label>
<input id="mute" placeholder="You were muted for {reason}">

<label>Ban Message</label>
<input id="ban" placeholder="You were banned for {reason}">

<label>Kick Message</label>
<input id="kick" placeholder="You were kicked for {reason}">
</div>

<div class="card">
<h2>📢 Announcement</h2>

<label>Channel ID</label>
<input id="ann_channel" placeholder="channel id">

<label>Message</label>
<textarea id="ann_msg" placeholder="announcement text"></textarea>

<button onclick="sendAnn()">Send Announcement</button>
</div>

<button onclick="save()">💾 Save Settings</button>

</div>

<script>
async function save(){
    const guild=document.getElementById("guild").value;

    await fetch("/api/save",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            guild,
            warn:document.getElementById("warn").value,
            mute:document.getElementById("mute").value,
            ban:document.getElementById("ban").value,
            kick:document.getElementById("kick").value
        })
    });

    alert("Saved!");
}

async function sendAnn(){
    const guild=document.getElementById("guild").value;

    await fetch("/api/announce",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            guild,
            channel:document.getElementById("ann_channel").value,
            message:document.getElementById("ann_msg").value
        })
    });

    alert("Sent!");
}
</script>

</body>
</html>
    `);
});

/* =========================
   💾 SAVE MOD SETTINGS
========================= */

app.post("/api/save", (req, res) => {
    const mod = read("mod_messages.json");

    const { guild, warn, mute, ban, kick } = req.body;

    mod[guild] = { warn, mute, ban, kick };

    write("mod_messages.json", mod);

    res.json({ ok: true });
});

/* =========================
   📢 ANNOUNCEMENTS
========================= */

app.post("/api/announce", async (req, res) => {
    const { guild, channel, message } = req.body;

    try {
        await fetch(`https://discord.com/api/v10/channels/${channel}/messages`, {
            method: "POST",
            headers: {
                "Authorization": `Bot ${process.env.DISCORD_TOKEN}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                content: message
            })
        });

        res.json({ ok: true });
    } catch (e) {
        console.log(e);
        res.json({ ok: false });
    }
});

/* =========================
   🚀 START
========================= */

const PORT = process.env.PORT;

app.listen(PORT, "0.0.0.0", () => {
    console.log("Dashboard running on " + PORT);
});
