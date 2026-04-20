const express = require("express");
const session = require("express-session");
const passport = require("passport");
const Strategy = require("passport-discord").Strategy;
const fs = require("fs");

const config = require("./config");

const app = express();

/* ================= BOT GUILDS ================= */

function getBotGuilds() {
    try {
        return JSON.parse(fs.readFileSync("./bot_guilds.json", "utf8"));
    } catch {
        return [];
    }
}

/* ================= PASSPORT ================= */

passport.serializeUser((user, done) => done(null, user));
passport.deserializeUser((obj, done) => done(null, obj));

passport.use(new Strategy({
    clientID: config.id,
    clientSecret: config.clientSecret,
    callbackURL: config.redirect,
    scope: ["identify", "guilds"]
}, (accessToken, refreshToken, profile, done) => {
    process.nextTick(() => done(null, profile));
}));

/* ================= MIDDLEWARE ================= */

app.use(session({
    secret: "secret",
    resave: false,
    saveUninitialized: false
}));

app.use(passport.initialize());
app.use(passport.session());

/* ================= LOGIN ================= */

app.get("/login", passport.authenticate("discord"));

/* ================= CALLBACK ================= */

app.get("/callback",
    passport.authenticate("discord", { failureRedirect: "/" }),
    (req, res) => {
        res.redirect("/dashboard");
    }
);

/* ================= DASHBOARD ================= */

app.get("/dashboard", (req, res) => {
    if (!req.user) return res.redirect("/login");

    const botGuilds = getBotGuilds();

    const userGuilds = req.user.guilds || [];

    const ownerGuilds = userGuilds.filter(g => g.owner === true);

    const guilds = ownerGuilds.filter(g =>
        botGuilds.includes(String(g.id))
    );

    let html = `
    <body style="background:#0f0f0f;color:white;font-family:Arial">
        <h1>Dashboard</h1>

        <a href="https://discord.com/oauth2/authorize?client_id=${config.id}&permissions=8&scope=bot"
           style="color:#5865F2">
           Invite Bot
        </a>

        <div>
    `;

    if (guilds.length === 0) {
        html += `<h3>No servers found</h3>`;
    } else {
        guilds.forEach(g => {
            html += `
                <div style="background:#1e1e1e;padding:10px;margin:10px;border-radius:8px">
                    <h3>${g.name}</h3>
                    <a href="/dashboard/${g.id}" style="color:#5865F2">Open</a>
                </div>
            `;
        });
    }

    html += `</div></body>`;
    res.send(html);
});

/* ================= SERVER PAGE ================= */

app.get("/dashboard/:id", (req, res) => {
    res.send(`
        <body style="background:#0f0f0f;color:white;font-family:Arial">
            <h1>Server Settings</h1>
            <p>Guild ID: ${req.params.id}</p>

            <a href="/dashboard" style="color:#5865F2">Back</a>
        </body>
    `);
});

/* ================= START ================= */

app.listen(config.port, () => {
    console.log("Dashboard running on port", config.port);
});
