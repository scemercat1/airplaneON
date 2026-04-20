const express = require("express");
const session = require("express-session");
const fetch = require("node-fetch");
const fs = require("fs");
const path = require("path");

const app = express();

const CLIENT_ID = process.env.CLIENT_ID;
const CLIENT_SECRET = process.env.CLIENT_SECRET;
const REDIRECT = process.env.REDIRECT;
const TOKEN = process.env.DISCORD_TOKEN; // Bot Token
const DATA_PATH = "/data";

app.use(express.json());
app.use(express.static("public"));

app.use(session({
    secret: "aircraft-dashboard",
    resave: false,
    saveUninitialized: false,
    cookie: { secure: false } // Set to true if using HTTPS/SSL
}));

/* =========================
   FILE SYSTEM UTILS
========================= */
function read(file) {
    try {
        const filePath = path.join(DATA_PATH, file);
        if (!fs.existsSync(filePath)) return {};
        return JSON.parse(fs.readFileSync(filePath, "utf8"));
    } catch (e) {
        console.error("Read error:", e);
        return {};
    }
}

function write(file, data) {
    try {
        fs.writeFileSync(path.join(DATA_PATH, file), JSON.stringify(data, null, 2));
    } catch (e) {
        console.error("Write error:", e);
    }
}

/* =========================
   ROUTES
========================= */

app.get("/", (req, res) => {
    res.send('<h1>Dashboard Home</h1><a href="/login">Login with Discord</a>');
});

app.get("/login", (req, res) => {
    const url = `https://discord.com/api/oauth2/authorize?client_id=${CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT)}&response_type=code&scope=identify%20guilds`;
    res.redirect(url);
});

app.get("/callback", async (req, res) => {
    const code = req.query.code;
    if (!code) return res.send("No code provided.");

    try {
        // Exchange Code for Token
        const params = new URLSearchParams();
        params.append("client_id", CLIENT_ID);
        params.append("client_secret", CLIENT_SECRET);
        params.append("grant_type", "authorization_code");
        params.append("code", code);
        params.append("redirect_uri", REDIRECT);

        const tokenRes = await fetch("https://discord.com/api/oauth2/token", {
            method: "POST",
            body: params,
            headers: { "Content-Type": "application/x-www-form-urlencoded" }
        });

        const tokenData = await tokenRes.json();
        if (!tokenData.access_token) return res.send("Error fetching access token.");

        // Fetch User Guilds
        const guildsRes = await fetch("https://discord.com/api/users/@me/guilds", {
            headers: { Authorization: `Bearer ${tokenData.access_token}` }
        });
        const userGuilds = await guildsRes.json();

        // 🔥 THE FIX: Fetch Bot Guilds from file
        // Make sure your bot.py saves an array like ["ID1", "ID2"] to /data/bot_guilds.json
        let botGuildIds = [];
        try {
            const botData = fs.readFileSync(path.join(DATA_PATH, "bot_guilds.json"), "utf8");
            botGuildIds = JSON.parse(botData);
        } catch (e) {
            console.log("bot_guilds.json not found or empty. Showing all guilds user is in for debug.");
            // Temporary debug: if file is missing, show all guilds where user is admin
            botGuildIds = userGuilds.map(g => g.id); 
        }

        // Filter: User must have ADMIN (0x8) or MANAGE_GUILD (0x20) and bot must be there
        const finalGuilds = userGuilds.filter(g => {
            const isAdmin = (parseInt(g.permissions) & 0x8) === 0x8;
            const isManager = (parseInt(g.permissions) & 0x20) === 0x20;
            return (isAdmin || isManager) && botGuildIds.includes(g.id);
        });

        req.session.guilds = finalGuilds;
        res.redirect("/dashboard");

    } catch (err) {
        console.error(err);
        res.status(500).send("Internal Error");
    }
});

app.get("/dashboard", (req, res) => {
    if (!req.session.guilds || req.session.guilds.length === 0) {
        return res.send("No mutual servers found. Make sure the bot is in your server!");
    }

    const guildOptions = req.session.guilds
        .map(g => `<option value="${g.id}">${g.name}</option>`)
        .join("");

    // Your HTML here (same as you provided)
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Aircraft Dashboard</title>
            <style>
                body {margin:0;font-family:Arial;background:#0f0f0f;color:white}
                .container{padding:20px}
                .card{background:#1a1a1a;padding:15px;margin:10px 0;border-radius:10px}
                input,select,textarea{width:100%;padding:8px;margin-top:5px;border-radius:6px;border:none;background:#2a2a2a;color:white}
                button{padding:10px;background:#5865F2;border:none;color:white;border-radius:6px;cursor:pointer;margin-top:10px}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔥 Aircraft Dashboard</h1>
                <div class="card">
                    <h2>Select Server</h2>
                    <select id="guild">${guildOptions}</select>
                </div>
                <div class="card">
                    <h2>Moderation Messages</h2>
                    <input id="warn" placeholder="Warn Message">
                    <input id="mute" placeholder="Mute Message">
                    <button onclick="save()">Save Settings</button>
                </div>
            </div>
            <script>
                async function save(){
                    const guild = document.getElementById("guild").value;
                    await fetch("/api/save", {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({
                            guild: guild,
                            warn: document.getElementById("warn").value,
                            mute: document.getElementById("mute").value
                        })
                    });
                    alert("Saved to /data!");
                }
            </script>
        </body>
        </html>
    `);
});

app.post("/api/save", (req, res) => {
    const data = read("mod_messages.json");
    data[req.body.guild] = req.body;
    write("mod_messages.json", data);
    res.json({ ok: true });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, "0.0.0.0", () => console.log("Online on " + PORT));
