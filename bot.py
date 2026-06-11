""" 
objetivos:
obligatorios:
que el bot haga una trivia de preguntas y respuestas
✅que cuente curiosisdades aleatorias sobre el medio ambiente

opcional:
✅que el bot tenga un sistema de puntos y niveles (base de datos sqlite3)
roles automaticos por niveles(sqlite3)
"""
import discord
from discord.ext import commands
import random
import sqlite3 
import json
import os
from dotenv import load_dotenv

load_dotenv('token.env')

bot = commands.Bot(command_prefix='$', intents=discord.Intents.all(), help_command=None)

#------bot commands-----------------------------------------------------------------------------------------------------------------------------------------------

############
###saludo###
############

@bot.command()
async def hola(ctx):
    await ctx.send(f"¡Hola {ctx.author.mention}! 👋")


##################
###curiosidades###
##################

@bot.command()
async def curiosidad(ctx):
    with open('curiosidades.json', 'r', encoding='utf-8') as f:
        curiosidades = json.load(f)
    curiosidad_aleatoria = random.choice(curiosidades)
    await ctx.send(curiosidad_aleatoria)


###########
###stats###
###########

@bot.command()
async def stats(ctx, miembro: discord.Member = None):
    miembro = miembro or ctx.author
    datos = get_usuario(str(miembro.id), str(ctx.guild.id))
    nivel_actual = datos["nivel"]
    nombre_nivel = get_nombre_nivel(nivel_actual)

    embed = discord.Embed(title=f"Perfil de {miembro.display_name}", color=0x5865F2)
    embed.add_field(name="Nivel", value=nombre_nivel)

    if nivel_actual >= NIVEL_MAXIMO:
        embed.add_field(name="XP", value="✅ Nivel máximo alcanzado")
    else:
        xp_necesario = XP_POR_NIVEL[nivel_actual]
        embed.add_field(name="XP", value=f"{datos['xp']} / {xp_necesario}")

    embed.set_thumbnail(url=miembro.display_avatar.url)
    await ctx.send(embed=embed)



############
###help  ###
############

@bot.command()
async def help(ctx):
    await ctx.send("Comandos disponibles:\n$help - Muestra esta lista de comandos\n$hola - Saluda al usuario\n$curiosidad - muestra una curiosidad sobre el medio ambiente\n$stats - muestra tu nivel y XP\n$trivia - proximamente")

############
###trivia###
############



#-----sistema de niveles----------------------------------------------------------------------------------------------------------------------------------------

#############
###niveles###
#############

NIVELES = [
    (0,   "🌱 Hoja"),
    (100, "🌿 Brote"),
    (200, "🌴 Árbol"),
    (300, "🌳🌳 Bosque"),
    (500, "🌲🌲 Ecosistema"),
    (600, "🌎 Planeta")
]

XP_POR_NIVEL = [100, 200, 300, 400, 500]

NIVEL_MAXIMO = len(NIVELES) - 1

def get_nombre_nivel(nivel: int) -> str:
    return NIVELES[nivel][1]

###################
###base de datos###
###################

DB_PATH = 'bot.db'

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def setup_database():
    with get_db_connection() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS usuarios ("
            "user_id TEXT NOT NULL,"
            "guild_id TEXT NOT NULL,"
            "xp INTEGER DEFAULT 0,"
            "nivel INTEGER DEFAULT 0,"
            "PRIMARY KEY (user_id, guild_id))"
        )

def get_usuario(user_id: str, guild_id: str):
    row = None
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT xp, nivel FROM usuarios WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        ).fetchone()

        if row is None:
            conn.execute(
                "INSERT INTO usuarios (user_id, guild_id) VALUES (?, ?)",
                (user_id, guild_id)
            )
            return {"xp": 0, "nivel": 0}

        return {"xp": row[0], "nivel": row[1]}

def agregar_xp(user_id: str, guild_id: str, xp: int) -> dict:
    usuario = get_usuario(user_id, guild_id)

    if usuario["nivel"] >= NIVEL_MAXIMO:
        return {"xp": usuario["xp"], "nivel": usuario["nivel"], "subio_nivel": False}

    else:
        nuevo_xp = usuario["xp"] + xp
        nuevo_nivel = usuario["nivel"]
        subio_nivel = False

        while nuevo_nivel < NIVEL_MAXIMO and nuevo_xp >= XP_POR_NIVEL[nuevo_nivel]:
            nuevo_xp -= XP_POR_NIVEL[nuevo_nivel]
            nuevo_nivel += 1
            subio_nivel = True

        if nuevo_nivel >= NIVEL_MAXIMO:
            nuevo_xp = 0

        with get_db_connection() as conn:
            conn.execute(
                "UPDATE usuarios SET xp = ?, nivel = ? WHERE user_id = ? AND guild_id = ?",
                (nuevo_xp, nuevo_nivel, user_id, guild_id)
            )

        return {"xp": nuevo_xp, "nivel": nuevo_nivel, "subio_nivel": subio_nivel}

#---bot events------------------------------------------------------------------------------------------------------------------------------------------------

##############
## Eventos ###
##############


@bot.event
async def on_ready():
    setup_database()
    print(f"Bot listo: {bot.user}")

    for guild in bot.guilds:
        canal = discord.utils.get(guild.text_channels, name="greenguard")
        if canal:
            await canal.send("🌱 ¡Estoy en línea y listo!")


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if not message.guild:
        return

    #$curiosidad suma 1-2 XP
    if message.content.startswith('$curiosidad'):
        xp_ganado = random.randint(1, 2)
        resultado = agregar_xp(str(message.author.id), str(message.guild.id), xp_ganado)

        if resultado["subio_nivel"]:
            nombre_nivel = get_nombre_nivel(resultado["nivel"])
            await message.channel.send(
                f"🎉 {message.author.mention} subió a **{nombre_nivel}**!"
            )

    #Cualquier otro comando no suma XP
    elif message.content.startswith('$'):
        await bot.process_commands(message)
        return

    await bot.process_commands(message)



bot.run(os.getenv("TOKEN"))