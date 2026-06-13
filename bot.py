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
    await ctx.send("Comandos disponibles:\n$help - Muestra esta lista de comandos\n$hola - Saluda al usuario\n$curiosidad - muestra una curiosidad sobre el medio ambiente(da entre 1-2 de xp)  \n$stats - muestra tu nivel y XP\n$trivia - inicia minijuego de tribia (da XP por acierto)")

############
###trivia###
############

@bot.command()
async def trivia(ctx):
    try:
        with open('trivia.json', 'r', encoding='utf-8') as f:
            preguntas = json.load(f)
    except FileNotFoundError:
        await ctx.send("⚠️ No se encontró el archivo `trivia.json`.")
        return

    pregunta = random.choice(preguntas)


    texto = f"❓ **{pregunta['pregunta']}**\n\n"
    texto += f"A) {pregunta['opciones'][0]}\n"
    texto += f"B) {pregunta['opciones'][1]}\n"
    texto += f"C) {pregunta['opciones'][2]}"


    vista = TriviaView(pregunta, ctx.author.id)
    
    await ctx.send(texto, view=vista)


#---clase_trivia------------------------------------------------------------------------------------------------------------------------------------------------

class TriviaButton(discord.ui.Button):
    def __init__(self, label, opcion, es_correcta, autor_id, xp_ganar):
        super().__init__(
            label=label, 
            style=discord.ButtonStyle.primary,
            custom_id=f"trivia_{opcion}"
        )
        self.opcion = opcion
        self.es_correcta = es_correcta
        self.autor_id = autor_id
        self.xp_ganar = xp_ganar
        self.respondido = False

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message(
                f"⚠️ Esta trivia es solo para {interaction.message.author.mention}. ¡Escribe `$trivia` para tener la tuya!", 
                ephemeral=True
            )
            return
        
        # 2. Evitar múltiples clics del mismo autor
        if self.respondido:
            return

        self.respondido = True
        
        for child in self.view.children:
            child.disabled = True
            if child.opcion == self.opcion:
                child.style = discord.ButtonStyle.green if self.es_correcta else discord.ButtonStyle.red
            elif child.es_correcta:
                child.style = discord.ButtonStyle.green # Siempre muestra cuál era la correcta al final
            else:
                child.style = discord.ButtonStyle.secondary

        await interaction.message.edit(view=self.view)

        if self.es_correcta:
            resultado = agregar_xp(str(interaction.user.id), str(interaction.guild.id), self.xp_ganar)
            mensaje = f"✅ ¡Correcto {interaction.user.mention}! Ganaste **{self.xp_ganar} XP**."
            
            if resultado["subio_nivel"]:
                nombre_nivel = get_nombre_nivel(resultado["nivel"])
                mensaje += f"\n🎉 ¡Subiste de nivel! Ahora eres **{nombre_nivel}**."
            
            await interaction.response.send_message(mensaje, ephemeral=True)
            
        else:
            correcta_label = "Desconocida"
            for child in self.view.children:
                if child.es_correcta:
                    correcta_label = child.label
                    break
            
            mensaje_fallo = (
                f"❌ Incorrecto {interaction.user.mention}. No ganas XP esta vez.\n"
                f"💡 La respuesta correcta era la opción **{correcta_label}**."
            )
            await interaction.response.send_message(mensaje_fallo, ephemeral=True)


class TriviaView(discord.ui.View):
    def __init__(self, pregunta_data, autor_id, timeout=30):
        super().__init__(timeout=timeout)
        self.pregunta_data = pregunta_data
        self.autor_id = autor_id
        
        # XP aleatorio entre 5 y 10 por acierto
        xp_ganar = random.randint(5, 10)
        
        opciones = [
            ("A", pregunta_data["opciones"][0], pregunta_data["correcta"] == 0),
            ("B", pregunta_data["opciones"][1], pregunta_data["correcta"] == 1),
            ("C", pregunta_data["opciones"][2], pregunta_data["correcta"] == 2)
        ]
        
        for label, texto, es_correcta in opciones:
            self.add_item(TriviaButton(label, label, es_correcta, autor_id, xp_ganar))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
            if hasattr(child, 'es_correcta') and child.es_correcta:
                child.style = discord.ButtonStyle.green
        

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