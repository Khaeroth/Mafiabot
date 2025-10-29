# cogs/acciones.py
import discord
from discord.ext import commands
from discord import option
from utils.funciones_json import cargar_json, guardar_json

config_file = "json/config.json"

# --- Cog principal ---
class Acciones(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
# --- Comando para configurar el canal de acciones ---
    @discord.slash_command(description="(MOD) Configura el canal donde se enviarán las acciones de los jugadores.")
    @discord.default_permissions(administrator=True)
    @option("canal", discord.TextChannel, description="Selecciona el canal para las acciones.")
    async def set_canal_acciones(self, ctx, canal: discord.TextChannel):
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        if server_id not in datos:
            datos[server_id] = {}

        datos[server_id]["canal_acciones"] = canal.id
        guardar_json(config_file, datos)

        await ctx.respond(f"✅ Canal de acciones configurado como {canal.mention}", ephemeral=False)

    # --- Comando para que los jugadores envíen acciones ---
    @discord.slash_command(description='Envía una acción al "canal de acciones" del juego.')
    @option("descripcion", str, description="Describe tu acción.", max_length=2000)
    async def accion(self, ctx, descripcion: str):
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        # Verificar configuración
        if server_id not in datos or "rol_jugador" not in datos[server_id] or "canal_acciones" not in datos[server_id]:
            await ctx.respond("⚠️ El sistema de acciones no está configurado aún.", ephemeral=True)
            return

        rol_jugador = ctx.guild.get_role(datos[server_id]["rol_jugador"])
        canal_acciones = ctx.guild.get_channel(datos[server_id]["canal_acciones"])

        if not rol_jugador or not canal_acciones:
            await ctx.respond("⚠️ El rol o el canal configurado ya no existen.", ephemeral=True)
            return

        # Verificar que el usuario tenga el rol
        if rol_jugador not in ctx.author.roles:
            await ctx.respond("🚫 Solo los jugadores pueden enviar acciones.", ephemeral=True)
            return

        # Enviar la acción al canal configurado
        mensaje = f"🕹️ **{ctx.author.display_name}** realiza la siguiente acción:\n>>> {descripcion}"
        await canal_acciones.send(mensaje)

        await ctx.respond(f"✅ Tu acción `{descripcion}` se ha enviado correctamente.", ephemeral=False)


def setup(bot):
    bot.add_cog(Acciones(bot))
