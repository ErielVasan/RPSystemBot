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

currentHP = skills.col_values(2)
currentHP = currentHP[1:]

# Discord connection
token = json.load(open('Credentials.json'))['discord_token']
discord_client = discord.Client()
@discord_client.event
async def on_message(message):
    channel = message.channel
    command = message.content
    command = command.lower()
    members = message.guild.members
    global currentHP

    # check if message author is a storyteller
    roles = message.author.roles
    roles = roles[1:]
    is_storyteller = False
    for i in range(len(roles)):
        if 'Storyteller' == roles[i].name:
            is_storyteller = True
            break

    # Not checking self messages
    if message.author == discord_client.user:
        return

    # Basic ping-pong function
    if command.startswith('!ping'):
        await channel.send('Pong {0.author.mention}!'.format(message))

    # Check of a nickname in the list of members of the server.
    if command.startswith('!note'):
        print(message.guild.roles)

    # Full restoration of current HP
    if command.startswith('!restore'):
        if is_storyteller:
            currentHP = skills.col_values(2)
            currentHP = currentHP[1:]
            await channel.send('HP has been restored for all characters')
        if not is_storyteller:
            await channel.send("Only storytellers have access to this command!")

    # Main Rolling Function
    if command.startswith('!roll '):
        character_names = skills.col_values(1)
        character_names = character_names[1:]
        character_names = [name.lower() for name in character_names]
        player_names = skills.col_values(21)
        player_names = player_names[1:]
        character_query = command[6:]

        if character_query == 'storyteller' and is_storyteller:
            # TODO: Implement the storyteller rolls (simple dice 1-5 bonus)
            await channel.send('This will be the storyteller only roll')
        else:
            try:  # find character name in the character names list
                character_row = character_names.index(character_query) + 2

            except ValueError:  # if not found
                await channel.send('Character not found, please try again!')
            else:  # initialisation of skill lists
                if player_names[character_row - 2] == message.author.display_name or is_storyteller:

                    skill_names = skills.row_values(1)
                    skill_names = skill_names[1:19]
                    skill_names = [name.lower() for name in skill_names]
                    targetable_skills = skill_names[1:4]
                    targeted_skills = skill_names[4:7]
                    targetable_skills.append(skill_names[7])
                    targetable_skills.append(skill_names[12])
                    targeted_skills.append(skill_names[8])
                    print(targetable_skills)
                    await channel.send('What skill would you like to roll?')

                    def reply_check(m):
                        return m.channel == channel and m.author == message.author

                    try:
                        skill_selection = await discord_client.wait_for('message', timeout=10, check=reply_check)
                    except asyncio.TimeoutError:
                        await channel.send('You have not entered a valid skill, please try to roll again!')
                    else:
                        skill_selection = skill_selection.content.lower()
                        if skill_selection in skill_names:
                            skill_column = skill_names.index(skill_selection) + 2
                            skill_level = skills.cell(character_row, skill_column).value
                            author_dice_roll = random.randint(1, 100)
                            author_bonus = 24 * (int(skill_level) - 1)
                            author_total = author_dice_roll + author_bonus
                            if skill_selection in targetable_skills:
                                await  channel.send('Please select a target')

                                target = await discord_client.wait_for('message', timeout=10, check=reply_check)
                                target = target.content.lower()

                                if target == 'storyteller':
                                    # TODO: Implement storyteller determining the outcome
                                    await channel.send(
                                        '{0.author.mention} ['.format(message) + str(author_dice_roll) + ']' + ' + ' +
                                        str(author_bonus) + ' = ' + str(author_total))

                                    await channel.send('To ask Storyteller if the player is successful.')
                                elif target in character_names:
                                    # TODO: Implement opposing rolls
                                    await channel.send(
                                        '{0.author.mention} ['.format(message) + str(author_dice_roll) + ']' + ' + ' +
                                        str(author_bonus) + ' = ' + str(author_total))
                                    await channel.send('Opposing roll here.')
                                else:
                                    await channel.send('Invalid Target!')
                            else:
                                # TODO: Same as if the target was Storyteller
                                await channel.send(
                                    '{0.author.mention} ['.format(message) + str(author_dice_roll) + ']' + ' + ' +
                                    str(author_bonus) + ' = ' + str(author_total))
                                await channel.send('To ask Storyteller if the player is successful.')
                        else:
                            await channel.send('Incorrect skill!')
                else:
                    await channel.send('You do not own this character, you can only roll your characters!')


@discord_client.event
async def on_ready():
    print('Logged in as')
    print(discord_client.user.name)
    print(discord_client.user.id)
    print('------')
    google_login.start()


@tasks.loop(minutes=30)
async def google_login():
    print("Relogging", time.asctime())
    google_client.login()


discord_client.run(token)
