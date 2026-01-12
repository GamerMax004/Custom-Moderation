import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta, datetime
import json
import os
from typing import Optional

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

class ModBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.cases = {}
        self.warns = {}
        self.config = {}
        self.load_data()

    def load_data(self):
        """Lädt Cases, Warns und Config aus JSON"""
        if os.path.exists('cases.json'):
            with open('cases.json', 'r', encoding='utf-8') as f:
                self.cases = json.load(f)
        if os.path.exists('warns.json'):
            with open('warns.json', 'r', encoding='utf-8') as f:
                self.warns = json.load(f)
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)

    def save_data(self):
        """Speichert Cases, Warns und Config"""
        with open('cases.json', 'w', encoding='utf-8') as f:
            json.dump(self.cases, f, indent=4, ensure_ascii=False)
        with open('warns.json', 'w', encoding='utf-8') as f:
            json.dump(self.warns, f, indent=4, ensure_ascii=False)
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def get_next_case_id(self, guild_id: str) -> int:
        """Generiert die nächste Case ID für einen Server"""
        if guild_id not in self.cases:
            self.cases[guild_id] = []
        return len(self.cases[guild_id]) + 1

    def add_case(self, guild_id: str, case_type: str, user_id: int, moderator_id: int, reason: str, extra_data: dict = None) -> int:
        """Fügt einen neuen Case hinzu"""
        case_id = self.get_next_case_id(guild_id)
        case = {
            "case_id": case_id,
            "type": case_type,
            "user_id": user_id,
            "moderator_id": moderator_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "active": True
        }
        if extra_data:
            case.update(extra_data)

        if guild_id not in self.cases:
            self.cases[guild_id] = []
        self.cases[guild_id].append(case)
        self.save_data()
        return case_id

    async def log_action(self, interaction: discord.Interaction, embed: discord.Embed):
        """Sendet ein Embed in den Log-Kanal, falls konfiguriert"""
        guild_id = str(interaction.guild.id)
        if guild_id in self.config and "log_channel" in self.config[guild_id]:
            channel_id = self.config[guild_id]["log_channel"]
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                try:
                    await channel.send(embed=embed)
                except:
                    pass

    def get_case(self, guild_id: str, case_id: int):
        """Holt einen Case anhand der ID"""
        if guild_id not in self.cases:
            return None
        for case in self.cases[guild_id]:
            if case["case_id"] == case_id:
                return case
        return None

    def has_mod_permission(self, member: discord.Member, command: str) -> bool:
        """Prüft ob ein Member die Berechtigung für einen Command hat"""
        guild_id = str(member.guild.id)
        if guild_id not in self.config:
            return member.guild_permissions.administrator

        config = self.config[guild_id]
        if "permissions" not in config:
            return member.guild_permissions.administrator

        for role in member.roles:
            role_id = str(role.id)
            if role_id in config["permissions"]:
                if command in config["permissions"][role_id]:
                    return True

        return member.guild_permissions.administrator

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Slash Commands synchronisiert!")

    async def on_ready(self):
        print(f"✅ {self.user.name} ist online!")
        print(f"🔧 Custom Moderation Bot bereit")
        print(f"📊 Auf {len(self.guilds)} Servern aktiv")

bot = ModBot()

# ============= PERMISSIONS SETUP =============
@bot.tree.command(name="setpermission", description="Setzt Berechtigungen für eine Rolle")
@app_commands.describe(
    rolle="Die Rolle",
    command="Der Command (z.B. ban, kick, warn, timeout, lock, etc.)",
    erlauben="Erlauben oder verbieten"
)
@app_commands.checks.has_permissions(administrator=True)
async def setpermission(interaction: discord.Interaction, rolle: discord.Role, command: str, erlauben: bool):
    guild_id = str(interaction.guild.id)

    if guild_id not in bot.config:
        bot.config[guild_id] = {"permissions": {}}
    if "permissions" not in bot.config[guild_id]:
        bot.config[guild_id]["permissions"] = {}

    role_id = str(rolle.id)
    if role_id not in bot.config[guild_id]["permissions"]:
        bot.config[guild_id]["permissions"][role_id] = []

    if erlauben:
        if command not in bot.config[guild_id]["permissions"][role_id]:
            bot.config[guild_id]["permissions"][role_id].append(command)
            bot.save_data()
            await interaction.response.send_message(
                f"<:4569ok:1459829278572019840> Die Rolle {rolle.mention} hat nun Zugriff auf `/{command}`",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"<:8649warning:1459829288558923859> Die Rolle {rolle.mention} hat bereits Zugriff auf `/{command}`",
                ephemeral=True
            )
    else:
        if command in bot.config[guild_id]["permissions"][role_id]:
            bot.config[guild_id]["permissions"][role_id].remove(command)
            bot.save_data()
            await interaction.response.send_message(
                f"<:4569ok:1459829278572019840> Der Zugriff auf `/{command}` wurde für {rolle.mention} entfernt",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"<:8649warning:1459829288558923859> Die Rolle {rolle.mention} hat keinen Zugriff auf `/{command}`",
                ephemeral=True
            )

@bot.tree.command(name="permissions", description="Zeigt alle Berechtigungen einer Rolle")
@app_commands.describe(rolle="Die Rolle")
async def permissions(interaction: discord.Interaction, rolle: discord.Role):
    guild_id = str(interaction.guild.id)
    role_id = str(rolle.id)

    if guild_id not in bot.config or "permissions" not in bot.config[guild_id]:
        await interaction.response.send_message("<:4934error:1459829281885782157> Keine Berechtigungen konfiguriert!", ephemeral=True)
        return

    if role_id not in bot.config[guild_id]["permissions"]:
        await interaction.response.send_message(f"<:4934error:1459829281885782157> Keine Berechtigungen für {rolle.mention} gefunden!", ephemeral=True)
        return

    perms = bot.config[guild_id]["permissions"][role_id]

    embed = discord.Embed(
        title=f"Berechtigungen für {rolle.name}",
        description=f"Diese Rolle hat Zugriff auf folgende Commands:",
        color=rolle.color
    )
    embed.add_field(name="<:7232rules:1460023657605628036> Commands", value=", ".join(f"`{p}`" for p in perms) if perms else "Keine", inline=False)
    embed.set_footer(text="Custom Moderation by Custom Discord Development")

    await interaction.response.send_message(embed=embed)
    await bot.log_action(interaction, embed)

# ============= BAN COMMAND =============
@bot.tree.command(name="ban", description="Bannt einen User vom Server")
@app_commands.describe(
    user="Der zu bannende User",
    grund="Grund für den Ban",
    tage="Nachrichten der letzten X Tage löschen (0-7)"
)
async def ban(interaction: discord.Interaction, user: discord.User, grund: str = "Kein Grund angegeben", tage: int = 0):
    if not bot.has_mod_permission(interaction.user, "ban"):
        await interaction.response.send_message("<:4934error:1459829281885782157> Du hast keine Berechtigung für diesen Befehl!", ephemeral=True)
        return

    if tage < 0 or tage > 7:
        await interaction.response.send_message("<:8649warning:1459829288558923859> Tage müssen zwischen 0 und 7 liegen!", ephemeral=True)
        return

    try:
        await interaction.guild.ban(
            user, 
            reason=f"{grund} | Moderator: {interaction.user.name}",
            delete_message_days=tage
        )

        case_id = bot.add_case(
            str(interaction.guild.id),
            "ban",
            user.id,
            interaction.user.id,
            grund,
            {"tage": tage}
        )

        embed = discord.Embed(
            title="User gebannt",
            description=f"**{user.name}** wurde erfolgreich gebannt.",
            color=0xED4245
        )
        embed.add_field(name="<:1710channel:1460023609081725112> Case ID", value=f"`#{case_id}`", inline=True)
        embed.add_field(name="<:2529memberwhite:1460023620364402730> User", value=f"{user.name} ({user.id})", inline=True)
        embed.add_field(name="<:4307managerwhite:1460023635497451551> Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="<:1701announcement:1460023604497481981> Grund", value=grund, inline=False)
        embed.set_footer(text="Custom Moderation by Custom Discord Development")
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed)
        await bot.log_action(interaction, embed)
    except discord.Forbidden:
        await interaction.response.send_message("<:4934error:1459829281885782157> Ich habe keine Berechtigung, diesen User zu bannen!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"<:4934error:1459829281885782157> Fehler beim Bannen: {str(e)}", ephemeral=True)

# ============= UNBAN COMMAND =============
@bot.tree.command(name="unban", description="Entbannt einen User")
@app_commands.describe(user_id="Die User ID des zu entbannenden Users")
async def unban(interaction: discord.Interaction, user_id: str):
    if not bot.has_mod_permission(interaction.user, "unban"):
        await interaction.response.send_message("<:4934error:1459829281885782157> Du hast keine Berechtigung für diesen Befehl!", ephemeral=True)
        return

    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user, reason=f"Entbannt von {interaction.user.name}")

        case_id = bot.add_case(
            str(interaction.guild.id),
            "unban",
            user.id,
            interaction.user.id,
            "Entbannt"
        )

        embed = discord.Embed(
            title="User entbannt",
            description=f"**{user.name}** wurde erfolgreich entbannt.",
            color=0x57F287
        )
        embed.add_field(name="<:1710channel:1460023609081725112> Case ID", value=f"`#{case_id}`", inline=True)
        embed.add_field(name="<:2529memberwhite:1460023620364402730> User", value=f"{user.name} ({user.id})", inline=True)
        embed.add_field(name="<:4307managerwhite:1460023635497451551> Moderator", value=interaction.user.mention, inline=True)
        embed.set_footer(text="Custom Moderation by Custom Discord Development")
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed)
        await bot.log_action(interaction, embed)
    except ValueError:
        await interaction.response.send_message("<:4934error:1459829281885782157> Ungültige User ID!", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("<:8649warning:1459829288558923859> Dieser User ist nicht gebannt!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"<:4934error:1459829281885782157> Fehler beim Entbannen: {str(e)}", ephemeral=True)

# ============= KICK COMMAND =============
@bot.tree.command(name="kick", description="Kickt einen User vom Server")
@app_commands.describe(
    user="Der zu kickende User",
    grund="Grund für den Kick"
)
async def kick(interaction: discord.Interaction, user: discord.Member, grund: str = "Kein Grund angegeben"):
    if not bot.has_mod_permission(interaction.user, "kick"):
        await interaction.response.send_message("<:4934error:1459829281885782157> Du hast keine Berechtigung für diesen Befehl!", ephemeral=True)
        return

    try:
        await user.kick(reason=f"{grund} | Moderator: {interaction.user.name}")

        case_id = bot.add_case(
            str(interaction.guild.id),
            "kick",
            user.id,
            interaction.user.id,
            grund
        )

        embed = discord.Embed(
            title="User gekickt",
            description=f"**{user.name}** wurde erfolgreich gekickt.",
            color=0xFEE75C
        )
        embed.add_field(name="<:1710channel:1460023609081725112> Case ID", value=f"`#{case_id}`", inline=True)
        embed.add_field(name="<:2529memberwhite:1460023620364402730> User", value=f"{user.name} (``{user.id}``)", inline=True)
        embed.add_field(name="<:4307managerwhite:1460023635497451551> Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="<:1701announcement:1460023604497481981> Grund", value=grund, inline=False)
        embed.set_footer(text="Custom Moderation by Custom Discord Development")
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed)
        await bot.log_action(interaction, embed)
    except discord.Forbidden:
        await interaction.response.send_message("<:4934error:1459829281885782157> Ich habe keine Berechtigung, diesen User zu kicken!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"<:4934error:1459829281885782157> Fehler beim Kicken: {str(e)}", ephemeral=True)

# ============= TIMEOUT COMMAND =============
@bot.tree.command(name="timeout", description="Gibt einem User einen Timeout")
@app_commands.describe(
    user="Der User",
    dauer="Dauer in Minuten (1-40320)",
    grund="Grund für den Timeout"
)
async def timeout(interaction: discord.Interaction, user: discord.Member, dauer: int, grund: str = "Kein Grund angegeben"):
    if not bot.has_mod_permission(interaction.user, "timeout"):
        await interaction.response.send_message("<:4934error:1459829281885782157> Du hast keine Berechtigung für diesen Befehl!", ephemeral=True)
        return

    if dauer < 1 or dauer > 40320:
        await interaction.response.send_message("<:8649warning:1459829288558923859> Dauer muss zwischen 1 und 40320 Minuten liegen!", ephemeral=True)
        return

    try:
        await user.timeout(
            timedelta(minutes=dauer),
            reason=f"{grund} | Moderator: {interaction.user.name}"
        )

        case_id = bot.add_case(
            str(interaction.guild.id),
            "timeout",
            user.id,
            interaction.user.id,
            grund,
            {"dauer": dauer}
        )

        embed = discord.Embed(
            title="User getimeoutet",
            description=f"{user.mention} wurde erfolgreich getimeoutet.",
            color=0xF26522
        )
        embed.add_field(name="<:1710channel:1460023609081725112> Case ID", value=f"`#{case_id}`", inline=True)
        embed.add_field(name="<:2529memberwhite:1460023620364402730> User", value=f"{user.name} ({user.id})", inline=True)
        embed.add_field(name="<:4307managerwhite:1460023635497451551> Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="<:8045slowmode:1460023665663017065> Dauer", value=f"{dauer} Minuten", inline=True)
        embed.add_field(name="<:1701announcement:1460023604497481981> Grund", value=grund, inline=False)
        embed.set_footer(text="Custom Moderation by Custom Discord Development")
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed)
        await bot.log_action(interaction, embed)
    except discord.Forbidden:
        await interaction.response.send_message("<:4934error:1459829281885782157> Ich habe keine Berechtigung, diesem User einen Timeout zu geben!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"<:4934error:1459829281885782157> Fehler beim Timeout: {str(e)}", ephemeral=True)

# ============= UNTIMEOUT COMMAND =============
@bot.tree.command(name="untimeout", description="Entfernt den Timeout von einem User")
@app_commands.describe(user="Der User")
async def untimeout(interaction: discord.Interaction, user: discord.Member):
    if not bot.has_mod_permission(interaction.user, "untimeout"):
        await interaction.response.send_message("<:4934error:1459829281885782157> Du hast keine Berechtigung für diesen Befehl!", ephemeral=True)
        return

    try:
        await user.timeout(None, reason=f"Timeout entfernt | Moderator: {interaction.user.name}")

        case_id = bot.add_case(
            str(interaction.guild.id),
            "untimeout",
            user.id,
            interaction.user.id,
            "Timeout entfernt"
        )

        embed = discord.Embed(
            title="Timeout entfernt",
            description=f"Der Timeout von **{user.mention}** wurde entfernt.",
            color=0x57F287
        )
        embed.add_field(name="<:1710channel:1460023609081725112> Case ID", value=f"`#{case_id}`", inline=True)
        embed.add_field(name="<:2529memberwhite:1460023620364402730> User", value=f"{user.name} (``{user.id}``)", inline=True)
        embed.add_field(name="<:4307managerwhite:1460023635497451551> Moderator", value=interaction.user.mention, inline=True)
        embed.set_footer(text="Custom Moderation by Custom Discord Development")
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed)
        await bot.log_action(interaction, embed)
    except discord.Forbidden:
        await interaction.response.send_message("<:4934error:1459829281885782157> Ich habe keine Berechtigung!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"<:4934error:1459829281885782157> Fehler: {str(e)}", ephemeral=True)

# ============= WARN COMMAND =============
@bot.tree.command(name="warn", description="Warnt einen User")
@app_commands.describe(
    user="Der zu warnende User",
    grund="Grund für die Warnung"
)
async def warn(interaction: discord.Interaction, user: discord.Member, grund: str):
    if not bot.has_mod_permission(interaction.user, "warn"):
        await interaction.response.send_message("<:4934error:1459829281885782157> Du hast keine Berechtigung für diesen Befehl!", ephemeral=True)
        return

    case_id = bot.add_case(
        str(interaction.guild.id),
        "warn",
        user.id,
        interaction.user.id,
        grund
    )

    # Warn zur Liste hinzufügen
    guild_id = str(interaction.guild.id)
    user_id = str(user.id)
    if guild_id not in bot.warns:
        bot.warns[guild_id] = {}
    if user_id not in bot.warns[guild_id]:
        bot.warns[guild_id][user_id] = []

    bot.warns[guild_id][user_id].append({
        "case_id": case_id,
        "grund": grund,
        "moderator_id": interaction.user.id,
        "timestamp": datetime.utcnow().isoformat()
    })
    bot.save_data()

    warn_count = len(bot.warns[guild_id][user_id])

    embed = discord.Embed(
        title="User verwarnt",
        description=f"**{user.mention}** wurde verwarnt.",
        color=0xFEE75C
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="<:1710channel:1460023609081725112> Case ID", value=f"`#{case_id}`", inline=True)
    embed.add_field(name="<:2529memberwhite:1460023620364402730> User", value=f"{user.name} (``{user.id}``)", inline=True)
    embed.add_field(name="<:4307managerwhite:1460023635497451551> Moderator", value=interaction.user.mention, inline=True)
    embed.add_field(name="<:1701announcement:1460023604497481981> Grund", value=grund, inline=False)
    embed.set_footer(text="Custom Moderation by Custom Discord Development")
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed)
    await bot.log_action(interaction, embed)

    # DM an den User
    try:
        dm_embed = discord.Embed(
            title=f"Du wurdest verwarnt - CaseID ``{case_id}``",
            description=f"Du wurdest auf **{interaction.guild.name}** verwarnt.",
            color=0xFEE75C
        )
        dm_embed.add_field(name="<:1701announcement:1460023604497481981> Grund", value=grund, inline=False)
        dm_embed.add_field(name="<:4307managerwhite:1460023635497451551> Moderator", value=interaction.user.mention, inline=False)
        dm_embed.timestamp = discord.utils.utcnow()

        await user.send(embed=dm_embed)
    except discord.Forbidden:
        pass

# ============= UNWARN COMMAND =============
@bot.tree.command(name="unwarn", description="Entfernt eine Warnung von einem User")
@app_commands.describe(
    user="Der User",
    case_id="Die Case ID der Warnung"
)
async def unwarn(interaction: discord.Interaction, user: discord.Member, case_id: int):
    if not bot.has_mod_permission(interaction.user, "unwarn"):
        await interaction.response.send_message("<:4934error:1459829281885782157> Du hast keine Berechtigung für diesen Befehl!", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    user_id = str(user.id)

    if guild_id not in bot.warns or user_id not in bot.warns[guild_id]:
        await interaction.response.send_message("<:8649warning:1459829288558923859> Dieser User hat keine Verwarnungen!", ephemeral=True)
        return

    # Suche die Warnung
    warn_found = False
    for i, warn in enumerate(bot.warns[guild_id][user_id]):
        if warn["case_id"] == case_id:
            bot.warns[guild_id][user_id].pop(i)
            warn_found = True
            break

    if not warn_found:
        await interaction.response.send_message("<:4934error:1459829281885782157> Warnung mit dieser Case ID nicht gefunden!", ephemeral=True)
        return

    # Case als inaktiv markieren
    case = bot.get_case(guild_id, case_id)
    if case:
        case["active"] = False

    bot.save_data()

    embed = discord.Embed(
        title="Warn entfernt",
        description=f"Der Warn ``#{case_id}`` von **{user.mention}** wurde entfernt.",
        color=0x57F287
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="<:1710channel:1460023609081725112> Case ID", value=f"`#{case_id}`", inline=True)
    embed.add_field(name="<:2529memberwhite:1460023620364402730> User", value=f"{user.name} (``{user.id}``)", inline=True)
    embed.add_field(name="<:4307managerwhite:1460023635497451551> Moderator", value=interaction.user.mention, inline=True)
    embed.set_footer(text="Custom Moderation by Custom Discord Development")
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed)
    await bot.log_action(interaction, embed)

# ============= WARNS COMMAND =============
@bot.tree.command(name="warns", description="Zeigt alle Verwarnungen eines Users")
@app_commands.describe(user="Der User")
async def warns(interaction: discord.Interaction, user: discord.Member):
    guild_id = str(interaction.guild.id)
    user_id = str(user.id)

    if guild_id not in bot.warns or user_id not in bot.warns[guild_id] or not bot.warns[guild_id][user_id]:
        embed = discord.Embed(
            title="<:4569ok:1459829278572019840> Keine Verwarnungen",
            description=f"{user.mention} hat keine aktiven Verwarnungen.",
            color=0x57F287
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Custom Moderation by Custom Discord Development")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.response.send_message(embed=embed)
        return

    warns_list = bot.warns[guild_id][user_id]

    embed = discord.Embed(
        title="Verwarnungen Übersicht",
        description=f"<:2529memberwhite:1460023620364402730> {user.mention}\n<:4322search:1460023637066125352> ``{len(warns_list)}`` Verwarnungen",
        color=0xFEE75C
    )
    embed.set_thumbnail(url=user.display_avatar.url)

    for warn in warns_list[:25]:  # Max 25 Fields
        moderator = await bot.fetch_user(warn["moderator_id"])
        timestamp = datetime.fromisoformat(warn["timestamp"])
        embed.add_field(
            name=f"<:1710channel:1460023609081725112> Case #{warn['case_id']}",
            value=f"**<:1701announcement:1460023604497481981> Grund:** ``{warn['grund']}``\n**<:4307managerwhite:1460023635497451551> Moderator:** {moderator.mention}\n**<:6334event:1460023646881055033> Datum:** <t:{int(timestamp.timestamp())}:R>",
            inline=False
        )

    embed.set_footer(text="Custom Moderation by Custom Discord Development")
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed)
    await bot.log_action(interaction, embed)

# ============= LOCK COMMAND =============
@bot.tree.command(name="lock", description="Sperrt einen Channel")
@app_commands.describe(
    channel="Der zu sperrende Channel (Optional, Standard: Aktueller Channel)",
    grund="Grund für die Sperrung"
)
async def lock(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None, grund: str = "Kein Grund angegeben"):
    if not bot.has_mod_permission(interaction.user, "lock"):
        await interaction.response.send_message("<:4934error:1459829281885782157> Du hast keine Berechtigung für diesen Befehl!", ephemeral=True)
        return

    channel = channel or interaction.channel

    try:
        overwrites = channel.overwrites_for(interaction.guild.default_role)
        overwrites.send_messages = False
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrites, reason=f"{grund} | Moderator: {interaction.user.name}")

        case_id = bot.add_case(
            str(interaction.guild.id),
            "lock",
            0,  # Kein User, sondern Channel
            interaction.user.id,
            grund,
            {"channel_id": channel.id}
        )

        embed = discord.Embed(
            title="Channel gesperrt",
            description=f"{channel.mention} wurde gesperrt.",
            color=0xED4245
        )
        embed.add_field(name="<:1710channel:1460023609081725112> Case ID", value=f"`#{case_id}`", inline=True)
        embed.add_field(name="<:4307managerwhite:1460023635497451551> Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="<:1701announcement:1460023604497481981> Grund", value=grund, inline=False)
        embed.set_footer(text="Custom Moderation by Custom Discord Development")
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed)
        await bot.log_action(interaction, embed)
    except discord.Forbidden:
        await interaction.response.send_message("<:4934error:1459829281885782157> Ich habe keine Berechtigung, diesen Channel zu sperren!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"<:4934error:1459829281885782157> Fehler beim Sperren: {str(e)}", ephemeral=True)

# ============= UNLOCK COMMAND =============
@bot.tree.command(name="unlock", description="Entsperrt einen Channel")
@app_commands.describe(
    channel="Der zu entsperrende Channel (Optional, Standard: Aktueller Channel)"
)
async def unlock(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    if not bot.has_mod_permission(interaction.user, "unlock"):
        await interaction.response.send_message("<:4934error:1459829281885782157> Du hast keine Berechtigung für diesen Befehl!", ephemeral=True)
        return

    channel = channel or interaction.channel

    try:
        overwrites = channel.overwrites_for(interaction.guild.default_role)
        overwrites.send_messages = None
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrites, reason=f"Entsperrt von {interaction.user.name}")

        case_id = bot.add_case(
            str(interaction.guild.id),
            "unlock",
            0,
            interaction.user.id,
            "Channel entsperrt",
            {"channel_id": channel.id}
        )

        embed = discord.Embed(
            title="Channel entsperrt",
            description=f"{channel.mention} wurde entsperrt.",
            color=0x57F287
        )
        embed.add_field(name="<:1710channel:1460023609081725112> Case ID", value=f"`#{case_id}`", inline=True)
        embed.add_field(name="<:4307managerwhite:1460023635497451551> Moderator", value=interaction.user.mention, inline=True)
        embed.set_footer(text="Custom Moderation by Custom Discord Development")
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed)
        await bot.log_action(interaction, embed)
    except discord.Forbidden:
        await interaction.response.send_message("<:4934error:1459829281885782157> Ich habe keine Berechtigung, diesen Channel zu entsperren!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"<:4934error:1459829281885782157> Fehler beim Entsperren: {str(e)}", ephemeral=True)

# ============= REPORT COMMAND =============
@bot.tree.command(name="report", description="Meldet einen User an die Moderatoren")
@app_commands.describe(
    user="Der zu meldende User",
    grund="Grund der Meldung"
)
async def report(interaction: discord.Interaction, user: discord.Member, grund: str):
    guild_id = str(interaction.guild.id)

    # Prüfe ob Report-Channel konfiguriert ist
    if guild_id not in bot.config or "report_channel" not in bot.config[guild_id]:
        await interaction.response.send_message(
            "<:4934error:1459829281885782157> Es wurde kein Report-Channel konfiguriert! Ein Admin muss `/setreportchannel` verwenden.",
            ephemeral=True
        )
        return

    report_channel_id = bot.config[guild_id]["report_channel"]
    report_channel = interaction.guild.get_channel(report_channel_id)

    if not report_channel:
        await interaction.response.send_message("<:4934error:1459829281885782157> Report-Channel nicht gefunden!", ephemeral=True)
        return

    case_id = bot.add_case(
        guild_id,
        "report",
        user.id,
        interaction.user.id,
        grund
    )

    # Report Embed für Mods
    embed = discord.Embed(
        title="Neuer Report",
        description=f"**{user.mention}** wurde gemeldet.",
        color=0xED4245
    )
    embed.add_field(name="<:1710channel:1460023609081725112> Case ID", value=f"`#{case_id}`", inline=True)
    embed.add_field(name="<:2529memberwhite:1460023620364402730> Gemeldeter User", value=f"{user.mention} ({user.id})", inline=True)
    embed.add_field(name="<:4307managerwhite:1460023635497451551> Gemeldet von", value=f"{interaction.user.mention}", inline=True)
    embed.add_field(name="<:1701announcement:1460023604497481981> Grund", value=grund, inline=False)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set.image(url=user.display_avatar.url)
    embed.set_footer(text="Custom Moderation by Custom Discord Development")
    embed.timestamp = discord.utils.utcnow()

    await report_channel.send(embed=embed)

    # Bestätigung an User
    confirm_embed = discord.Embed(
        title="<:4569ok:1459829278572019840> Report gesendet",
        description=f"Dein Report zu **{user.name}** wurde an die Moderatoren weitergeleitet.",
        color=0x57F287
    )
    confirm_embed.add_field(name="<:1710channel:1460023609081725112> Case ID", value=f"`#{case_id}`", inline=False)
    confirm_embed.set_footer(text="Custom Moderation by Custom Discord Development")

    await interaction.response.send_message(embed=confirm_embed, ephemeral=True)

# ============= SET REPORT CHANNEL =============
@bot.tree.command(name="setreportchannel", description="Setzt den Channel für Reports")
@app_commands.describe(channel="Der Report-Channel")
@app_commands.checks.has_permissions(administrator=True)
async def setreportchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild.id)

    if guild_id not in bot.config:
        bot.config[guild_id] = {}

    bot.config[guild_id]["report_channel"] = channel.id
    bot.save_data()

    await interaction.response.send_message(
        f"<:4569ok:1459829278572019840> Report-Channel wurde auf {channel.mention} gesetzt!",
        ephemeral=True
    )

# ============= SET LOG CHANNEL =============
@bot.tree.command(name="setlogchannel", description="Setzt den Channel für Moderations-Logs")
@app_commands.describe(channel="Der Log-Channel")
@app_commands.checks.has_permissions(administrator=True)
async def setlogchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild.id)
    
    if guild_id not in bot.config:
        bot.config[guild_id] = {}
        
    bot.config[guild_id]["log_channel"] = channel.id
    bot.save_data()
    
    await interaction.response.send_message(
        f"<:4569ok:1459829278572019840> Log-Channel wurde auf {channel.mention} gesetzt!",
        ephemeral=True
    )

# ============= CASE COMMAND =============
@bot.tree.command(name="case", description="Zeigt Informationen zu einem Case")
@app_commands.describe(case_id="Die Case ID")
async def case(interaction: discord.Interaction, case_id: int):
    guild_id = str(interaction.guild.id)
    case_data = bot.get_case(guild_id, case_id)

    if not case_data:
        await interaction.response.send_message("<:4934error:1459829281885782157> Case nicht gefunden!", ephemeral=True)
        return

    user = await bot.fetch_user(case_data["user_id"]) if case_data["user_id"] != 0 else None
    moderator = await bot.fetch_user(case_data["moderator_id"])
    timestamp = datetime.fromisoformat(case_data["timestamp"])

    # Farbe je nach Type
    type_info = {
        "ban": ("🔨", "Ban", 0xED4245),
        "unban": ("✅", "Unban", 0x57F287),
        "kick": ("👢", "Kick", 0xFEE75C),
        "timeout": ("⏱️", "Timeout", 0xF26522),
        "untimeout": ("✅", "Untimeout", 0x57F287),
        "warn": ("⚠️", "Warnung", 0xFEE75C),
        "lock": ("🔒", "Lock", 0xED4245),
        "unlock": ("🔓", "Unlock", 0x57F287),
        "report": ("🚨", "Report", 0xED4245),
        "clear": ("🗑️", "Clear", 0x57F287)
    }

    emoji, type_name, color = type_info.get(case_data["type"], ("📋", case_data["type"], 0x5865F2))

    embed = discord.Embed(
        title=f"{emoji} Case #{case_id} - {type_name}",
        color=color
    )

    if user:
        embed.add_field(name="<:2529memberwhite:1460023620364402730> User", value=f"{user.mention} (``{user.id}``)", inline=True)
    elif "channel_id" in case_data:
        channel = interaction.guild.get_channel(case_data["channel_id"])
        embed.add_field(name="<:9896forum:1460023685623845040> Channel", value=channel.mention if channel else "Unbekannt", inline=True)

    embed.add_field(name="<:4307managerwhite:1460023635497451551> Moderator", value=moderator.mention, inline=True)
    embed.add_field(name="<:6334event:1460023646881055033> Datum", value=f"<t:{int(timestamp.timestamp())}:F>", inline=True)
    embed.add_field(name="<:1701announcement:1460023604497481981> Grund", value=case_data["reason"], inline=False)
    embed.add_field(name="<:6576settings:1460023653168320546> Status", value="<:4569ok:1459829278572019840> Aktiv" if case_data.get("active", True) else "<:4934error:1459829281885782157> Inaktiv", inline=True)

    # Zusätzliche Daten
    if "dauer" in case_data:
        embed.add_field(name="<:8045slowmode:1460023665663017065> Dauer", value=f"{case_data['dauer']} Minuten", inline=True)
    if "tage" in case_data:
        embed.add_field(name="<:2854copy:1460023622805491936> Nachrichten", value=f"{case_data['tage']} Tage gelöscht", inline=True)

    embed.set_footer(text="Custom Moderation by Custom Discord Development")
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed)
    await bot.log_action(interaction, embed)

# ============= CLEAR COMMAND =============
@bot.tree.command(name="clear", description="Löscht eine bestimmte Anzahl an Nachrichten")
@app_commands.describe(anzahl="Anzahl der zu löschenden Nachrichten (1-100)")
async def clear(interaction: discord.Interaction, anzahl: int):
    if not bot.has_mod_permission(interaction.user, "clear"):
        await interaction.response.send_message("<:4934error:1459829281885782157> Du hast keine Berechtigung für diesen Befehl!", ephemeral=True)
        return

    if anzahl < 1 or anzahl > 100:
        await interaction.response.send_message("<:8649warning:1459572747196825856> Anzahl muss zwischen 1 und 100 liegen!", ephemeral=True)
        return

    try:
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=anzahl)

        case_id = bot.add_case(
            str(interaction.guild.id),
            "clear",
            0,
            interaction.user.id,
            f"{len(deleted)} Nachrichten gelöscht",
            {"anzahl": len(deleted), "channel_id": interaction.channel.id}
        )

        embed = discord.Embed(
            title="Nachrichten gelöscht",
            description=f"**{len(deleted)}** Nachrichten wurden erfolgreich gelöscht.",
            color=0x57F287
        )
        embed.add_field(name="<:1710channel:1460023609081725112> Case ID", value=f"`#{case_id}`", inline=True)
        embed.add_field(name="<:4307managerwhite:1460023635497451551> Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="<:9896forum:1460023685623845040> Channel", value=interaction.channel.mention, inline=True)
        embed.set_footer(text="Custom Moderation by Custom Discord Development")
        embed.timestamp = discord.utils.utcnow()

        await interaction.followup.send(embed=embed, ephemeral=False)
        await bot.log_action(interaction, embed)
    except discord.Forbidden:
        await interaction.followup.send("<:4934error:1459829281885782157> Ich habe keine Berechtigung, Nachrichten zu löschen!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"<:4934error:1459829281885782157> Fehler: {str(e)}\n(Nachrichten älter als 14 Tage können nicht gelöscht werden)", ephemeral=True)

# ============= USERINFO COMMAND =============
@bot.tree.command(name="userinfo", description="Zeigt Informationen über einen User")
@app_commands.describe(user="Der User")
async def userinfo(interaction: discord.Interaction, user: discord.Member = None):
    user = user or interaction.user

    embed = discord.Embed(
        title=f"Informationen über {user.name}",
        color=0x5865F2
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="<:2529memberwhite:1460023620364402730> Username", value=(f"``{user.name}``"), inline=True)
    embed.add_field(name="<:1710channel:1460023609081725112> User ID", value=(f"``{user.id}``"), inline=True)
    embed.add_field(name="<:6422verifiedwhite:1460023649925988372> Erstellt am", value=f"<t:{int(user.created_at.timestamp())}:F>", inline=False)
    embed.add_field(name="<:1132eventadd:1460023597593530601> Beigetreten am", value=f"<t:{int(user.joined_at.timestamp())}:F>", inline=False)
    embed.add_field(name="<:5269studenthub:1460023640203595889> Rollen", value=f"{len(user.roles)-1} Rollen", inline=True)
    embed.add_field(name="<:1706developerwhite:1460023607596945439> Bot", value="``Ja``" if user.bot else "``Nein``", inline=True)

    # Verwarnungen anzeigen
    guild_id = str(interaction.guild.id)
    user_id = str(user.id)
    if guild_id in bot.warns and user_id in bot.warns[guild_id]:
        warn_count = len(bot.warns[guild_id][user_id])
        embed.add_field(name="<:3259moderatorwhite:1460023630984380590> Verwarnungen", value=f"{warn_count} Verwarnungen", inline=True)

    embed.set_footer(text="Custom Moderation by Custom Discord Development", icon_url=bot.user.display_avatar.url)
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed)
    await bot.log_action(interaction, embed)

# ============= SERVERINFO COMMAND =============
@bot.tree.command(name="serverinfo", description="Zeigt Informationen über den Server")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild

    embed = discord.Embed(
        title=f"Informationen über {guild.name}",
        color=0x5865F2
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(name="<:3041ownerwhite:1460023625632714822> Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="<:1710channel:1460023609081725112> Server ID", value=(f"``{guild.id}``"), inline=True)
    embed.add_field(name="<:1132eventadd:1460023597593530601> Erstellt am", value=f"<t:{int(guild.created_at.timestamp())}:F>", inline=False)
    embed.add_field(name="<:2529memberwhite:1460023620364402730> Mitglieder", value=guild.member_count, inline=True)
    embed.add_field(name="<:9896forum:1460023685623845040> Kanäle", value=len(guild.channels), inline=True)
    embed.add_field(name="<:5269studenthub:1460023640203595889> Rollen", value=len(guild.roles), inline=True)
    embed.add_field(name="<:2982media:1460023623837286714> Emojis", value=len(guild.emojis), inline=True)
    embed.add_field(name="<:9520boosterwhite:1460023680548474880> Boosts", value=f"Level {guild.premium_tier} ({guild.premium_subscription_count} Boosts)", inline=True)
    embed.set_footer(text="Custom Moderation by Custom Discord Development", icon_url=bot.user.display_avatar.url)
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed)
    await bot.log_action(interaction, embed)

# Bot starten - ERSETZE MIT DEINEM TOKEN
if __name__ == "__main__":
    bot.run('MTQ1OTU2OTU3OTc5Mjc5MzYyMQ.GpeCRA.sd-rlNRugXks6I1-EL40DVFqB5oWqiBTNPS2iE')