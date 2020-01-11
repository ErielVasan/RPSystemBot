import gspread
from oauth2client.service_account import ServiceAccountCredentials
import discord
import json

# Google Spreadsheet connection
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("Credentials.json", scope)
google_client = gspread.authorize(credentials)

spreadsheet_names = list()
spreadsheet_names.append("Rolling System")
spreadsheet = google_client.open(spreadsheet_names[0])
skills = spreadsheet.worksheet("Skills")
xp = spreadsheet.worksheet("XP")


# Discord connection
token = json.load(open("Credentials.json"))["discord_token"]
client = discord.Client()


@client.event
async def on_message(message):

    channel = message.channel
    if message.author == client.user:
        return

    if message.content.startswith('!ping'):
        msg = 'Pong {0.author.mention} '.format(message)
        await channel.send(msg)

    if message.content.startswith('!find '):
        name = message.content[6:]
        cell = skills.find(name)
        cell2 = xp.find(name)
        row_content = skills.row_values(cell.row)
        row_content2 = skills.row_values(cell2.row)
        if row_content == row_content2:
            await channel.send(row_content)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

client.run(token)