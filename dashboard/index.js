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

        const guilds = await guildsRes.json();

        req.session.guilds = guilds;

        res.redirect("/dashboard");
    } catch (e) {
        console.log(e);
        res.send("OAuth failed");
    }
});

/* =========================
   🌐 DASHBOARD UI
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
body {
    margin:0;
    font-family: Arial;
    background:#0f0f0f;
    color:white;
}
.container {
    padding:20px;
}
.card {
    background:#1a1a1a;
    padding:20px;
    border-radius:12px;
    margin-bottom:20px;
}
select, input {
    padding:10px;
    margin:5px;
    width:100%;
    border-radius:8px;
    border:none;
}
button {
    padding:10px;
    background:#5865F2;
    border:none;
    color:white;
    border-radius:8px;
    cursor:pointer;
}
button:hover {
    background:#4752c4;
}
</style>
</head>
<body>

<div class="container">

<h1>🔥 Aircraft Dashboard</h1>

<div class="card">
<h3>🔥 Select Server Discord</h3>
<select id="guild">
${guildOptions}
</select>
</div>

<div class="card">
<h3>🔥 Roles (IDs separated by space)</h3>
<input id="roles" placeholder="roleID1 roleID2 roleID3">
</div>

<div class="card">
<h3>🔥 Logs Channel ID</h3>
<input id="logs" placeholder="channel ID">
</div>

<button onclick="save()">Save Config</button>

</div>

<script>
async function save() {
    const guild = document.getElementById("guild").value;
    const roles = document.getElementById("roles").value.split(" ");
    const logs = document.getElementById("logs").value;

    await fetch("/api/save", {
        method:"POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
            guild,
            roles,
            logs
        })
    });

    alert("Saved!");
}
</script>

</body>
</html>
    `);
});

/* =========================
   💾 SAVE CONFIG
========================= */

app.post("/api/save", (req, res) => {
    const config = read("config.json");
    const logs = read("logs.json");

    const { guild, roles, logs: logChannel } = req.body;

    config[guild] = roles;
    logs[guild] = logChannel;

    write("config.json", config);
    write("logs.json", logs);

    res.json({ ok: true });
});

/* =========================
   🚀 SERVER START
========================= */

const PORT = process.env.PORT;

app.listen(PORT, "0.0.0.0", () => {
    console.log("Dashboard running on " + PORT);
});
