import asyncio
import json
import random
import time
import discord
import gspread
from discord.ext import tasks
from oauth2client.service_account import ServiceAccountCredentials

# Google Spreadsheet connection
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('Credentials.json', scope)
google_client = gspread.authorize(credentials)

spreadsheet_names = list()
spreadsheet_names.append('Rolling System')
spreadsheet = google_client.open(spreadsheet_names[0])
skills = spreadsheet.worksheet('Skills')
xp = spreadsheet.worksheet('XP')

# Discord connection
token = json.load(open('Credentials.json'))['discord_token']
discord_client = discord.Client()


@discord_client.event
async def on_message(message):
    channel = message.channel
    command = message.content
    command = command.lower()

    if message.author == discord_client.user:
        return

    if command.startswith('!ping'):
        await channel.send('Pong {0.author.mention}!'.format(message))

    # To be generalised later
    if command.startswith('!find '):
        name = message.content[6:]
        cell = skills.find(name)
        cell2 = xp.find(name)
        row_content = skills.row_values(cell.row)
        row_content2 = skills.row_values(cell2.row)
        if row_content == row_content2:
            await channel.send(row_content)

    if command.startswith('!roll '):
        character_names = skills.col_values(1)
        character_names = character_names[1:]
        character_names = [name.lower() for name in character_names]
        character_query = command[6:]

        try:
            character_row = character_names.index(character_query) + 2
        except ValueError:
            await channel.send('Character not found, please try again!')
        else:
            skill_names = skills.row_values(1)
            skill_names = skill_names[1:19]
            skill_names = [name.lower() for name in skill_names]
            await channel.send('What skill would you like to roll?')

            def check(m):
                return m.content.lower() in skill_names and m.channel == channel

            try:
                skill_selection = await discord_client.wait_for('message', timeout=10, check=check)
            except asyncio.TimeoutError:
                await channel.send('You have not entered a valid skill, please try to roll again!')
            else:
                skill_selection = skill_selection.content
                skill_column = skill_names.index(skill_selection.lower()) + 2
                skill_level = skills.cell(character_row, skill_column).value
                dice_roll = random.randint(1, 100)
                bonus = 24 * (int(skill_level) - 1)
                total = dice_roll + bonus
                await channel.send('[' + str(dice_roll) + ']' + ' + ' + str(bonus) + ' = ' + str(total))


@discord_client.event
async def on_ready():
    print('Logged in as')
    print(discord_client.user.name)
    print(discord_client.user.id)
    print('------')
    google_login.start()


@tasks.loop(minutes=60)
async def google_login():
    print("Relogging", time.asctime())
    google_client.login()


discord_client.run(token)
