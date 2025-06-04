# Import necessary libraries
import streamlit as st

from modules.clashroyale_clan_rrlog import ClashRoyaleClanRRLog
from modules.clashroyale_clan_rrlog_db import ClashRoyaleClanRRLogDB

st.set_page_config(layout="wide")

st.title("Clash Royale Clan Stats")

@st.cache_data
def get_clans_from_db():
    return ClashRoyaleClanRRLogDB.get_clans_from_db()

@st.cache_data
def get_clan_riverracelog(clan_id):
    crs = ClashRoyaleClanRRLog(clan_id)
    season_data = crs.get_clan_riverracelog()
    return season_data

clans = get_clans_from_db()
clan_id = st.sidebar.selectbox("Enter clan ID:", clans)

if clan_id:
    season_data = get_clan_riverracelog(clan_id)

    season_id = st.sidebar.selectbox("Select a season:", sorted(season_data.keys(), key=int, reverse=True))
    if st.sidebar.button("Update", type="primary"):
        crs = ClashRoyaleClanRRLog(clan_id)
        crs.store_clan_riverracelog()
        st.sidebar.write("Updated!")

    fame = season_data[season_id]["fame"]
    decks = season_data[season_id]["decks_used"]

    st.header(f"Clan ID {clan_id} - Season {season_id}")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Fame")
        st.dataframe(fame)

    with col2:
        st.subheader("Decks Used")
        st.dataframe(decks)
