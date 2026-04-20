const express = require("express");
const session = require("express-session");
const fetch = require("node-fetch");
const fs = require("fs");

const app = express();

const CLIENT_ID = process.env.CLIENT_ID;
const CLIENT_SECRET = process.env.CLIENT_SECRET;
const REDIRECT = process.env.REDIRECT;

const BOT_GUILDS_FILE = "./bot_guilds.json";
const CONFIG_FILE = "./config.json";

app.use(express.json());
app.use(session({
    secret: "dash_secret",
    resave: false,
    saveUninitialized: false
}));

function read(file){
    if(!fs.existsSync(file)) return {};
    return JSON.parse(fs.readFileSync(file));
}

function write(file, data){
    fs.writeFileSync(file, JSON.stringify(data, null, 2));
}

function intersect(a,b){
    return a.filter(x => b.includes(x));
}

/* ================= LOGIN ================= */

app.get("/login",(req,res)=>{
    res.redirect(
        `https://discord.com/api/oauth2/authorize` +
        `?client_id=${CLIENT_ID}` +
        `&redirect_uri=${encodeURIComponent(REDIRECT)}` +
        `&response_type=code&scope=identify%20guilds`
    );
});

/* ================= CALLBACK ================= */

app.get("/callback", async (req,res)=>{
    const code = req.query.code;

    const token = await fetch("https://discord.com/api/oauth2/token",{
        method:"POST",
        headers:{"Content-Type":"application/x-www-form-urlencoded"},
        body:new URLSearchParams({
            client_id:CLIENT_ID,
            client_secret:CLIENT_SECRET,
            grant_type:"authorization_code",
            code,
            redirect_uri:REDIRECT
        })
    }).then(r=>r.json());

    const guilds = await fetch("https://discord.com/api/users/@me/guilds",{
        headers:{Authorization:`Bearer ${token.access_token}`}
    }).then(r=>r.json());

    req.session.guilds = guilds;
    res.redirect("/dashboard");
});

/* ================= DASHBOARD ================= */

app.get("/dashboard",(req,res)=>{
    if(!req.session.guilds) return res.redirect("/login");

    const botGuilds = read(BOT_GUILDS_FILE);
    const config = read(CONFIG_FILE);

    const userGuilds = req.session.guilds;

    // ONLY OWNER GUILDS
    const ownerGuilds = userGuilds.filter(g => g.owner === true);

    // ONLY WHERE BOT EXISTS
    const botGuildIds = Array.isArray(botGuilds) ? botGuilds : [];

    const filtered = ownerGuilds.filter(g =>
        botGuildIds.includes(String(g.id))
    );

    const cards = filtered.map(g=>{
        const cfg = config[g.id] || { commands: {}, messages: {} };

        return `
        <div style="background:#1e1e1e;padding:15px;margin:10px;border-radius:10px;color:white">
            <h2>${g.name}</h2>

            <p>Commands:</p>
            <pre>${JSON.stringify(cfg.commands, null, 2)}</pre>

            <a href="/dashboard/${g.id}" style="color:#5865F2">Configure</a>
        </div>
        `;
    }).join("");

    res.send(`
    <body style="background:#0f0f0f;color:white;font-family:Arial">
        <h1>Dashboard</h1>

        <a href="https://discord.com/oauth2/authorize?client_id=${CLIENT_ID}&permissions=8&scope=bot"
           style="color:#5865F2">
           Invite Bot
        </a>

        <div>${cards || "<h3>No servers found</h3>"}</div>
    </body>
    `);
});

/* ================= SERVER CONFIG ================= */

app.get("/dashboard/:id",(req,res)=>{
    const id = req.params.id;
    const config = read(CONFIG_FILE);

    const data = config[id] || {
        commands: {
            warn: true,
            mute: true,
            ban: true,
            kick: true
        },
        messages: {
            warn: "You were warned",
            mute: "You were muted",
            ban: "You were banned",
            kick: "You were kicked"
        }
    };

    res.send(`
    <body style="background:#0f0f0f;color:white;font-family:Arial">
        <h1>Server Config</h1>

        <form method="POST" action="/save/${id}">
            <h3>Enable/Disable Commands</h3>

            ${Object.keys(data.commands).map(cmd=>{
                return `
                <label>
                    <input type="checkbox" name="${cmd}" ${data.commands[cmd] ? "checked" : ""}>
                    ${cmd}
                </label><br>
                `;
            }).join("")}

            <h3>Custom Messages</h3>

            ${Object.keys(data.messages).map(msg=>{
                return `
                <label>${msg}</label><br>
                <input name="msg_${msg}" value="${data.messages[msg]}"><br><br>
                `;
            }).join("")}

            <button type="submit">Save</button>
        </form>
    </body>
    `);
});

/* ================= SAVE CONFIG ================= */

app.post("/save/:id",(req,res)=>{
    let body = "";

    req.on("data", chunk => body += chunk);
    req.on("end", ()=>{
        const params = new URLSearchParams(body);

        const id = req.params.id;

        const config = read(CONFIG_FILE);

        config[id] = {
            commands: {
                warn: params.get("warn") === "on",
                mute: params.get("mute") === "on",
                ban: params.get("ban") === "on",
                kick: params.get("kick") === "on"
            },
            messages: {
                warn: params.get("msg_warn"),
                mute: params.get("msg_mute"),
                ban: params.get("msg_ban"),
                kick: params.get("msg_kick")
            }
        };

        write(CONFIG_FILE, config);

        res.redirect("/dashboard");
    });
});

/* ================= START ================= */

app.listen(process.env.PORT, ()=>{
    console.log("Dashboard running");
});
