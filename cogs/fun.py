import discord
from discord.ext import commands
from utils.funciones_json import cargar_json, guardar_json
import random

config_file = "json/config.json"

class EventosRandom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        datos = cargar_json(config_file)
        server_id = str(message.guild.id)

        # Verificar canal de votación configurado
        if server_id not in datos or "canal_juego" not in datos[server_id]:
            return

        # ⚠️ NUEVO: verificar si los eventos están activados
        if (
            "tourette_activo" not in datos[server_id]
            or not datos[server_id]["tourette_activo"]
        ):
            datos[server_id]["tourette_activo"] = False
            guardar_json(config_file, datos)
            return  # Eventos desactivados → salir


        canal_juego_id = datos[server_id]["canal_juego"]
        if message.channel.id != canal_juego_id:
            return

        # --- Buscar el último mensaje distinto al actual ---
        async for ultimo_msg in message.channel.history(limit=2):
            if ultimo_msg.id != message.id:
                break
        else:
            return

        contenido = ultimo_msg.content.lower()

        # --- Reacción especial a “jueves” ---
        if "jueves" in contenido.split():
            try:
                await message.channel.send(
                    ":zany_face: >  Y hasta los domingos :point_right: :point_right:",
                    reference=ultimo_msg,
                    mention_author=False
                )
                return
            except discord.Forbidden:
                print("⚠️ No tengo permisos para enviar mensajes en este canal.")
            except discord.HTTPException as e:
                print(f"⚠️ Error al enviar mensaje: {e}")

        # --- Reacción especial a “dos” ---
        if "dos" in contenido.split():
            try:
                await message.channel.send(
                    ":zany_face: >  Hasta tres :point_right: :point_right:",
                    reference=ultimo_msg,
                    mention_author=False
                )
                return
            except discord.Forbidden:
                print("⚠️ No tengo permisos para enviar mensajes en este canal.")
            except discord.HTTPException as e:
                print(f"⚠️ Error al enviar mensaje: {e}")

        # --- Evento aleatorio con 1% ---
        if random.randint(1, 100) == 1:
            palabras = ultimo_msg.content.split()
            if not palabras:
                return

            palabras_invalidas = {
                "y", "de", "a", "el", "la", "los", "las", "en", "un", "una", "eso", "esa", "me",
                "por", "para", "con", "sin", "que", "o", "al", "del", "se", "lo", "le"
            }

            palabras_validas = [p for p in palabras if len(p) > 2 and p.lower() not in palabras_invalidas]
            if not palabras_validas:
                return

            reemplazos = ["pla", "popístic@", "bzz bzz"]
            palabra_original = random.choice(palabras_validas)
            palabra_nueva = random.choice(reemplazos)
            nuevo_contenido = f":zany_face: >  {ultimo_msg.content.replace(palabra_original, palabra_nueva, 1)}"

            try:
                await message.channel.send(
                    nuevo_contenido,
                    reference=ultimo_msg,
                    mention_author=False
                )
            except discord.Forbidden:
                print("⚠️ No tengo permisos para enviar mensajes en este canal.")
            except discord.HTTPException as e:
                print(f"⚠️ Error al enviar mensaje: {e}")

        # --- Segundo evento aleatorio con 1% ---
        if random.randint(1, 100) == 1:
            frases = [
                "Linchen a Hyde",
                "Envenenen a Mirto",
                "Maquillaron a Lazo!",
                "LA CEBOLLA :speaking_head:",
                "Basado :moyai:",
                "Primarca :moyai:"
            ]
            try:
                await message.channel.send(f":zany_face: > {random.choice(frases)}")
            except discord.Forbidden:
                print("⚠️ No tengo permisos para enviar mensajes en este canal.")
            except discord.HTTPException as e:
                print(f"⚠️ Error al enviar mensaje: {e}")

    # ------------------------------
    # ✅ Comando para activar/desactivar
    # ------------------------------
    @discord.slash_command(description="(MOD) Activa o desactiva los eventos aleatorios del canal de votación.")
    @discord.default_permissions(administrator=True)
    async def toggle_tourette(self, ctx):
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        if server_id not in datos:
            datos[server_id] = {}

        estado_actual = datos[server_id].get("tourette_activo", True)
        nuevo_estado = not estado_actual
        datos[server_id]["tourette_activo"] = nuevo_estado

        guardar_json(config_file, datos)
        estado_texto = "✅ Activados" if nuevo_estado else "❌ Desactivados"
        await ctx.respond(f"Eventos aleatorios para este servidor: {estado_texto}.", ephemeral=False)


    @discord.slash_command(description="John Bot Jovi está enfermito :(")
    async def tourette(self, ctx):
        await ctx.respond(":pensive: El bot fue diagnosticado con síndrome de Tourette y a veces se le salen oraciones sin querer.\n" + 
                          "Cuando veas un mensaje que empieza con el emoji :zany_face:, no lo tomes en serio, realmente no lo dijo con intención :(")


    
def setup(bot):
    bot.add_cog(EventosRandom(bot))

