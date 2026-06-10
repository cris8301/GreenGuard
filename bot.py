""" 
objetivos:
obligatorios:
que el bot haga una trivia de preguntas y respuestas

/que cuente curiosisdades aleatorias sobre el medio ambiente/


opcional:
que el bot tenga un sistema de puntos y niveles (base de datos sqlite3)
roles automaticos por niveles(sqlite3)
"""
import discord
from discord.ext import commands
from discord import app_commands
import random
import sqlite3 
import json
import os

bot = commands.Bot(command_prefix='/', intents=discord.Intents.all(),  help_command=None)

@bot.command()
async def curiosidad(ctx):
    with open('curiosidades.json', 'r') as f:
        curiosidades = json.load(f)
    curiosidad_aleatoria = random.choice(curiosidades)
    await ctx.send(curiosidad_aleatoria)


#dejar el comando help al final, para no perderlo de vista, recordar actualizar cadaque se añada un nuevo comando
@bot.command()
async def help(ctx):
    await ctx.send("Comandos disponibles:\n/help - Muestra esta lista de comandos\n/curiosidad - muestra una curiosidad sobre el medio ambiente")


token = ("TU_TOKEN_AQUI")
