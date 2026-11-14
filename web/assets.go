package web

import "embed"

// Assets contains the embedded frontend files.
//
//go:embed index.html style.css script.js
var Assets embed.FS
