const status = document.querySelector("#status");
const table = document.querySelector("table");
const gamesBody = document.querySelector("#games");

function gameTime(game) {
    if (game.status_description && game.status_description !== "In Progress") {
        return game.status_description;
    }

    const period = Number(game.half);
    let half = game.half || "-";

    if (period === 1) {
        half = "1st";
    } else if (period === 2) {
        half = "2nd";
    } else if (period > 2) {
        half = `${period - 2}OT`;
    }

    return `${game.display_clock || "-"} ${half}`;
}

try {
    const response = await fetch("/landolytics/api/liveGames");

    if (!response.ok) {
        throw new Error(`Live games request failed: HTTP ${response.status}`);
    }

    const data = await response.json();

    for (const game of data.games) {
        const row = document.createElement("tr");
        const awayScore = game.away_team_score ?? "-";
        const homeScore = game.home_team_score ?? "-";

        const columns = [
            {
                value: game.away_team_abbreviation || "-",
                className: "away-team",
            },
            {
                value: `${awayScore} - ${gameTime(game)} - ${homeScore}`,
                className: "live-score",
            },
            {
                value: game.home_team_abbreviation || "-",
                className: "home-team",
            },
        ];

        for (const { value, className } of columns) {
            const cell = document.createElement("td");
            cell.classList.add(className);
            cell.textContent = value;
            row.append(cell);
        }

        gamesBody.append(row);
    }

    table.hidden = data.games.length === 0;
    status.textContent = data.games.length === 0
        ? "No live games."
        : `${data.count} live games.`;
} catch (error) {
    console.error("Unable to load live games", error);
    status.textContent = "Unable to load live games. Please reload to try again.";
}
