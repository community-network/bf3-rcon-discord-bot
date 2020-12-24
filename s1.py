import asyncio
import sys
import rconbf3
import discord

"""bf3 rcon version"""
# RCON_CONFIG
IP = ""
PORT = 47200
PASSWORD = ""
# DISCORD_CONFIG
BOT_TOKEN = ""  # https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token
 
#bf3 map shortname to readable name dict
bf3maps = {'MP_001': 'Grand Bazaar', 'MP_003': 'Tehran Highway', 'MP_007': 'Caspian Border', 'MP_011': 'Seine Crossing', 'MP_012': 'Operation Firestorm', 'MP_013': 'Damavand Peak ', 'MP_017': 'Noshahr Canals', 'MP_018': 'Kharg Island', 'MP_Subway': 'Operation Métro', 'XP1_001': 'Strike at Karkand', 'XP1_002': 'Gulf of Oman', 'XP1_003': 'Sharqi Peninsula', 'XP1_004': 'Wake Island', 'XP2_Factory': 'Scrapmetal', 'XP2_Office': 'Operation 925', 'XP2_Palace': 'Donya Fortress', 'XP2_Skybar': 'Ziba Tower', 'XP3_Alborz': 'Alborz Mountains', 'XP3_Desert': 'Bandar Desert', 'XP3_Shield': 'Armored Shield', 'XP3_Valley': 'Death Valley', 'XP4_FD': 'Markaz Monolith', 'XP4_Parl': 'Azadi Palace', 'XP4_Quake': 'Epicenter', 'XP4_Rubble': 'Talah Market', 'XP5_001': 'Operation Riverside', 'XP5_002': 'Nebandan Flats', 'XP5_003': 'Kiasar Railroad', 'XP5_004': 'Sabalan Pipeline'}

class LivePlayercountBot(discord.Client):
    """Discord bot to display the Bf3 playercount in the bot status"""
 
    async def on_ready(self):
        print(f"Logged on as {self.user}\n" f"Started monitoring server {IP}")
        status = ""
        connection = rconbf3.connect(IP, PORT)
        rconbf3.start_update(connection)
        result = rconbf3.authenticate(connection, PASSWORD)
        if result and result == ["OK"]:
            while True:
                try:
                    newstatus = await get_playercount(connection)
                    if newstatus != status:  # avoid spam to the discord API
                        await self.change_presence(activity=discord.Game(newstatus))
                        status = newstatus
                except:
                    pass
                # amount of time between updates
                await asyncio.sleep(120)
 
async def get_playercount(connection):
    try:                    # use serverInfo command of rcon command list
        info = rconbf3.invoke(connection, "serverInfo")
        #ARR: 2 == playermount, 3 -- maxplayers, 5 == mapname short version
        return f"{info[2]}/{info[3]} - {bf3maps[info[5]]}"  # discord status message
    except Exception as e:
        print(f"Error getting data from the battlefield 3 server: {e}") 
 
if __name__ == "__main__":
    assert sys.version_info >= (3, 7), "Script requires Python 3.7+"
    assert BOT_TOKEN and IP and PORT and PASSWORD, "Config is empty, pls fix"
    print("Initiating bot")
    LivePlayercountBot().run(BOT_TOKEN)