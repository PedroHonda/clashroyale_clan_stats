'''
Create a graph of the clan's history
'''

# Import necessary libraries
import pandas as pd
import numpy as np
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

    df_all = pd.concat(df_list)
    # Group by index (player tag)
    ranking = df_all.groupby(df_all.index)['total'].sum().sort_values(ascending=False)
    return ranking.head(top).index.tolist()

@st.cache_data
def get_all_players(season_data):
    # Mapping of tag to the latest name found
    player_map = {}
    # Sort seasons to get the latest name
    sorted_seasons = sorted(season_data.keys(), key=int)
    for season_id in sorted_seasons:
        fame_df = season_data[season_id]["fame"]
        for tag, row in fame_df.iterrows():
            player_map[tag] = row["name"]
    return player_map

def create_performance_plot(season_data, player_tags, player_map, title):
    fig = go.Figure()

    # Sort seasons numerically for the x-axis
    sorted_seasons = sorted(season_data.keys(), key=int)

    for tag in player_tags:
        xaxis, yaxis = [], []
        player_name = player_map.get(tag, tag)
        for season_id in sorted_seasons:
            data = season_data[season_id]
            dfr = data["fame"]

            if tag in dfr.index:
                player_stats = dfr.loc[tag]
                xaxis.append(season_id)
                yaxis.append(player_stats.total)

        if xaxis:
            fig.add_trace(go.Scatter(
                x=xaxis,
                y=yaxis,
                name=player_name,
                line_shape='hv',
                mode='lines+markers',
                marker=dict(size=8),
                hovertemplate=f"Player: {player_name}<br>Season %{{x}}<br>Fame: %{{y}}<extra></extra>"
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
    # all_players is a dict: {tag: latest_name}
    all_players_map = get_all_players(season_data)
    all_player_tags = list(all_players_map.keys())

    st.title(f"Clan History: {clan_id}")

    # Section 1: Top Players
    st.header("🏆 Top Performers")
    top_n = st.slider("Select number of top players to display", 5, 20, 10)
    top_player_tags = get_top_players(season_data, top=top_n)

    if top_player_tags:
        fig_top = create_performance_plot(
            season_data,
            top_player_tags,
            all_players_map,
            f"Top {top_n} Players - Fame over Seasons"
        )
        st.plotly_chart(fig_top, use_container_width=True)

    st.divider()

    # Section 2: Individual Player Analysis
    st.header("👤 Player Analysis")
    col1, col2 = st.columns([1, 3])

    with col1:
        # Show names in multiselect but work with tags
        selected_player_tags = st.multiselect(
            "Select players to compare:",
            options=all_player_tags,
            format_func=lambda x: all_players_map.get(x, x),
            default=all_player_tags[:1] if all_player_tags else []
        )

        if selected_player_tags:
            # Show summary stats for selected players in a table
            stats = []
            for tag in selected_player_tags:
                player_name = all_players_map.get(tag, tag)
                player_fame = []
                for data in season_data.values():
                    fame_df = data["fame"]
                    if tag in fame_df.index:
                        player_fame.append(fame_df.loc[tag, "total"])

                if player_fame:
                    stats.append({
                        "Player": player_name,
                        "Avg Fame": int(sum(player_fame) / len(player_fame)),
                        "Max Fame": max(player_fame),
                        "Seasons": len(player_fame)
                    })

            if stats:
                st.write("### Summary")
                st.table(pd.DataFrame(stats))

    with col2:
        if selected_player_tags:
            fig_custom = create_performance_plot(
                season_data,
                selected_player_tags,
                all_players_map,
                "Custom Player Comparison"
            )
            st.plotly_chart(fig_custom, use_container_width=True)
        else:
            st.info("Select one or more players from the sidebar to see their history.")

    st.divider()

    # Section 3: All-time Accumulated Points
    st.header("📈 All-time Accumulated Points")
    st.info("Total fame accumulated across all recorded seasons.")

    accumulated_data = []
    for tag, name in all_players_map.items():
        player_fame = []
        for data in season_data.values():
            fame_df = data["fame"]
            if tag in fame_df.index:
                player_fame.append(fame_df.loc[tag, "total"])

        if player_fame:
            accumulated_data.append({
                "Tag": tag,
                "Player": name,
                "Total Fame": sum(player_fame),
                "Average Fame": int(sum(player_fame) / len(player_fame)),
                "Seasons": len(player_fame)
            })

    if accumulated_data:
        acc_df = pd.DataFrame(accumulated_data).sort_values("Total Fame", ascending=False)

        # Display as a bar chart
        fig_acc = go.Figure()
        fig_acc.add_trace(go.Bar(
            x=acc_df["Player"],
            y=acc_df["Total Fame"],
            customdata=acc_df["Tag"],
            marker_color='rgb(26, 118, 255)',
            hovertemplate="Player: %{x}<br>Tag: %{customdata}<br>Total Fame: %{y}<extra></extra>"
        ))

        fig_acc.update_layout(
            title="Total Accumulated Fame by Player",
            xaxis_title="Player",
            yaxis_title="Total Fame",
            template="plotly_white",
            height=500,
            margin=dict(l=40, r=40, t=80, b=40)
        )

        st.plotly_chart(fig_acc, use_container_width=True)

        # Display the table
        st.dataframe(
            acc_df,
            column_config={
                "Total Fame": st.column_config.NumberColumn(format="%d"),
                "Average Fame": st.column_config.NumberColumn(format="%d"),
                "Seasons": st.column_config.NumberColumn(format="%d"),
            },
            hide_index=True,
            use_container_width=True
        )

    st.divider()

    # Section 4: Player Efficiency
    st.header("🎯 Player Efficiency")
    st.info("Efficiency is calculated as the average fame per war, considering only seasons where the player used all available decks (16 per week).")

    efficiency_data = []
    for tag, name in all_players_map.items():
        for season_id, data in season_data.items():
            fame_df = data["fame"]
            decks_df = data["decks_used"]

            if tag in fame_df.index and tag in decks_df.index:
                fame_total = fame_df.loc[tag, "total"]
                decks_total = decks_df.loc[tag, "total"]

                # Dynamically determine the number of weeks (sections) in this season
                # Columns in decks_df are: name, total, and N_decks_used
                week_cols = [col for col in decks_df.columns if col not in ["name", "total"]]
                num_weeks = len(week_cols)
                expected_decks = num_weeks * 16

                # Consider only seasons where the player participated fully (16 decks per week)
                if num_weeks > 0 and decks_total == expected_decks:
                    efficiency_data.append({
                        "Tag": tag,
                        "Player": name,
                        "Season": season_id,
                        "Fame (Season)": fame_total,
                        "Num Weeks": num_weeks,
                        "Avg Fame per War": fame_total / num_weeks
                    })

    if efficiency_data:
        eff_df = pd.DataFrame(efficiency_data)

        # Aggregate by player: calculate total efficiency (Total Valid Fame / Total Valid Weeks)
        player_eff_stats = []
        for tag, name in all_players_map.items():
            p_data = eff_df[eff_df["Tag"] == tag]
            if not p_data.empty:
                total_valid_fame = p_data["Fame (Season)"].sum()
                total_valid_weeks = p_data["Num Weeks"].sum()
                num_valid_seasons = len(p_data)

                # Efficiency is total points / total wars (weeks)
                avg_fame_per_war = total_valid_fame / total_valid_weeks

                player_eff_stats.append({
                    "Tag": tag,
                    "Player": name,
                    "Avg Fame per War": avg_fame_per_war,
                    "Valid Seasons": num_valid_seasons,
                    "Total Valid Fame": total_valid_fame
                })

        player_eff = pd.DataFrame(player_eff_stats).sort_values("Avg Fame per War", ascending=False)

        fig_eff = go.Figure()
        fig_eff.add_trace(go.Bar(
            x=player_eff["Player"],
            y=player_eff["Avg Fame per War"],
            marker_color='rgb(55, 83, 109)',
            customdata=np.stack((player_eff["Valid Seasons"], player_eff["Tag"]), axis=-1),
            hovertemplate="Player: %{x}<br>Tag: %{customdata[1]}<br>Avg Fame/War: %{y:.2f}<br>Valid Seasons: %{customdata[0]}<extra></extra>"
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
            st.dataframe(
                eff_df.sort_values(["Avg Fame per War"], ascending=False),
                column_config={
                    "Avg Fame per War": st.column_config.NumberColumn(format="%.2f"),
                },
                hide_index=True,
                use_container_width=True
            )
    else:
        st.warning("No data found for players who used exactly 16 decks in a season.")
else:
    st.info("Please select a Clan ID from the sidebar to view the history.")
