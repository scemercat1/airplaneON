const express = require("express");
const session = require("express-session");
const fetch = require("node-fetch");
const fs = require("fs");
const path = require("path");

const app = express();

const CLIENT_ID = process.env.CLIENT_ID;
const CLIENT_SECRET = process.env.CLIENT_SECRET;
const REDIRECT = process.env.REDIRECT;

app.use(express.json());
app.use(express.static("public"));

app.use(session({
    secret: "dash",
    resave: false,
    saveUninitialized: false
}));

function read(file){
    try{
        return JSON.parse(fs.readFileSync(`/data/${file}`));
    }catch{
        return [];
    }
}

/* ================= LOGIN ================= */

app.get("/login",(req,res)=>{
    res.redirect(
        `https://discord.com/api/oauth2/authorize?client_id=${CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT)}&response_type=code&scope=identify%20guilds`
    );
});

/* ================= CALLBACK ================= */

app.get("/callback", async (req,res)=>{
    const code = req.query.code;
    if(!code) return res.send("No code");

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

    const botGuilds = read("bot_guilds.json");

    const list = req.session.guilds.map(g=>{
        const hasBot = botGuilds.includes(g.id);

        return `
        <div style="padding:10px;background:#1a1a1a;margin:10px;border-radius:10px">
            <b>${g.name}</b> ${hasBot ? "🟢" : "🔴"}
            <br>
            <a href="/dashboard/${g.id}">Open</a>
        </div>`;
    }).join("");

    res.send(`
    <h1>Servers</h1>
    <a href="https://discord.com/oauth2/authorize?client_id=1495464598331985940&permissions=8&scope=bot">Invite Bot</a>
    ${list}
    `);
});

const PORT = process.env.PORT;
app.listen(PORT,()=>console.log("Dashboard up"));
