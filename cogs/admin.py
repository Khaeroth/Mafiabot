# cogs/admin.py
import discord
from discord.ext import commands
from discord import option
import asyncio
from datetime import datetime, timedelta
from utils.funciones_json import cargar_json

config_file = "json/config.json"

# --- Cog principal ---
class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cuentas_atras = {}

    @discord.slash_command(description="(MOD) Envía un mensaje al canal de juego en nombre del bot.")
    @discord.default_permissions(administrator=True)
    @option("mensaje", str, description="El mensaje que deseas enviar en el canal de juego.")
    async def anunciar(self, ctx, mensaje: str):
        """Permite a un moderador enviar un mensaje al canal de juego usando el bot."""
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        # Verificar que haya un canal de juego configurado
        if server_id not in datos or "canal_juego" not in datos[server_id]:
            await ctx.respond("⚠️ No hay ningún canal de juego configurado.", ephemeral=True)
            return

        canal_id = datos[server_id]["canal_juego"]
        canal_juego = ctx.guild.get_channel(canal_id)

        if not canal_juego:
            await ctx.respond("⚠️ El canal de juego configurado ya no existe.", ephemeral=True)
            return

        # Enviar el mensaje como el bot
        await canal_juego.send(mensaje)

        # Confirmar al moderador que el mensaje fue enviado
        await ctx.respond(f"✅ Mensaje enviado correctamente a {canal_juego.mention}.", ephemeral=True)


    # --- Comando para borrar mensajes del canal ---
    @discord.slash_command(description="(MOD) Borra una cantidad de mensajes en el canal actual.")
    @discord.default_permissions(administrator=True)
    @option("cantidad", int, description="Cantidad de mensajes a borrar (máx. 100).")
    async def borrar_mensajes(self, ctx, cantidad: int):
        """Borra mensajes recientes del canal."""
        
        if cantidad < 1 or cantidad > 100:
            await ctx.respond("⚠️ Debes especificar una cantidad entre 1 y 100.", ephemeral=True)
            return
        
        await ctx.defer(ephemeral=True)  # evita timeout mientras borra
        
        # Borra los mensajes
        borrados = await ctx.channel.purge(limit=cantidad + 1)  # +1 incluye el comando
        await ctx.respond(f"🧹 Se han borrado **{len(borrados)-1}** mensajes.", ephemeral=True)


    # --- Comando para iniciar una cuenta atrás ---
    @discord.slash_command(description="(MOD) Inicia una cuenta regresiva. El formato es: En X horas se va a: 'mensaje'.")
    @option("tiempo", int, description="Tiempo **en horas** para la cuenta regresiva.")
    @option("mensaje", str, description="Qué ocurrirá cuando termine la cuenta regresiva.")
    @discord.default_permissions(administrator=True)
    async def cuenta_atras_iniciar(self, ctx, tiempo: int, mensaje: str):
        """Crea una cuenta regresiva que envía un aviso cuando se cumple el tiempo."""

        if tiempo <= 0:
            await ctx.respond("⏳ El tiempo debe ser mayor que 0 horas.", ephemeral=True)
            return

        guild_id = ctx.guild.id

        # Si ya hay una cuenta atrás activa en este servidor
        if guild_id in self.cuentas_atras:
            await ctx.respond(
                "⚠️ Ya hay una cuenta regresiva activa. Usa `/cuenta_atras_cancelar` para detenerla primero.",
                ephemeral=True
            )
            return

        await ctx.respond(
            f"🕐 En **{tiempo} hora{'s' if tiempo != 1 else ''}** se va a: **{mensaje}**"
        )

        segundos = tiempo * 3600
        fin = datetime.utcnow() + timedelta(seconds=segundos)

        async def tarea_cuenta_atras():
            try:
                await asyncio.sleep(segundos)
                await ctx.channel.send(f"🚨 ¡Ahora se va a: **{mensaje}**!")
            except asyncio.CancelledError:
                #await ctx.channel.send("❌ La cuenta regresiva fue cancelada.")
                pass
            finally:
                self.cuentas_atras.pop(guild_id, None)

        tarea = asyncio.create_task(tarea_cuenta_atras())

        # Guardar los datos del temporizador
        self.cuentas_atras[guild_id] = {
            "tarea": tarea,
            "fin": fin,
            "mensaje": mensaje
        }

    @discord.slash_command(description="Muestra cuánto tiempo falta para que termine la cuenta regresiva.")
    async def cuenta_atras_status(self, ctx):
        guild_id = ctx.guild.id
        datos = self.cuentas_atras.get(guild_id)

        if not datos:
            await ctx.respond("❌ No hay ninguna cuenta regresiva activa.", ephemeral=True)
            return

        faltante = datos["fin"] - datetime.utcnow()
        horas, resto = divmod(int(faltante.total_seconds()), 3600)
        minutos, segundos = divmod(resto, 60)

        await ctx.respond(
            f"⏳ Faltan **{horas}h {minutos}m {segundos}s** para: **{datos['mensaje']}**"
        )

    @discord.slash_command(description="(MOD) Cancela la cuenta regresiva activa, si hay una.")
    @discord.default_permissions(administrator=True)
    async def cuenta_atras_cancelar(self, ctx):
        guild_id = ctx.guild.id
        datos = self.cuentas_atras.get(guild_id)

        if not datos:
            await ctx.respond("❌ No hay ninguna cuenta regresiva activa.", ephemeral=True)
            return

        datos["tarea"].cancel()
        self.cuentas_atras.pop(guild_id, None)
        await ctx.respond("🛑 Cuenta regresiva cancelada correctamente.", ephemeral=False)

    @discord.slash_command(description="(MOD) Verifica si el bot está funcionando.")
    @discord.default_permissions(administrator=True)
    async def ping(self, ctx):
        await ctx.respond("Pong :ping_pong:")

def setup(bot):
    bot.add_cog(Admin(bot))
