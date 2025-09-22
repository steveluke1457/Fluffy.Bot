import discord
from discord.ext import tasks
from discord import app_commands
from datetime import datetime
import asyncio
import json
import os

OWNER_ID = 1301533813381402706  # Your Discord ID
TOKEN = "MTQxOTcwMzQzMDc3OTM3NTcyOA.Gb7rC-._93rTKgD64kArxDuw5pMJd53Oc9K9dqE8tVCHs"
SCHEDULE_FILE = "schedules.json"

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# Load schedules
if os.path.exists(SCHEDULE_FILE):
    with open(SCHEDULE_FILE, "r") as f:
        schedules = json.load(f)
else:
    schedules = []

def save_schedules():
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(schedules, f, indent=4)

async def send_scheduled_message(schedule):
    now = datetime.now()
    target_time = datetime.fromisoformat(schedule['time'])
    wait_seconds = (target_time - now).total_seconds()
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)

    user = await bot.fetch_user(schedule['user_id'])
    if 'content' in schedule:
        await user.send(schedule['content'])
    if 'file' in schedule:
        await user.send(file=discord.File(schedule['file']))
    schedules.remove(schedule)
    save_schedules()

@bot.event
async def on_ready():
    await tree.sync()
    print(f"{bot.user} is online!")
    for schedule in schedules.copy():
        bot.loop.create_task(send_scheduled_message(schedule))

# ------------------ Slash Commands ------------------

def owner_only(interaction):
    return interaction.user.id == OWNER_ID

@tree.command(name="schedule_text", description="Schedule a text DM to a user")
async def schedule_text(interaction: discord.Interaction, user: discord.User, time: str, message: str):
    if not owner_only(interaction):
        await interaction.response.send_message("❌ You are not the owner.", ephemeral=True)
        return
    schedule_data = {
        "time": time,  # ISO format YYYY-MM-DDTHH:MM
        "user_id": user.id,
        "content": message
    }
    schedules.append(schedule_data)
    save_schedules()
    bot.loop.create_task(send_scheduled_message(schedule_data))
    await interaction.response.send_message(f"✅ Scheduled text DM to {user.name} at {time}", ephemeral=True)

@tree.command(name="schedule_file", description="Schedule a file DM to a user")
async def schedule_file(interaction: discord.Interaction, user: discord.User, time: str, file: discord.Attachment):
    if not owner_only(interaction):
        await interaction.response.send_message("❌ You are not the owner.", ephemeral=True)
        return
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"
    await file.save(file_path)
    schedule_data = {
        "time": time,
        "user_id": user.id,
        "file": file_path
    }
    schedules.append(schedule_data)
    save_schedules()
    bot.loop.create_task(send_scheduled_message(schedule_data))
    await interaction.response.send_message(f"✅ Scheduled file DM to {user.name} at {time}", ephemeral=True)

@tree.command(name="list_schedules", description="List all scheduled messages")
async def list_schedules(interaction: discord.Interaction):
    if not owner_only(interaction):
        await interaction.response.send_message("❌ You are not the owner.", ephemeral=True)
        return
    if not schedules:
        await interaction.response.send_message("No scheduled messages.", ephemeral=True)
        return
    msg = ""
    for i, s in enumerate(schedules, 1):
        target_user = await bot.fetch_user(s['user_id'])
        msg += f"{i}. To: {target_user.name}, Time: {s['time']}, Type: {'File' if 'file' in s else 'Text'}\n"
    await interaction.response.send_message(f"📋 Scheduled messages:\n{msg}", ephemeral=True)

@tree.command(name="cancel_schedule", description="Cancel a scheduled message by index")
async def cancel_schedule(interaction: discord.Interaction, index: int):
    if not owner_only(interaction):
        await interaction.response.send_message("❌ You are not the owner.", ephemeral=True)
        return
    if 0 < index <= len(schedules):
        removed = schedules.pop(index-1)
        save_schedules()
        await interaction.response.send_message(f"✅ Cancelled schedule for user ID {removed['user_id']}", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Invalid index!", ephemeral=True)

bot.run(TOKEN)
