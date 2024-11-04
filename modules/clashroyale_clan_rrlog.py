'''
Defining ClashRoyaleClanRRLog class
'''
import re
import requests

import pandas as pd

from modules.clashroyale_clan_rrlog_db import ClashRoyaleClanRRLogDB

class ClashRoyaleClanRRLog:
    '''
    Class for retrieving the RiverRaceLog for a given clan tag    
    '''
    API_KEY_PATH = r"clan_api_key"
    BASE_URL = 'https://api.clashroyale.com/v1'

    def __init__(self, clan_tag: str):
        '''
        Constructor for the ClashRoyaleClanRRLog class

        Parameters:
        clan_tag (str): The tag of the clan for which to retrieve the RiverRaceLog
        '''
        self.api_key = self._load_api_key()
        self.clan_tag = clan_tag.replace("#", "")

    def _load_api_key(self):
        '''
        Returns the API key's content
        '''
        try:
            with open(self.API_KEY_PATH, "r") as inp:
                key = inp.read()
        except FileNotFoundError:
            return ""
        return key

    def fetch_clan_riverracelog(self):
        '''
        Returns the RiverRaceLog for the given clan tag

        Returns:
        dict: The RiverRaceLog data
        '''
        headers = {
            # The API key is required to access the API
            'Authorization': f'Bearer {self.api_key}',
            # The API returns the data in JSON format
            'Accept': 'application/json'
        }

        # Fetch the war log for the clan
        url = f'{self.BASE_URL}/clans/%23{self.clan_tag}/riverracelog'
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            # The request was successful
            return response.json()
        # The request was not successful
        print(f"Failed to fetch data: {response.status_code} - {response.text}")
        return None

    def store_clan_riverracelog(self):
        '''
        Analyze the RiverRaceLog for the given clan tag and return a dictionary
        with the total fame earned by each player in each season for each section.

        Returns:
        dict: A dictionary with the total fame earned by each player in each
              season for each section. The structure is as follows:

              clan_stats[season_id][section_id][player_tag] = {
                  "name": player_name, 
                  "fame": fame, 
                  "decks_used": decks_used
              }
        '''
        # Fetch the RiverRaceLog for the given clan tag
        rrlog = self.fetch_clan_riverracelog()
        if not rrlog:
            return

        # Initialize the dictionary to store the clan stats
        clan_stats = {}

        # Iterate over the items in the RiverRaceLog
        for item in rrlog["items"]:
            # Extract the season ID and section ID from the item
            season_id = item["seasonId"]
            section_id = item["sectionIndex"]

            # Initialize the dictionary for the season
            if season_id not in clan_stats:
                clan_stats[season_id] = {"players": {}}

            # Iterate over the standings in the item
            for clan in item["standings"]:
                # Check if the clan is the one we are interested in
                if clan["clan"]["tag"] == f"#{self.clan_tag}":
                    # Iterate over the participants in the clan
                    for participant in clan["clan"]["participants"]:
                        # Extract the name, fame and decks used from the participant
                        player_tag = participant["tag"]

                        if player_tag not in clan_stats[season_id]["players"]:
                            # Initialize the player data
                            clan_stats[season_id]["players"][player_tag] = {
                                "name": participant["name"],
                                f"{section_id}_fame": 0,
                                f"{section_id}_decks_used": 0
                            }

                        if f"{section_id}_fame" not in clan_stats[season_id]["players"][player_tag]:
                            clan_stats[season_id]["players"][player_tag][
                                f"{section_id}_fame"] = 0
                            clan_stats[season_id]["players"][player_tag][
                                f"{section_id}_decks_used"] = 0

                        # Add the fame and decks used to the clan_data
                        clan_stats[season_id]["players"][player_tag][
                            f"{section_id}_fame"] += participant["fame"]
                        clan_stats[season_id]["players"][player_tag][
                            f"{section_id}_decks_used"] += participant["decksUsed"]

        # Clean special characters
        clean_clan_stats = ClashRoyaleClanRRLog.clean_special_characters(clan_stats)

        # Store in database
        crcs_db = ClashRoyaleClanRRLogDB(self.clan_tag)
        crcs_db.insert_clan_riverracelog(clean_clan_stats)

    def get_clan_riverracelog(self) -> dict:
        '''
        Returns the RiverRaceLog for the given clan tag

        This function reads the data from the MongoDB database and returns it
        as a dictionary with the season ID as the key and the season data as
        the value. The season data is a dictionary with the keys "fame" and
        "decks_used" and the values are pandas DataFrames sorted by the total
        fame and total decks used respectively.

        Returns:
        dict: The RiverRaceLog data
        '''
        def get_total_df(aux_dfr, flt):
            '''
            Sum all columns that match the given filter and return the result
            sorted by the total.

            Parameters:
            aux_dfr (pd.DataFrame): The DataFrame to be filtered and summed.
            flt (str): The regex pattern to use for filtering the columns.

            Returns:
            pd.DataFrame: The DataFrame with the columns filtered and summed,
            sorted by the total.
            '''
            new_df = aux_dfr.filter(regex=flt)
            columns_to_sum = [col for col in new_df.columns if col != "name"]
            new_df = new_df.copy()
            new_df["total"] = new_df[columns_to_sum].sum(axis=1)
            return new_df.sort_values(by='total', ascending=False)

        crcs_db = ClashRoyaleClanRRLogDB(self.clan_tag)
        all_dict = crcs_db.collection.find()
        all_df = {i["season_id"] : pd.DataFrame(i["players"]).transpose() for i in all_dict}

        season_data = {}
        for season_id, dfr in all_df.items():
            season_data[season_id] = {
                "fame": get_total_df(dfr, r"(\d_fame)|(name)"),
                "decks_used": get_total_df(dfr, r"(\d_decks_used)|(name)"),
            }

        return season_data

    @staticmethod
    def clean_special_characters(input_dict):
        '''
        Clean special characters from a string.
        '''
        def clean_string(string):
            '''
            Allow only alphanumeric characters and basic punctuation (you can customize this).
            '''
            return re.sub(r'[^a-zA-Z0-9 .,!?-]', '', string)

        def clean_dict(dictionary):
            '''
            Recursive function to traverse and clean all strings in the dictionary.
            '''
            for key, value in dictionary.items():
                if isinstance(value, dict):
                    # If value is a nested dictionary, recurse
                    clean_dict(value)
                elif isinstance(value, list):
                    for index, item in enumerate(value):
                        if isinstance(item, str):
                            # Clean strings in lists
                            value[index] = clean_string(item)
                        elif isinstance(item, dict):
                            # If item in list is a dict, recurse
                            clean_dict(item)
                elif isinstance(value, str):
                    # Clean string values
                    dictionary[key] = clean_string(value)

        clean_dict(input_dict)
        return input_dict
