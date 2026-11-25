package web

import "embed"

// Assets contains the embedded frontend files.
//
//go:embed index.html live.html style.css script.js live.js
var Assets embed.FS
