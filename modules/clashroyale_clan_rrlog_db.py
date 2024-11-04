'''
MongoDB class for storing clan stats in a MongoDB database
'''
import os
from dotenv import load_dotenv
import pymongo


class ClashRoyaleClanRRLogDB:
    '''
    MongoDB class for storing clan riverrace log in a MongoDB database
    '''
    def __init__(self, clan_tag):
        '''
        Constructor for the ClashRoyaleClanRRLogDB class
        '''
        load_dotenv()
        self.clan_tag = clan_tag.replace('#', '')
        # Change to MONGODB_LOCAL for local database
        self.client = pymongo.MongoClient(os.getenv('MONGODB_CRS'))
        self.db = self.client["clashroyale_clan_stats"]
        self.collection = self.db[f"#{self.clan_tag}"]

    def insert_clan_riverracelog(self, riverracelog_data: dict) -> None:
        '''
        Insert the RiverRaceLog for the given clan tag into the database

        Parameters:
        riverracelog_data (dict): The RiverRaceLog data
        '''
        # Iterate over the seasons in the RiverRaceLog data
        for season_id, season_data in riverracelog_data.items():
            # Find the existing document for the season in the collection
            document = self.collection.find_one({"season_id": season_id})

            # If the document exists, update the players in the document
            if document:
                # Iterate over the players in the season data
                for player_tag, player_data in season_data["players"].items():
                    # If the player exists in the document, update the player
                    if player_tag in document["players"]:
                        # Iterate over the keys in the player data
                        for key, value in document["players"][player_tag].items():
                            # If the key does not exist in the player data, add it
                            if key not in player_data:
                                player_data[key] = value
                # Replace the document with the updated data
                self.collection.replace_one({"_id": document["_id"]}, {"season_id": season_id, **season_data})
            # If the document does not exist, insert a new document
            else:
                # Insert the season data into the collection
                self.collection.insert_one({"season_id": season_id, **season_data})

    def get_clan_riverracelog_season(self, season_id:int):
        '''
        Retrieve the RiverRaceLog for a specific season from the database.

        Parameters:
        season_id (int): The ID of the season for which to retrieve the RiverRaceLog.

        Returns:
        dict: The document containing the RiverRaceLog data for the specified season, or None if not found.
        '''
        # Query the collection to find the document with the given season_id
        return self.collection.find_one({"season_id": season_id})

    @staticmethod
    def get_clans_from_db() -> list:
        '''
        Retrieve all the clans from the database.

        Returns:
        list: A list containing all the clans from the database.
        '''
        client = pymongo.MongoClient('mongodb://localhost:27017/')
        db = client['clashroyale_clan_stats']
        return db.list_collection_names()
