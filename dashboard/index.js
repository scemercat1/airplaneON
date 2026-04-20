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
    secret: "aircraft-dashboard",
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
        return [];
    }
}

function write(file, data) {
    fs.writeFileSync(path.join(DATA_PATH, file), JSON.stringify(data, null, 2));
}

/* =========================
   HOME
========================= */

app.get("/", (req, res) => {
    res.send("Aircraft Dashboard Online");
});

/* =========================
   LOGIN
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
   CALLBACK (OAUTH FIXED)
========================= */

app.get("/callback", async (req, res) => {
    const code = req.query.code;

    if (!code) return res.send("No code received");

    try {
        const params = new URLSearchParams({
            client_id: CLIENT_ID,
            client_secret: CLIENT_SECRET,
            grant_type: "authorization_code",
            code,
            redirect_uri: REDIRECT
        });

        const tokenRes = await fetch("https://discord.com/api/oauth2/token", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body: params
        });

        const tokenData = await tokenRes.json();

        if (!tokenRes.ok) {
            console.log("OAuth error:", tokenData);
            return res.send("OAuth error: " + JSON.stringify(tokenData));
        }

        if (!tokenData.access_token) {
            return res.send("No access token");
        }

        // 🔥 USER GUILDS
        const guildsRes = await fetch("https://discord.com/api/users/@me/guilds", {
            headers: {
                Authorization: `Bearer ${tokenData.access_token}`
            }
        });

        const userGuilds = await guildsRes.json();

        if (!Array.isArray(userGuilds)) {
            return res.send("Guild fetch failed");
        }

        req.session.guilds = userGuilds;

        res.redirect("/dashboard");

    } catch (err) {
        console.log("OAuth exception:", err);
        res.send("OAuth exception (check logs)");
    }
});

/* =========================
   DASHBOARD
========================= */

app.get("/dashboard", (req, res) => {
    if (!req.session.guilds) return res.redirect("/login");

    const botGuilds = read("bot_guilds.json") || [];

    const options = req.session.guilds.map(g => {
        const hasBot = botGuilds.includes(g.id);

        return `
        <option value="${g.id}">
            ${g.name} ${hasBot ? "🟢 Bot" : "🔴 No Bot"}
        </option>`;
    }).join("");

    res.send(`
<!DOCTYPE html>
<html>
<head>
<title>Aircraft Dashboard</title>
<style>
body{margin:0;font-family:Arial;background:#0f0f0f;color:white}
.container{padding:20px}
.card{background:#1a1a1a;padding:15px;margin:10px 0;border-radius:10px}
input,select,textarea{width:100%;padding:8px;margin-top:5px;border-radius:6px;border:none;background:#2a2a2a;color:white}
button{padding:10px;background:#5865F2;border:none;color:white;border-radius:6px;cursor:pointer}
button:hover{background:#4752c4}
</style>
</head>
<body>

<div class="container">

<h1>🔥 Aircraft Dashboard</h1>

<div class="card">
<h2>Servers</h2>
<select id="guild">${options}</select>
</div>

<div class="card">
<h2>Moderation Messages</h2>
<input id="warn" placeholder="Warn message">
<input id="mute" placeholder="Mute message">
<input id="ban" placeholder="Ban message">
<input id="kick" placeholder="Kick message">
</div>

<div class="card">
<h2>Announcement</h2>
<input id="channel" placeholder="Channel ID">
<textarea id="message"></textarea>
<button onclick="send()">Send</button>
</div>

<button onclick="save()">Save</button>

</div>

<script>

async function save(){
    await fetch("/api/save",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            guild:guild.value,
            warn:warn.value,
            mute:mute.value,
            ban:ban.value,
            kick:kick.value
        })
    });

    alert("Saved");
}

async function send(){
    const res = await fetch("/api/announce",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            guild:guild.value,
            channel:channel.value,
            message:message.value
        })
    });

    const data = await res.json();

    if(!data.ok){
        alert("Error: " + JSON.stringify(data.error));
    } else {
        alert("Sent successfully");
    }
}

</script>

</body>
</html>
    `);
});

/* =========================
   SAVE SETTINGS
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
   ANNOUNCEMENTS (REAL CHECK)
========================= */

app.post("/api/announce", async (req, res) => {
    try {
        const response = await fetch(
            `https://discord.com/api/v10/channels/${req.body.channel}/messages`,
            {
                method: "POST",
                headers: {
                    "Authorization": `Bot ${TOKEN}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    content: req.body.message
                })
            }
        );

        const data = await response.json();

        console.log("DISCORD RESPONSE:", data);

        if (!response.ok) {
            return res.json({ ok: false, error: data });
        }

        res.json({ ok: true });

    } catch (err) {
        console.log("ANNOUNCE ERROR:", err);
        res.json({ ok: false, error: err.toString() });
    }
});

/* =========================
   START
========================= */

const PORT = process.env.PORT;

app.listen(PORT, "0.0.0.0", () => {
    console.log("Dashboard running on " + PORT);
});
