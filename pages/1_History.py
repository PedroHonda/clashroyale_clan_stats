'''
Create a graph of the clan's history
'''

# Import necessary libraries
import pandas as pd
import streamlit as st
from plotly import graph_objects as go

from modules.clashroyale_clan_rrlog import ClashRoyaleClanRRLog
from modules.clashroyale_clan_rrlog_db import ClashRoyaleClanRRLogDB

st.set_page_config(page_title="Clan History", layout="wide")

@st.cache_data
def get_clans_from_db():
    return ClashRoyaleClanRRLogDB.get_clans_from_db()

@st.cache_data
def get_clan_riverracelog(clan_id):
    crs = ClashRoyaleClanRRLog(clan_id)
    season_data = crs.get_clan_riverracelog()
    return season_data

@st.cache_data
def get_top_players(season_data, top=10):
    # Combine all fame data across seasons
    df_list = []
    for _, data in season_data.items():
        df_list.append(data["fame"])

    if not df_list:
        return []

    df_all = pd.concat(df_list, ignore_index=True)
    ranking = df_all.groupby('name')['total'].sum().sort_values(ascending=False)
    return ranking.head(top).index.tolist()

@st.cache_data
def get_all_players(season_data):
    players = set()
    for data in season_data.values():
        players.update(data["fame"]["name"].tolist())
    return sorted(list(players))

def create_performance_plot(season_data, players, title):
    fig = go.Figure()

    # Sort seasons numerically for the x-axis
    sorted_seasons = sorted(season_data.keys(), key=int)

    for player in players:
        xaxis, yaxis = [], []
        for season_id in sorted_seasons:
            data = season_data[season_id]
            dfr = data["fame"]
            player_stats = dfr[dfr["name"] == player]

            if not player_stats.empty:
                xaxis.append(season_id)
                yaxis.append(player_stats.total.values[0])

        if xaxis:
            fig.add_trace(go.Scatter(
                x=xaxis,
                y=yaxis,
                name=player,
                line_shape='hv',
                mode='lines+markers',
                marker=dict(size=8),
                hovertemplate="Season %{x}<br>Fame: %{y}<extra></extra>"
            ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=24)),
        xaxis_title="Season ID",
        yaxis_title="Fame",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=40, r=40, t=80, b=40),
        height=600
    )

    fig.update_xaxes(type='category')
    return fig

clans = get_clans_from_db()
clan_id = st.sidebar.selectbox("Enter clan ID:", clans)

if clan_id:
    season_data = get_clan_riverracelog(clan_id)
    all_players = get_all_players(season_data)

    st.title(f"Clan History: {clan_id}")

    # Section 1: Top Players
    st.header("🏆 Top Performers")
    top_n = st.slider("Select number of top players to display", 5, 20, 10)
    top_players = get_top_players(season_data, top=top_n)

    if top_players:
        fig_top = create_performance_plot(
            season_data,
            top_players,
            f"Top {top_n} Players - Fame over Seasons"
        )
        st.plotly_chart(fig_top, use_container_width=True)

    st.divider()

    # Section 2: Individual Player Analysis
    st.header("👤 Player Analysis")
    col1, col2 = st.columns([1, 3])

    with col1:
        selected_players = st.multiselect(
            "Select players to compare:", 
            options=all_players,
            default=all_players[:1] if all_players else []
        )

        if selected_players:
            # Show summary stats for selected players in a table
            stats = []
            for player in selected_players:
                player_fame = []
                for data in season_data.values():
                    p_data = data["fame"][data["fame"]["name"] == player]
                    if not p_data.empty:
                        player_fame.append(p_data.total.values[0])

                if player_fame:
                    stats.append({
                        "Player": player,
                        "Avg Fame": int(sum(player_fame) / len(player_fame)),
                        "Max Fame": max(player_fame),
                        "Seasons": len(player_fame)
                    })

            if stats:
                st.write("### Summary")
                st.table(pd.DataFrame(stats))

    with col2:
        if selected_players:
            fig_custom = create_performance_plot(
                season_data,
                selected_players,
                "Custom Player Comparison"
            )
            st.plotly_chart(fig_custom, use_container_width=True)
        else:
            st.info("Select one or more players from the sidebar to see their history.")

    st.divider()

    # Section 3: Player Efficiency
    st.header("🎯 Player Efficiency")
    st.info("Efficiency is calculated as the average fame per war, considering only seasons where the player used all 16 decks.")

    efficiency_data = []
    for player in all_players:
        player_efficiencies = []
        for season_id, data in season_data.items():
            fame_df = data["fame"]
            decks_df = data["decks_used"]

            p_fame = fame_df[fame_df["name"] == player]
            p_decks = decks_df[decks_df["name"] == player]

            if not p_fame.empty and not p_decks.empty:
                fame_total = p_fame.total.values[0]
                decks_total = p_decks.total.values[0]

                # Consider only seasons with 16 decks used
                if decks_total == 16:
                    # Average fame per war (4 wars per season usually)
                    efficiency_data.append({
                        "Player": player,
                        "Season": season_id,
                        "Avg Fame per War": fame_total / 4,
                        "Total Fame": fame_total
                    })

    if efficiency_data:
        eff_df = pd.DataFrame(efficiency_data)

        # Aggregate by player
        player_eff = eff_df.groupby("Player")["Avg Fame per War"].mean().reset_index()
        player_eff = player_eff.sort_values("Avg Fame per War", ascending=False)

        fig_eff = go.Figure()
        fig_eff.add_trace(go.Bar(
            x=player_eff["Player"],
            y=player_eff["Avg Fame per War"],
            marker_color='rgb(55, 83, 109)',
            hovertemplate="Player: %{x}<br>Avg Fame/War: %{y:.2f}<extra></extra>"
        ))

        fig_eff.update_layout(
            title="Average Efficiency (Only 16-deck Seasons)",
            xaxis_title="Player",
            yaxis_title="Avg Fame per War",
            template="plotly_white",
            height=500,
            margin=dict(l=40, r=40, t=80, b=40)
        )

        st.plotly_chart(fig_eff, use_container_width=True)

        with st.expander("View Raw Efficiency Data"):
            st.dataframe(eff_df.sort_values(["Avg Fame per War"], ascending=False))
    else:
        st.warning("No data found for players who used exactly 16 decks in a season.")
else:
    st.info("Please select a Clan ID from the sidebar to view the history.")
