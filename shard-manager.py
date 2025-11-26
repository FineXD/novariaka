import discord
from discord.ext import commands, tasks
import re
from datetime import datetime, timedelta
import json
import os
import asyncio


intents = discord.Intents.default()
intents.message_content = True
intents.members = True  
bot = commands.Bot(command_prefix='.', intents=intents)


bot.remove_command('help')


staff_shards = {}  
staff_list = set() 
log_channel_id = None  
bot_log_channel_id = None  
staff_update_channel_id = None  
weekly_start = None
stage_start = None
best_time_start = None
best_time_end = None
punishments = []  
staff_role_id = None  


DISCORD_STAFF_ROLES = [1186282691180642374, 1186309153854074951, 1186339787041419334] 
MINECRAFT_STAFF_ROLES = [1186276888759500890, 1186279568890409054, 1186309153854074951, 1186339787041419334]


EMOJI_SUCCESS = "✅"
EMOJI_ERROR = "❌"
EMOJI_REPORT = "📊"
EMOJI_TIME = "⏰"
EMOJI_STAFF = "📋"
EMOJI_HELP = "📜"
EMOJI_ROLE = "🛡️"


DATA_FILE = "bot_data.json"


def load_data():
    global staff_shards, staff_list, log_channel_id, bot_log_channel_id, staff_update_channel_id, weekly_start, stage_start, best_time_start, best_time_end, punishments, staff_role_id
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
            staff_shards = {k: int(v) for k, v in data.get('staff_shards', {}).items()}
            staff_list = set(data.get('staff_list', []))
            log_channel_id = data.get('log_channel_id')
            bot_log_channel_id = data.get('bot_log_channel_id')
            staff_update_channel_id = data.get('staff_update_channel_id')
            staff_role_id = data.get('staff_role_id')
            weekly_start = datetime.fromisoformat(data['weekly_start']) if data.get('weekly_start') else None
            stage_start = datetime.fromisoformat(data['stage_start']) if data.get('stage_start') else None
            best_time_start = datetime.fromisoformat(data['best_time_start']) if data.get('best_time_start') else None
            best_time_end = datetime.fromisoformat(data['best_time_end']) if data.get('best_time_end') else None
            punishments = [(datetime.fromisoformat(p[0]), p[1], p[2], p[3], int(p[4])) for p in data.get('punishments', [])]
            print("Data loaded successfully from bot_data.json")
        except Exception as e:
            print(f"Error loading data: {e}")


def save_data_to_file():
    data = {
        'staff_shards': staff_shards,
        'staff_list': list(staff_list),
        'log_channel_id': log_channel_id,
        'bot_log_channel_id': bot_log_channel_id,
        'staff_update_channel_id': staff_update_channel_id,
        'staff_role_id': staff_role_id,
        'weekly_start': weekly_start.isoformat() if weekly_start else None,
        'stage_start': stage_start.isoformat() if stage_start else None,
        'best_time_start': best_time_start.isoformat() if best_time_start else None,
        'best_time_end': best_time_end.isoformat() if best_time_end else None,
        'punishments': [(p[0].isoformat(), p[1], p[2], p[3], p[4]) for p in punishments]
    }
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        print("Data saved successfully to bot_data.json")
    except Exception as e:
        print(f"Error saving data: {e}")


@tasks.loop(seconds=10)
async def update_status():
    statuses = [
        discord.Activity(type=discord.ActivityType.watching, name=" Shards"),
        discord.Activity(type=discord.ActivityType.watching, name=f" {len(staff_list)} Staff")
    ]
    for status in statuses:
        await bot.change_presence(status=discord.Status.dnd, activity=status)
        await asyncio.sleep(10)


def check_staff_role():
    async def predicate(ctx):
        if staff_role_id is None or ctx.command.name in ['setstaffrole', 'weeklyreport', 'stagereport', 'stafflist']:
            return True
        return any(role.id == staff_role_id for role in ctx.author.roles)
    return commands.check(predicate)

@bot.event
async def on_ready():
    global log_channel_id, bot_log_channel_id
    print(f'{bot.user} is ready!')
   
    load_data()
   
    if not log_channel_id or not bot_log_channel_id:
        accessible_channels = []
        for guild in bot.guilds:
            for channel in guild.text_channels:
                permissions = channel.permissions_for(guild.me)
                if permissions.read_messages and permissions.send_messages:
                    accessible_channels.append(channel)
            if len(accessible_channels) >= 2:
                log_channel_id = accessible_channels[0].id
                bot_log_channel_id = accessible_channels[1].id
                embed = discord.Embed(
                    title=f"{EMOJI_SUCCESS} Log Channels Auto-Set",
                    description=f"Punishment log channel: {accessible_channels[0].mention}\nBot log channel: {accessible_channels[1].mention}",
                    color=discord.Color.green()
                )
                await accessible_channels[1].send(embed=embed)
                save_data_to_file()
                break
            elif len(accessible_channels) == 1:
                log_channel_id = accessible_channels[0].id
                bot_log_channel_id = accessible_channels[0].id
                embed = discord.Embed(
                    title=f"{EMOJI_SUCCESS} Log Channel Auto-Set",
                    description=f"Using {accessible_channels[0].mention} for both punishment and bot logs",
                    color=discord.Color.green()
                )
                await accessible_channels[0].send(embed=embed)
                save_data_to_file()
                break
            else:
                print("Insufficient accessible text channels found for logging!")
    
    update_status.start()

@bot.command(name='setstaffrole')
@check_staff_role()
async def set_staff_role(ctx, role_id: str):
    global staff_role_id
    try:
        role = await ctx.guild.fetch_role(int(role_id))
        if not role:
            embed = discord.Embed(
                title=f"{EMOJI_ERROR} Invalid Role",
                description="The provided ID does not belong to a valid role.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        staff_role_id = role.id
        embed = discord.Embed(
            title=f"{EMOJI_ROLE} Staff Role Set",
            description=f"Staff role set to {role.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        save_data_to_file()
    except (ValueError, discord.NotFound):
        embed = discord.Embed(
            title=f"{EMOJI_ERROR} Invalid Role ID",
            description="Please provide a valid role ID.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title=f"{EMOJI_ERROR} Permission Error",
            description="Bot lacks permission to access that role.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name='setstaffupdate')
@check_staff_role()
async def set_staff_update(ctx, channel_id: str):
    global staff_update_channel_id
    try:
        channel = await bot.fetch_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            embed = discord.Embed(
                title=f"{EMOJI_ERROR} Invalid Channel",
                description="The provided ID does not belong to a text channel.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        permissions = channel.permissions_for(ctx.guild.me)
        if not (permissions.read_messages and permissions.send_messages):
            embed = discord.Embed(
                title=f"{EMOJI_ERROR} Permission Error",
                description="Bot lacks permissions to read or send messages in that channel.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        staff_update_channel_id = channel.id
        embed = discord.Embed(
            title=f"{EMOJI_SUCCESS} Staff Update Channel Set",
            description=f"Staff update channel set to {channel.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        save_data_to_file()
    except (ValueError, discord.NotFound):
        embed = discord.Embed(
            title=f"{EMOJI_ERROR} Invalid Channel ID",
            description="Please provide a valid channel ID.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title=f"{EMOJI_ERROR} Permission Error",
            description="Bot lacks permission to access that channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name='help')
@check_staff_role()
async def custom_help(ctx):
    embed = discord.Embed(
        title=f"{EMOJI_HELP} Command List",
        description="Available commands and their functions:",
        color=discord.Color.green()
    )
    commands_list = [
        (".setstaffrole <role_id>", "Set the role that can access commands"),
        (".setchannellog <channel_id>", "Set the channel for reading punishment logs"),
        (".setbotlog <channel_id>", "Set the channel for bot's shard/punishment logs"),
        (".setstaffupdate <channel_id>", "Set the channel for staff update messages"),
        (".setstaff <name>", "Add a staff member by name"),
        (".removestaff <name>", "Remove a staff member by name"),
        (".stafflist", "Show all staff members and their shards (visible only to you)"),
        (".setweekly <date>", "Set weekly period start to date (YYYY-MM-DD)"),
        (".setstage <date>", "Set stage period start to date (YYYY-MM-DD)"),
        (".setbesttime <end_date>", "Set best time period to end on date (YYYY-MM-DD)"),
        (".unsetweekly", "Reset weekly period"),
        (".unsetstage", "Reset stage period"),
        (".unsetbesttime", "Reset best time period"),
        (".weeklyreport", "Show punishment stats for weekly period (visible only to you)"),
        (".stagereport", "Show punishment stats for stage period (visible only to you)")
    ]
    for cmd, desc in commands_list:
        embed.add_field(name=cmd, value=desc, inline=False)
    await ctx.send(embed=embed, ephemeral=True)

@bot.command(name='setchannellog')
@check_staff_role()
async def set_channel_log(ctx, channel_id: str):
    global log_channel_id
    try:
        channel = await bot.fetch_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            embed = discord.Embed(
                title=f"{EMOJI_ERROR} Invalid Channel",
                description="The provided ID does not belong to a text channel.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        permissions = channel.permissions_for(ctx.guild.me)
        if not (permissions.read_messages and permissions.send_messages):
            embed = discord.Embed(
                title=f"{EMOJI_ERROR} Permission Error",
                description="Bot lacks permissions to read or send messages in that channel.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        log_channel_id = channel.id
        embed = discord.Embed(
            title=f"{EMOJI_SUCCESS} Log Channel Set",
            description=f"Punishment log channel set to {channel.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        save_data_to_file()
    except (ValueError, discord.NotFound):
        embed = discord.Embed(
            title=f"{EMOJI_ERROR} Invalid Channel ID",
            description="Please provide a valid channel ID.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title=f"{EMOJI_ERROR} Permission Error",
            description="Bot lacks permission to access that channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name='setbotlog')
@check_staff_role()
async def set_bot_log(ctx, channel_id: str):
    global bot_log_channel_id
    try:
        channel = await bot.fetch_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            embed = discord.Embed(
                title=f"{EMOJI_ERROR} Invalid Channel",
                description="The provided ID does not belong to a text channel.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        permissions = channel.permissions_for(ctx.guild.me)
        if not (permissions.read_messages and permissions.send_messages):
            embed = discord.Embed(
                title=f"{EMOJI_ERROR} Permission Error",
                description="Bot lacks permissions to read or send messages in that channel.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        bot_log_channel_id = channel.id
        embed = discord.Embed(
            title=f"{EMOJI_SUCCESS} Bot Log Channel Set",
            description=f"Bot log channel set to {channel.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        save_data_to_file()
    except (ValueError, discord.NotFound):
        embed = discord.Embed(
            title=f"{EMOJI_ERROR} Invalid Channel ID",
            description="Please provide a valid channel ID.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title=f"{EMOJI_ERROR} Permission Error",
            description="Bot lacks permission to access that channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name='setstaff')
@check_staff_role()
async def set_staff(ctx, staff_name: str):
    staff_list.add(staff_name)
    embed = discord.Embed(
        title=f"{EMOJI_SUCCESS} Staff Added",
        description=f"{staff_name} has been added as staff.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)
    save_data_to_file()

@bot.command(name='removestaff')
@check_staff_role()
async def remove_staff(ctx, staff_name: str):
    if staff_name in staff_list:
        staff_list.remove(staff_name)
        embed = discord.Embed(
            title=f"{EMOJI_SUCCESS} Staff Removed",
            description=f"{staff_name} has been removed from staff.",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title=f"{EMOJI_ERROR} Error",
            description=f"{staff_name} is not a staff member.",
            color=discord.Color.red()
        )
    await ctx.send(embed=embed)
    save_data_to_file()

@bot.command(name='stafflist')
@check_staff_role()
async def staff_list_command(ctx):
    embed = discord.Embed(
        title=f"{EMOJI_STAFF} Staff List",
        description="List of all staff members and their total shards:",
        color=discord.Color.green()
    )
    if staff_list:
        for staff_name in sorted(staff_list):
            shards = staff_shards.get(staff_name, 0)
            embed.add_field(name=staff_name, value=f"{shards} shards", inline=True)
    else:
        embed.add_field(name="No Staff", value="No staff members registered.", inline=False)
    await ctx.send(embed=embed, ephemeral=True)

def parse_date(date_str):
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        return date
    except ValueError:
        return None

@bot.command(name='setweekly')
@check_staff_role()
async def set_weekly(ctx, date_str: str):
    global weekly_start
    date = parse_date(date_str)
    if date and date <= datetime.now():
        weekly_start = date
        embed = discord.Embed(
            title=f"{EMOJI_TIME} Weekly Period Set",
            description=f"Weekly period starts on {weekly_start.strftime('%Y-%m-%d')}",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title=f"{EMOJI_ERROR} Invalid Date",
            description="Please provide a valid date (YYYY-MM-DD) in the past or today.",
            color=discord.Color.red()
        )
    await ctx.send(embed=embed)
    save_data_to_file()

@bot.command(name='setstage')
@check_staff_role()
async def set_stage(ctx, date_str: str):
    global stage_start
    date = parse_date(date_str)
    if date and date <= datetime.now():
        stage_start = date
        embed = discord.Embed(
            title=f"{EMOJI_TIME} Stage Period Set",
            description=f"Stage period starts on {stage_start.strftime('%Y-%m-%d')}",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title=f"{EMOJI_ERROR} Invalid Date",
            description="Please provide a valid date (YYYY-MM-DD) in the past or today.",
            color=discord.Color.red()
        )
    await ctx.send(embed=embed)
    save_data_to_file()

@bot.command(name='setbesttime')
@check_staff_role()
async def set_best_time(ctx, end_date_str: str):
    global best_time_start, best_time_end
    end_date = parse_date(end_date_str)
    now = datetime.now()
    if end_date and end_date > now:
        best_time_start = now
        best_time_end = end_date
        embed = discord.Embed(
            title=f"{EMOJI_TIME} Best Time Set",
            description=f"Best time starts now and ends on {best_time_end.strftime('%Y-%m-%d')}",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title=f"{EMOJI_ERROR} Invalid End Date",
            description="Please provide a valid future date (YYYY-MM-DD).",
            color=discord.Color.red()
        )
    await ctx.send(embed=embed)
    save_data_to_file()

@bot.command(name='unsetweekly')
@check_staff_role()
async def unset_weekly(ctx):
    global weekly_start
    weekly_start = None
    embed = discord.Embed(
        title=f"{EMOJI_SUCCESS} Weekly Period Unset",
        description="Weekly period has been reset.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)
    save_data_to_file()

@bot.command(name='unsetstage')
@check_staff_role()
async def unset_stage(ctx):
    global stage_start
    stage_start = None
    embed = discord.Embed(
        title=f"{EMOJI_SUCCESS} Stage Period Unset",
        description="Stage period has been reset.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)
    save_data_to_file()

@bot.command(name='unsetbesttime')
@check_staff_role()
async def unset_best_time(ctx):
    global best_time_start, best_time_end
    best_time_start = None
    best_time_end = None
    embed = discord.Embed(
        title=f"{EMOJI_SUCCESS} Best Time Unset",
        description="Best time period has been reset.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)
    save_data_to_file()

@bot.command(name='weeklyreport')
@check_staff_role()
async def weekly_report(ctx):
    if not weekly_start:
        embed = discord.Embed(
            title=f"{EMOJI_ERROR} No Weekly Period",
            description="Weekly period is not set. Use .setweekly to set it.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return

    report = {}
    for timestamp, staff_name, action_type, _, _ in punishments:
        if timestamp >= weekly_start:
            if staff_name not in report:
                report[staff_name] = {'Ban': 0, 'Mute': 0, 'Shards': 0}
            report[staff_name][action_type] += 1
            points = 15 if action_type == 'Ban' else 20
            if best_time_start and best_time_end and best_time_start <= timestamp <= best_time_end:
                points *= 2
            report[staff_name]['Shards'] += points

    embed = discord.Embed(
        title=f"{EMOJI_REPORT} Weekly Punishment Report",
        description=f"From {weekly_start.strftime('%Y-%m-%d')} to now",
        color=discord.Color.green()
    )
    for staff_name, counts in sorted(report.items()):
        embed.add_field(
            name=staff_name,
            value=f"Bans: {counts['Ban']}\nMutes: {counts['Mute']}\nShards: {counts['Shards']}",
            inline=True
        )
    if not report:
        embed.add_field(name="No Data", value="No punishments recorded.", inline=False)
    await ctx.send(embed=embed, ephemeral=True)

@bot.command(name='stagereport')
@check_staff_role()
async def stage_report(ctx):
    if not stage_start:
        embed = discord.Embed(
            title=f"{EMOJI_ERROR} No Stage Period",
            description="Stage period is not set. Use .setstage to set it.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return

    report = {}
    for timestamp, staff_name, action_type, _, _ in punishments:
        if timestamp >= stage_start:
            if staff_name not in report:
                report[staff_name] = {'Ban': 0, 'Mute': 0, 'Shards': 0}
            report[staff_name][action_type] += 1
            points = 15 if action_type == 'Ban' else 20
            if best_time_start and best_time_end and best_time_start <= timestamp <= best_time_end:
                points *= 2
            report[staff_name]['Shards'] += points

    embed = discord.Embed(
        title=f"{EMOJI_REPORT} Stage Punishment Report",
        description=f"From {stage_start.strftime('%Y-%m-%d')} to now",
        color=discord.Color.green()
    )
    for staff_name, counts in sorted(report.items()):
        embed.add_field(
            name=staff_name,
            value=f"Bans: {counts['Ban']}\nMutes: {counts['Mute']}\nShards: {counts['Shards']}",
            inline=True
        )
    if not report:
        embed.add_field(name="No Data", value="No punishments recorded.", inline=False)
    await ctx.send(embed=embed, ephemeral=True)

def parse_log_message(content):
    target_match = re.search(r'Target\s*\n(.*?)(?=\n[A-Z]|$)', content, re.DOTALL)
    type_match = re.search(r'Type\s*\n(.*?)(?=\n[A-Z]|$)', content, re.DOTALL)
    issued_by_match = re.search(r'Issued By\s*\n(.*?)(?=\n[A-Z]|$)', content, re.DOTALL)
    
    if target_match and type_match and issued_by_match:
        return (
            target_match.group(1).strip(),
            type_match.group(1).strip(),
            issued_by_match.group(1).strip()
        )
    return None

def parse_staff_update_message(content):
    mention_match = re.search(r'Mention\s*:\s*<@!?(\d+)>', content)
    mode_match = re.search(r'Mode\s*:\s*\*\*(.*?)(?:\s*-.*)?\*\*', content)
    staff_match = re.search(r'Staff\s*:\s*(.*?)(?=\n|$)', content)
    
    if mention_match and mode_match and staff_match:
        return (
            int(mention_match.group(1)),  
            mode_match.group(1).strip(),  
            staff_match.group(1).strip() 
        )
    return None

@bot.event
async def on_message(message):
  
    if log_channel_id and message.channel.id == log_channel_id:
        parsed = parse_log_message(message.content)
        if parsed:
            target, action_type, staff_name = parsed
            if staff_name in staff_list and action_type in ['Ban', 'Mute']:
             
                points = 15 if action_type == 'Ban' else 20
                if best_time_start and best_time_end:
                    now = datetime.now()
                    if best_time_start <= now <= best_time_end:
                        points *= 2  
                
              
                if staff_name not in staff_shards:
                    staff_shards[staff_name] = 0
                staff_shards[staff_name] += points
                
             
                punishments.append((datetime.now(), staff_name, action_type, target, message.id))
                
          
                guild = message.guild
                link = f"https://discord.com/channels/{guild.id}/{message.channel.id}/{message.id}"
                
                
                embed = discord.Embed(
                    title=f"{EMOJI_SUCCESS} Punishment Logged",
                    description=f"Staff {staff_name} earned {points} shards!",
                    color=discord.Color.green()
                )
                embed.add_field(name="Action", value=action_type, inline=True)
                embed.add_field(name="Target", value=target, inline=True)
                embed.add_field(name="Total Shards", value=staff_shards[staff_name], inline=True)
                embed.add_field(name="Log", value=f"[View Log]({link})", inline=False)
                bot_log_channel = bot.get_channel(bot_log_channel_id)
                if bot_log_channel:
                    await bot_log_channel.send(embed=embed)
                save_data_to_file()

 
    if staff_update_channel_id and message.channel.id == staff_update_channel_id:
        parsed = parse_staff_update_message(message.content)
        if parsed:
            user_id, mode, staff_type = parsed
            try:
               
                try:
                    member = await message.guild.fetch_member(user_id)
                except discord.NotFound:
                  
                    member = discord.Object(id=user_id)
                
                if mode in ['Joined', 'ReJoin']:
                    roles_to_assign = (
                        DISCORD_STAFF_ROLES if staff_type == 'Discord' else
                        MINECRAFT_STAFF_ROLES if staff_type == 'Minecraft' else
                        []
                    )
                    if isinstance(member, discord.Member):
                        for role_id in roles_to_assign:
                            role = message.guild.get_role(role_id)
                            if role:
                                await member.add_roles(role, reason=f"Staff update: {mode} as {staff_type}")
                            else:
                                print(f"Role {role_id} not found for {mode} action")
                elif mode == 'Blacklist':
                    await message.guild.ban(member, reason="Staff update: Blacklisted")
                elif mode == 'Demote':
                    if isinstance(member, discord.Member):
                        await message.guild.kick(member, reason="Staff update: Demoted")
                    else:
                        print(f"Cannot kick {user_id}: User not in server")
            except discord.Forbidden:
                print(f"Permission error: Cannot perform action for user {user_id} (Mode: {mode})")
            except discord.HTTPException as e:
                print(f"HTTP error performing action for user {user_id} (Mode: {mode}): {e}")

    await bot.process_commands(message)


bot.run('MTM4NjY1NDEzMjU2MzIxNDQ4OA.GmpTZg.1GUta_wDAw63JRbVyyR4BFtfDTq6dqyRIbzv_g')