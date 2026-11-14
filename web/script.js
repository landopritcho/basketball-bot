const status = document.querySelector("#status");
const table = document.querySelector("table");
const gamesBody = document.querySelector("#games");

function teamLabel(school, name, abbreviation, primaryColor, alternateColor, rank) {
    const label = document.createElement("span");

    if (rank != null) {
        label.append(`#${rank} `);
    }

    const schoolLabel = document.createElement("span");
    schoolLabel.textContent = school ?? abbreviation ?? "Unknown team";
    if (primaryColor) {
        schoolLabel.style.color = `#${primaryColor}`;
    }
    label.append(schoolLabel);

    if (name) {
        const nameLabel = document.createElement("span");
        nameLabel.textContent = name;
        if (alternateColor) {
            nameLabel.style.color = `#${alternateColor}`;
        }
        label.append(" ", nameLabel);
    }

    return label;
}

function matchup(homeSchool, homeColor, homeRank, awaySchool, awayColor, awayRank) {
    const label = document.createElement("span");
    label.append(
        teamLabel(awaySchool, null, null, awayColor, null, awayRank),
        " @ ",
        teamLabel(homeSchool, null, null, homeColor, null, homeRank),
    );
    return label;
}

try {
    const response = await fetch("/landolytics/api/upcomingGames");

    if (!response.ok) {
        throw new Error(`Upcoming games request failed: HTTP ${response.status}`);
    }

    const data = await response.json();

    for (const game of data.games) {
        const row = document.createElement("tr");
        const values = [
            matchup(
                game.home_team_school_name,
                game.home_team_primary_color,
                game.home_team_rank,
                game.away_team_school_name,
                game.away_team_primary_color,
                game.away_team_rank,
            ),
            game.tipoff_time,
        ];

        for (const value of values) {
            const cell = document.createElement("td");
            cell.append(value || "-");
            row.append(cell);
        }

        gamesBody.append(row);
    }

    table.hidden = data.games.length === 0;
    status.textContent = data.games.length === 0
        ? "No upcoming games."
        : `${data.count} upcoming games.`;
} catch (error) {
    console.error("Unable to load upcoming games", error)
    status.textContent = "Unable to load upcoming games. Please reload to try again.";
}
