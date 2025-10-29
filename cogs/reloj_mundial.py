# cogs/reloj_mundial.py
import asyncio
from datetime import datetime
import discord
from discord import option
from discord.ext import commands, tasks
import pytz
from utils.funciones_json import cargar_json, guardar_json

db_canales = "json/db_canales.json"

# --- Cog principal ---
class RelojMundial(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.actualizar_horas.start()

    def registrar_zona(self, servidor_id, pais, canal_id, zona_horaria):
        """Agrega un país con su canal y zona al servidor dado. 
        Si el servidor no existe, lo crea automáticamente."""
        datos = cargar_json(db_canales)
        servidor_id = str(servidor_id)

        # Si el servidor no existe, lo creamos con estructura vacía
        if servidor_id not in datos:
            guild = self.bot.get_guild(int(servidor_id))
            datos[servidor_id] = {"server":str(guild.name),"canales": {}, "zonas": {}}

        # Asignamos canal y zona al país
        datos[servidor_id]["canales"][str(canal_id)] = pais
        datos[servidor_id]["zonas"][pais] = zona_horaria

        guardar_json(db_canales, datos)

    def eliminar_pais(self, servidor_id, pais):
        """Elimina un país del servidor, tanto en 'canales' como en 'zonas'.
        Si el servidor queda vacío, también se elimina del archivo."""

        datos = cargar_json(db_canales)
        servidor_id = str(servidor_id)

        if servidor_id not in datos:
            return False

        servidor = datos[servidor_id]
        eliminado = False

        # Buscar canal asociado a ese país
        canales_a_eliminar = [cid for cid, p in servidor["canales"].items() if p == pais]
        for cid in canales_a_eliminar:
            del servidor["canales"][cid]
            eliminado = True

        # Eliminar zona
        if pais in servidor["zonas"]:
            del servidor["zonas"][pais]
            eliminado = True

        # Si ya no queda nada, eliminar servidor
        if eliminado:
            if not servidor["canales"] and not servidor["zonas"]:
                del datos[servidor_id]
            guardar_json(db_canales, datos)

        return eliminado          

    # --- Tarea automática ---

    # 🔹 Espera a que el bot esté listo antes de arrancar el loop
    @commands.Cog.listener()
    async def on_ready(self):
        if not self.actualizar_horas.is_running():
            await asyncio.sleep(30)  # 🔸 Espera 10 segundos para que la caché cargue bien
            self.actualizar_horas.start()
            print("⏰ Tarea automática de Reloj Mundial iniciada.")

    @tasks.loop(minutes=1)
    async def actualizar_horas(self):
        ahora = datetime.now()
        if ahora.minute % 10 != 0:
            return

        datos = cargar_json(db_canales)
        cambios_realizados = False  # <- bandera para guardar solo si algo cambió

        # Recorremos todos los servidores registrados
        for servidor_id, info in list(datos.items()):
            # Recorremos una copia de los canales (para poder eliminar)
            for canal_id, pais in list(info["canales"].items()):
                zona = info["zonas"].get(pais)
                canal = self.bot.get_channel(int(canal_id))

                # 🔧 Si el canal o la zona ya no existen, eliminarlos
                if not canal or not zona:
                    print(f"Canal inválido eliminado: {pais} ({canal_id})")

                    if canal_id in info["canales"]:
                        del info["canales"][canal_id]
                        cambios_realizados = True
                    if pais in info["zonas"]:
                        del info["zonas"][pais]
                        cambios_realizados = True
                    continue
                
                # 🕓 Si el canal existe, actualizar su hora
                try:
                    tz = pytz.timezone(zona)
                    hora = datetime.now(tz).strftime("%I:%M %p")
                    #print(f"✅ Hora actualizada: {pais} en {info.get("server")}")
                    await canal.edit(name=f"{pais}: {hora}")

                except Exception as e:
                    print(f"Error al actualizar {pais}: {e}")

                # 🧹 Si el servidor ya no tiene canales registrados, eliminarlo del JSON.
            if not info["canales"]:
                print(f"Servidor vacío eliminado del registro: {servidor_id}")
                del datos[servidor_id]
                cambios_realizados = True

        # 💾 Guardar los cambios solo si se modificó algo
        if cambios_realizados:
            guardar_json(db_canales, datos)
            #print("✅ JSON actualizado tras limpieza de canales o servidores inválidos.")

    # --- Slash commands ---

    # 🟢 Registrar país
    @discord.slash_command(description="(MOD) Registra un país con su canal y zona horaria para que se actualice cada 10min.")
    @option("pais", str, description="Nombre del país a registrar")
    @option("canal", discord.VoiceChannel, description="Canal a usar para mostrar la hora. Debe ser un canal de voz.")
    @option("zona", str, description="Zona horaria (ejemplo: America/Bogota)", choices=[
            discord.OptionChoice("America/Argentina/Buenos_Aires"),
            discord.OptionChoice("America/Bogota"),
            discord.OptionChoice("America/Caracas"),
            discord.OptionChoice("America/Costa_Rica"),
            discord.OptionChoice("America/Mexico_City"),
            discord.OptionChoice("America/Lima"),
            discord.OptionChoice("America/Santiago"),
            discord.OptionChoice("Europe/Madrid"),
            discord.OptionChoice("Europe/London"),
            discord.OptionChoice("America/New_York"),
            discord.OptionChoice("America/Los_Angeles")
        ]
    )
    @discord.default_permissions(administrator=True)
    async def zh_registrar(self, ctx, pais: str, canal: discord.VoiceChannel, zona: str):
        self.registrar_zona(ctx.guild.id, pais, canal.id, zona)
        await ctx.respond(f"✅ **{pais}** registrado correctamente.\n📺 Canal: {canal.mention}\n🕒 Zona: `{zona}`")


    # 🔴 Eliminar país
    @discord.slash_command(description="(MOD) Elimina un país del registro actual.")
    @option("pais", str, description="Nombre del país a eliminar")
    @discord.default_permissions(administrator=True)
    async def zh_eliminar(self, ctx, pais: str):
        if self.eliminar_pais(ctx.guild.id, pais):
            await ctx.respond(f"🗑️ {pais} eliminado.")
        else:
            await ctx.respond(f"⚠️ {pais} no encontrado.")


    # 📋 Listar países del servidor actual
    @discord.slash_command(description="(MOD) Muestra los países registrados en este servidor.")
    @discord.default_permissions(administrator=True)
    async def zh_listado(self, ctx):
        datos = cargar_json(db_canales)
        servidor_id = str(ctx.guild.id)
        if servidor_id not in datos or not datos[servidor_id]["canales"]:
            await ctx.respond("⚠️ No hay países registrados en este servidor.")
            return

        info = datos[servidor_id]
        lista = "\n".join(
            f"🌍 **{pais}** → <#{canal}> (`{info['zonas'][pais]}`)"
            for canal, pais in info["canales"].items()
        )

        await ctx.respond(f"**Países registrados en este servidor:**\n{lista}")


    # 🌐 Listar todos los países registrados en todos los servidores
    #Solo funciona en el server de Probando-Ando
    @discord.slash_command(description="Muestra todos los países registrados en todos los servidores.", guild_ids=[1420124484790128773])
    async def zh_lista_completa(self, ctx):
        datos = cargar_json(db_canales)
        if not datos:
            await ctx.respond("⚠️ No hay registros en ningún servidor.")
            return

        mensaje = ""
        for servidor_id, info in datos.items():
            guild = self.bot.get_guild(int(servidor_id))
            nombre = guild.name if guild else f"Servidor {servidor_id}"
            lista = "\n".join(
                f"🌍 **{pais}** → <#{canal}> (`{info['zonas'][pais]}`)"
                for canal, pais in info["canales"].items()
            )
            mensaje += f"\n**🛠️ {nombre}:**\n{lista}\n"

        await ctx.respond(mensaje or "⚠️ No hay registros.")


    @discord.slash_command(description="(MOD) Muestra información del módulo de Zonas Horarias (Reloj Mundial).")
    @discord.default_permissions(administrator=True)
    async def zh_info(self, ctx):
        """Muestra un resumen explicativo del módulo de Zonas Horarias."""

        embed = discord.Embed(
            title="🌍 Módulo de Zonas Horarias — Reloj Mundial",
            description=(
                "Este módulo permite mostrar la **hora local de diferentes países directamente en canales de voz**.\n"
                "Cada 10 minutos, el bot actualiza automáticamente el nombre del canal con la hora correspondiente según la zona horaria configurada."
            ),
            color=discord.Color.blue()
        )

        embed.add_field(
            name="⚙️ Funcionamiento",
            value=(
                "- Cada país se asocia con un **canal de voz** y una **zona horaria**.\n"
                "- El bot cambia el **nombre del canal** cada 10 minutos.\n"
            ),
            inline=False
        )

        embed.add_field(
            name="🧭 Comandos principales",
            value=(
                "**/zh_registrar** → Registra un país, canal (tiene que ser de voz) y zona horaria.\n"
                "(El nombre con el que registres el país, es el que aparecerá en el canal)\n"
                "**/zh_eliminar** → Elimina un país registrado.\n"
                "**/zh_listado** → Muestra los países del servidor.\n"
                "**/zh_reset_config** → Reinicia la configuración del módulo.\n"
            ),
            inline=False
        )

        embed.add_field(
            name="🕐 Zonas horarias disponibles",
            value=(
                "`America/Argentina/Buenos_Aires`\n"
                "`America/Bogota`\n"
                "`America/Caracas`\n"
                "`America/Costa_Rica`\n"
                "`America/Mexico_City`\n"
                "`America/Lima`\n"
                "`America/Santiago (de Chile)`\n"
                "`Europe/Madrid`\n"
                "`Europe/London`\n"
                "`America/New_York`\n"
                "`America/Los_Angeles`\n"
            ),
            inline=False
        )


        embed.add_field(
            name="🧨 Ejemplo visual",
            value=(
                "```\n"
                "🔊 Colombia: 08:30 AM\n"
                "🔊 México: 07:30 AM\n"
                "🔊 España: 02:30 PM\n"
                "```\n"
                "Los canales se mantienen sincronizados con la hora real de cada país."
            ),
            inline=False
        )

        embed.set_footer(text="Desarrollado por Khaeroth (https://github.com/Khaeroth)")
        await ctx.respond(embed=embed)

    @discord.slash_command(description="(MOD) Elimina toda la configuración de las zonas horarias en el servidor.")
    @discord.default_permissions(administrator=True)
    async def zh_reset_config(self, ctx):
        """Elimina toda la configuración del servidor actual del archivo JSON, con confirmación previa."""
        datos = cargar_json(db_canales)
        server_id = str(ctx.guild.id)

        if server_id not in datos:
            await ctx.respond("ℹ️ No hay configuración guardada para este servidor.", ephemeral=True)
            return

        # Crear botones de confirmación
        class ConfirmarReset(discord.ui.View):
            def __init__(self, autor):
                super().__init__(timeout=30)
                self.autor = autor
                self.value = None

            async def interaction_check(self, interaction):
                if interaction.user != self.autor:
                    await interaction.response.send_message("🚫 Solo quien ejecutó el comando puede confirmar.", ephemeral=True)
                    return False
                return True

            @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.danger)
            async def confirmar(self, button, interaction):
                datos = cargar_json(db_canales)
                server_id = str(ctx.guild.id)

                if server_id in datos:
                    del datos[server_id]
                    guardar_json(db_canales, datos)

                await interaction.response.edit_message(content="🗑️ Configuración del servidor eliminada correctamente.", view=None)
                self.value = True
                self.stop()

            @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
            async def cancelar(self, button, interaction):
                await interaction.response.edit_message(content="❎ Operación cancelada. No se ha eliminado nada.", view=None)
                self.value = False
                self.stop()

        view = ConfirmarReset(ctx.author)
        await ctx.respond("⚠️ ¿Estás seguro de que quieres **eliminar toda la configuración** del servidor?\nEsta acción no se puede deshacer.", view=view, ephemeral=True)

def setup(bot):
    bot.add_cog(RelojMundial(bot))