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

max_HP = skills.col_values(2)
max_HP = max_HP[1:]
current_HP = max_HP.copy()

# Discord connection
token = json.load(open('Credentials.json'))['discord_token']
discord_client = discord.Client()


# noinspection PyCompatibility
@discord_client.event
async def on_message(message):
    channel = message.channel
    command = message.content
    command = command.lower()
    members = message.guild.members

    global current_HP
    global max_HP

    roles = message.guild.roles
    for i in range(len(roles)):
        if 'Storyteller' == roles[i].name:
            storyteller_mention = roles[i].mention
            break

    # check if message author is a storyteller
    author_roles = message.author.roles
    author_roles = author_roles[1:]
    is_storyteller = False
    for i in range(len(author_roles)):
        if 'Storyteller' == author_roles[i].name:
            is_storyteller = True
            break

    def reply_check(m):
        return m.channel == channel and m.author == message.author

    def yes_no_storyteller_check(m):
        response_roles = m.author.roles
        response_roles = response_roles[1:]
        is_storyteller = False
        for i in range(len(response_roles)):
            if 'Storyteller' == response_roles[i].name:
                is_storyteller = True
                break
        return m.channel == channel and is_storyteller and (m.content.startswith('y') or m.content.startswith('n'))

    def yes_no_check(m):
        return m.channel == channel and (m.content.startswith('y') or m.content.startswith('n'))

    # Not checking self messages
    if message.author == discord_client.user:
        return

    # Basic ping-pong function
    if command.startswith('!ping'):
        await channel.send('Pong {0.author.mention}!'.format(message))

    # Check of a nickname in the list of members of the server.
    if command.startswith('!note'):
        query = 'Indystiru'
        for i in range(len(members)):
            if members[i].name == query:
                break
        mention = members[i].mention
        await channel.send(mention)

    # Full restoration of current HP
    if command.startswith('!restore'):
        if is_storyteller:
            current_HP = max_HP
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
            await channel.send('Please enter the skill level (1-5) you wish to roll:')
            skill_level = await discord_client.wait_for('message', timeout=10, check=reply_check)
            skill_level = int(skill_level.content)
            if 1 <= skill_level <= 5:
                author_dice_roll = random.randint(1, 100)
                author_bonus = 24 * (skill_level - 1)
                author_total = author_dice_roll + author_bonus
                await channel.send(
                    '{0.author.mention} ['.format(message) + str(author_dice_roll) + ']' + ' + ' +
                    str(author_bonus) + ' = ' + str(author_total))
            else:
                await channel.send("")
        else:
            try:  # find character name in the character names list
                character_row = character_names.index(character_query) + 2

            except ValueError:  # if not found
                await channel.send('Character not found, please try again!')
            else:  # initialisation of skill lists
                if player_names[character_row - 2] == message.author.name or is_storyteller:

                    skill_names = skills.row_values(1)
                    skill_names = skill_names[1:19]
                    skill_names = [name.lower() for name in skill_names]
                    targetable_skills = skill_names[1:4]
                    targeted_skills = skill_names[4:7]
                    targetable_skills.append(skill_names[7])
                    targetable_skills.append(skill_names[12])
                    targeted_skills.append(skill_names[8])
                    targeted_skills.append('endurance')
                    print(targetable_skills)
                    await channel.send('What skill would you like to roll?')

                    try:
                        skill_selection = await discord_client.wait_for('message', timeout=10, check=reply_check)
                    except asyncio.TimeoutError:
                        await channel.send('You have not entered a valid skill, please try to roll again!')
                    else:
                        skill_selection = skill_selection.content.lower()
                        if skill_selection in skill_names:

                            # author rolls
                            skill_column = skill_names.index(skill_selection) + 2
                            skill_level = skills.cell(character_row, skill_column).value
                            author_dice_roll = random.randint(1, 100)
                            author_bonus = 24 * (int(skill_level) - 1)
                            author_total = author_dice_roll + author_bonus

                            skill_success = False
                            has_target = False
                            if skill_selection in targetable_skills:

                                await  channel.send('Please select a target')

                                target = await discord_client.wait_for('message', timeout=10, check=reply_check)
                                target = target.content.lower()

                                if target == 'storyteller':

                                    await channel.send(
                                        '{0.author.mention} ['.format(message) + str(author_dice_roll) + ']' + ' + ' +
                                        str(author_bonus) + ' = ' + str(author_total))

                                    await channel.send(storyteller_mention + ' Was that check successful?')
                                    storyteller_answer = await discord_client.wait_for('message', timeout=60,
                                                                                       check=yes_no_storyteller_check)
                                    storyteller_answer = storyteller_answer.content.lower()
                                    skill_success = storyteller_answer.startswith('y')

                                elif target in character_names and \
                                        (target != character_query or skill_selection == 'biomedical'):

                                    has_target = True
                                    await channel.send(
                                        '{0.author.mention} ['.format(message) + str(author_dice_roll) + ']' + ' + ' +
                                        str(author_bonus) + ' = ' + str(author_total))
                                    target_name_index = character_names.index(target)

                                    if skill_selection == 'biomedical':
                                        # TODO: Implement healing
                                        pass
                                    else:
                                        matching_skill_index = targetable_skills.index(skill_selection)
                                        matching_skill_column = skill_names.index(
                                            targeted_skills[matching_skill_index]) + 2
                                        targeted_skill_level = skills.cell(target_name_index + 2,
                                                                           matching_skill_column).value
                                        target_dice_roll = random.randint(1, 100)
                                        target_bonus = 24 * (int(targeted_skill_level) - 1)
                                        target_total = target_dice_roll + target_bonus

                                        for i in range(len(members)):
                                            if members[i].name == player_names[target_name_index]:
                                                break
                                        mention = members[i].mention
                                        await channel.send(mention + ' [' + str(target_dice_roll) + ']' + ' + ' +
                                                           str(target_bonus) + ' = ' + str(target_total))

                                        while author_total == target_total:
                                            await channel.send('There is a tie, rerolling!')
                                            author_dice_roll = random.randint(1, 100)
                                            author_total = author_dice_roll + author_bonus
                                            target_dice_roll = random.randint(1, 100)
                                            target_total = target_dice_roll + target_bonus
                                            await channel.send(
                                                '{0.author.mention} ['.format(message) + str(
                                                    author_dice_roll) + ']' + ' + ' +
                                                str(author_bonus) + ' = ' + str(author_total))
                                            await channel.send(
                                                mention + ' [' + str(target_dice_roll) + ']' + ' + ' +
                                                str(target_bonus) + ' = ' + str(target_total))

                                        if matching_skill_index < 3:  # if matching skill is a defence
                                            if author_total > target_total:
                                                if current_HP[target_name_index] != '0':
                                                    temp = int(current_HP[target_name_index])
                                                    temp -= 1
                                                    current_HP[target_name_index] = str(temp)
                                                    skill_success = True
                                                    await channel.send(
                                                        '{0.author.mention} The attack was successful!'.format(message))
                                                    await channel.send(
                                                        mention + 'Your character lost 1 HP, current HP is: ' +
                                                        current_HP[target_name_index])
                                                else:
                                                    await channel.send(
                                                        '{0.author.mention} Your target cannot take more damage,'
                                                        ' they have reached 0 HP already!'.format(message))
                                                    return
                                            else:
                                                await channel.send(
                                                    '{0.author.mention} Your attack did not pass.'.format(message))
                                        else:  # if matching skill is perception
                                            if author_total > target_total:
                                                await channel.send(
                                                    '{0.author.mention} Success! You manage to remain unseen!'.format(
                                                        message))
                                                skill_success = True
                                            else:
                                                await channel.send(mention + 'Has spotted the stealther!')

                                else:
                                    await channel.send('Invalid target!')
                                    return
                            else:
                                await channel.send(
                                    '{0.author.mention} ['.format(message) + str(author_dice_roll) + ']' + ' + ' +
                                    str(author_bonus) + ' = ' + str(author_total))

                                await channel.send(storyteller_mention + ' Was that check successful?')
                                storyteller_answer = await discord_client.wait_for('message', timeout=60,
                                                                                   check=yes_no_storyteller_check)
                                storyteller_answer = storyteller_answer.content.lower()
                                skill_success = storyteller_answer.startswith('y')
                            if skill_success:
                                # TODO: Implement success XP
                                await channel.send('{0.author.mention} Your character gained 4 XP'.format(message))
                                if has_target:
                                    await channel.send(mention + 'Your character gained 1 XP')
                            else:
                                # TODO: Implement fail XP
                                await channel.send('{0.author.mention} Your character gained 1 XP'.format(message))
                                if has_target:
                                    await channel.send(mention + ' Your character gained 4 XP')
                        else:
                            await channel.send('Incorrect skill!')
                            return
                else:
                    await channel.send('You do not own this character, you can only roll your characters!')
                    return


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
