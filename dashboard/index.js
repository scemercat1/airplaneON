const express = require("express");
const session = require("express-session");
const fetch = require("node-fetch");

const app = express();

const CLIENT_ID = process.env.CLIENT_ID;
const CLIENT_SECRET = process.env.CLIENT_SECRET;
const REDIRECT = process.env.REDIRECT;

app.use(express.json());
app.use(express.static("public"));

app.use(session({
    secret: "aircraft-secret",
    resave: false,
    saveUninitialized: false
}));

// 🧠 HOME
app.get("/", (req, res) => {
    res.send("Dashboard is running");
});

// 🔐 LOGIN
app.get("/login", (req, res) => {
    const url =
        `https://discord.com/api/oauth2/authorize` +
        `?client_id=${CLIENT_ID}` +
        `&redirect_uri=${encodeURIComponent(REDIRECT)}` +
        `&response_type=code` +
        `&scope=identify%20guilds`;

    res.redirect(url);
});

// 🔁 CALLBACK
app.get("/callback", async (req, res) => {
    const code = req.query.code;

    if (!code) return res.send("No code provided");

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

        const tokenData = await tokenRes.json();

        if (!tokenData.access_token) {
            return res.send("Auth failed");
        }

        const userRes = await fetch("https://discord.com/api/users/@me", {
            headers: {
                Authorization: `Bearer ${tokenData.access_token}`
            }
        });

        const user = await userRes.json();

        req.session.user = user;

        res.redirect("/");
    } catch (err) {
        console.error(err);
        res.send("OAuth error");
    }
});

// 🧪 TEST ROUTE (FOARTE IMPORTANT)
app.get("/health", (req, res) => {
    res.send("OK");
});

// 🚀 PORT (RAILWAY SAFE)
const PORT = process.env.PORT;

app.listen(PORT, "0.0.0.0", () => {
    console.log("Dashboard running on port " + PORT);
});
