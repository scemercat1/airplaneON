const express = require("express");
const session = require("express-session");
const fetch = require("node-fetch");

const app = express();

const CLIENT_ID = process.env.CLIENT_ID;
const CLIENT_SECRET = process.env.CLIENT_SECRET;
const REDIRECT = process.env.REDIRECT;

app.use(express.json());
app.use(session({
    secret: "dash",
    resave: false,
    saveUninitialized: false
}));

/* ================= LOGIN ================= */

app.get("/login",(req,res)=>{
    res.redirect(
        `https://discord.com/api/oauth2/authorize` +
        `?client_id=${CLIENT_ID}` +
        `&redirect_uri=${encodeURIComponent(REDIRECT)}` +
        `&response_type=code` +
        `&scope=identify%20guilds`
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

app.get("/dashboard", async (req,res)=>{
    if(!req.session.guilds) return res.redirect("/login");

    let botData = await fetch(process.env.BOT_API + "/guilds")
        .then(r=>r.json())
        .catch(()=>({guilds:[]}));

    const botGuildIds = botData.guilds.map(g => String(g.id));

    const cards = req.session.guilds.map(g=>{
        const hasBot = botGuildIds.includes(String(g.id));

        return `
        <div style="
            background:#1a1a1a;
            padding:15px;
            margin:10px;
            border-radius:10px;
            color:white;
        ">
            <h3>${g.name}</h3>
            <p>${hasBot ? "🟢 Bot online" : "🔴 Bot offline"}</p>
            <a href="/dashboard/${g.id}" style="color:#5865F2">Open</a>
        </div>`;
    }).join("");

    res.send(`
    <body style="background:#0f0f0f;color:white;font-family:Arial">
        <h1>🔥 Dashboard</h1>

        <a href="https://discord.com/oauth2/authorize?client_id=1495464598331985940&permissions=8&scope=bot"
           style="color:#5865F2">
           ➕ Invite Bot
        </a>

        <div>${cards}</div>
    </body>
    `);
});

/* ================= SERVER PAGE ================= */

app.get("/dashboard/:id",(req,res)=>{
    const id = req.params.id;

    res.send(`
        <body style="background:#0f0f0f;color:white;font-family:Arial">
            <h1>Server Config</h1>
            <p>Guild ID: ${id}</p>

            <a href="/dashboard" style="color:#5865F2">Back</a>
        </body>
    `);
});

/* ================= START ================= */

app.listen(process.env.PORT,()=>{
    console.log("Dashboard running");
});
