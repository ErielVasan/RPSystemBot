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
xp_active = False

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
    global xp_active

    max_HP = skills.col_values(2)
    max_HP = max_HP[1:]

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

    # XP mode on or off
    if command.startswith('!xp'):
        if is_storyteller:
            if xp_active:
                activity = 'on'
                opposite_activity = 'off'
            else:
                activity = 'off'
                opposite_activity = 'on'
            await channel.send('XP gains are currently turned ' + activity + '. Do you want to turn them ' + opposite_activity + '?')
            answer = await discord_client.wait_for('message', timeout=10, check=yes_no_storyteller_check)
            answer = answer.content.lower()
            if answer.startswith('y'):
                xp_active = not xp_active
                await channel.send('XP gains have been turned ' + opposite_activity + '!')
            else:
                await channel.send('XP gains will remain turned ' + activity + '!')
        else:
            await channel.send("Only storytellers have access to this command!")

    # Full restoration of current HP
    if command.startswith('!restore'):
        if is_storyteller:
            current_HP = max_HP
            await channel.send('HP has been restored for all characters')
        else:
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
                await channel.send("You can only roll skills from 1-5!")
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
                                    is_biomedical = False
                                    await channel.send(
                                        '{0.author.mention} ['.format(message) + str(author_dice_roll) + ']' + ' + ' +
                                        str(author_bonus) + ' = ' + str(author_total))
                                    target_name_index = character_names.index(target)
                                    for i in range(len(members)):
                                        if members[i].name == player_names[target_name_index]:
                                            break
                                    mention = members[i].mention
                                    if skill_selection == 'biomedical':
                                        is_biomedical = True

                                        if int(current_HP[target_name_index]) != int(max_HP[target_name_index]):
                                            target_dice_roll = random.randint(1, 100)
                                            target_bonus = 24 * (int(current_HP[target_name_index]) - 1)
                                            target_total = target_dice_roll + target_bonus

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

                                            if author_total > target_total:
                                                temp = int(current_HP[target_name_index])
                                                temp += 1
                                                current_HP[target_name_index] = str(temp)
                                                skill_success = True
                                                await channel.send(
                                                    '{0.author.mention} You managed to restore 1 HP!'.format(message))
                                                await channel.send(
                                                    mention + 'Your character gained 1 HP, current HP is: ' +
                                                    current_HP[target_name_index])
                                            else:
                                                await channel.send('{0.author.mention} Your healing attempt was not '
                                                                   'successful!'.format(message))

                                        else:
                                            await channel.send(
                                                '{0.author.mention} Your target is at maximum health and cannot be '
                                                'healed further!'.format(message))
                                            return

                                    else:
                                        matching_skill_index = targetable_skills.index(skill_selection)
                                        matching_skill_column = skill_names.index(
                                            targeted_skills[matching_skill_index]) + 2
                                        targeted_skill_level = skills.cell(target_name_index + 2,
                                                                           matching_skill_column).value
                                        target_dice_roll = random.randint(1, 100)
                                        target_bonus = 24 * (int(targeted_skill_level) - 1)
                                        target_total = target_dice_roll + target_bonus

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

                            if xp_active:
                                author_xp = xp.cell(character_row, skill_column - 1).value
                                author_xp = int(author_xp)
                                author_powerlevel = skills.cell(character_row, 20).value
                                author_powerlevel = int(author_powerlevel)
                                if skill_success:
                                    if author_xp < 480 and author_powerlevel < 34:
                                        if author_xp > 476:
                                            author_xp = 480
                                        else:
                                            author_xp += 4
                                        xp.update_cell(character_row, skill_column - 1, author_xp)
                                        await channel.send('{0.author.mention} Your character gained 4 XP'.format(message))
                                    else:
                                        await channel.send(
                                            '{0.author.mention} Your character cannot get more XP'.format(message))
                                    if has_target and not is_biomedical:
                                        target_xp = xp.cell(target_name_index + 2, matching_skill_column - 1).value
                                        target_xp = int(target_xp)
                                        target_powerlevel = skills.cell(target_name_index + 2, 20).value
                                        target_powerlevel = int(target_powerlevel)
                                        if target_powerlevel < 480 or target_powerlevel < 34:
                                            target_xp += 1
                                            xp.update_cell(target_name_index + 2, matching_skill_column - 1, target_xp)
                                            await channel.send(mention + 'Your character gained 1 XP')
                                        else:
                                            await channel.send(mention + 'Your character cannot get more XP')
                                else:
                                    if author_xp < 480 and author_powerlevel < 34:
                                        author_xp += 1
                                        xp.update_cell(character_row, skill_column - 1, author_xp)
                                        await channel.send('{0.author.mention} Your character gained 1 XP'.format(message))
                                    else:
                                        await channel.send(
                                            '{0.author.mention} Your character cannot get more XP'.format(message))
                                    if has_target and not is_biomedical:
                                        target_xp = xp.cell(target_name_index + 2, matching_skill_column - 1).value
                                        target_xp = int(target_xp)
                                        target_powerlevel = skills.cell(target_name_index + 2, 20).value
                                        target_powerlevel = int(target_powerlevel)
                                        if target_powerlevel < 480 or target_powerlevel < 34:
                                            if target_xp > 476:
                                                target_xp = 480
                                            else:
                                                target_xp += 4
                                            xp.update_cell(target_name_index + 2, matching_skill_column - 1, target_xp)
                                            await channel.send(mention + 'Your character gained 4 XP')
                                        else:
                                            await channel.send(mention + 'Your character cannot get more XP')
                            else:
                                await channel.send('No XP were given because XP gains are turned off.')
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
