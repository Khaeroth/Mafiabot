# cogs/votos.py
import discord
import random
import os
from discord.ext import commands
from discord import option
from utils.funciones_json import cargar_json, guardar_json

config_file = "json/config.json"

# --- Helpers de peso y threshold (solo por usuario) ---
def _user_key(user_id: int) -> str:
    return f"user_{user_id}"


def obtener_peso_votante(member: discord.Member, datos: dict, server_id: str) -> int:
    """
    Devuelve el multiplicador entero del votante. Por defecto 1.
    Busca en datos[server_id]["weights"] con clave 'user_<id>'.
    """
    try:
        weights = datos.get(server_id, {}).get("weights", {})
        key = _user_key(member.id)
        val = weights.get(key, 1)
        return int(val) if int(val) >= 1 else 1
    except Exception:
        return 1

def obtener_threshold_offset(member: discord.Member, datos: dict, server_id: str) -> int:
    """
    Devuelve el offset entero del threshold para el objetivo.
    Puede ser negativo o positivo. Por defecto 0.
    Busca en datos[server_id]['thresholds'] con clave 'user_<id>'.
    """
    try:
        thresholds = datos.get(server_id, {}).get("thresholds", {})
        key = _user_key(member.id)
        return int(thresholds.get(key, 0))
    except Exception:
        return 0

# --- Cog principal ---
class Votaciones(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(description="(MOD) Registra el canal donde se desarrollará el juego.")
    @discord.default_permissions(administrator=True)
    @option("canal", discord.TextChannel, description="Selecciona el canal para el juego.")
    async def set_canal_juego(self, ctx, canal: discord.TextChannel):
        datos = cargar_json(config_file)
        servidor_id = str(ctx.guild.id)

        '''if servidor_id not in datos:
            datos[servidor_id] = {}'''

        # Si el servidor no existe, lo creamos con estructura vacía
        if servidor_id not in datos:
            guild = self.bot.get_guild(int(servidor_id))
            datos[servidor_id] = {"server":str(guild.name)}

        datos[servidor_id]["canal_juego"] = canal.id
        guardar_json(config_file, datos)

        await ctx.respond(f"✅ Canal de juego registrado: {canal.mention}")


    @discord.slash_command(description="(MOD) Registra el rol que será usado para los jugadores.")
    #@discord.default_permissions(manage_guild=True)
    @discord.default_permissions(administrator=True)
    @option("rol", discord.Role, description="Selecciona el rol que usarán los jugadores.")
    async def set_rol_jugadores(self, ctx, rol: discord.Role):
        datos = cargar_json(config_file)
        servidor_id = str(ctx.guild.id)

        if servidor_id not in datos:
            datos[servidor_id] = {}

        datos[servidor_id]["rol_jugador"] = rol.id
        guardar_json(config_file, datos)

        await ctx.respond(f"✅ Rol de **jugadores** registrado: **{rol.name}**")


    @discord.slash_command(description="(MOD) Registra el rol que será usado para los jugadores muertos.")
    @discord.default_permissions(administrator=True)
    @option("rol", discord.Role, description="Selecciona el rol que usarán los jugadores muertos.")
    async def set_rol_muertos(self, ctx, rol: discord.Role):
        """Permite registrar un rol especial para los jugadores muertos."""
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        if server_id not in datos:
            datos[server_id] = {}

        datos[server_id]["rol_muerto"] = rol.id
        guardar_json(config_file, datos)

        await ctx.respond(f"💀 Rol de **muertos** registrado: **{rol.name}**")


    @discord.slash_command(description='(MOD) Configura el "peso" del voto a un jugador. 1 = normal, 2 = doble, 3 = triple, etc.')
    @discord.default_permissions(administrator=True)
    @option("usuario", description="Usuario al que asignar peso", type=discord.Member)
    @option("peso", description="Valor numérico (ej: 1, 2). Usa 1 para restablecer a 1 o 0 para eliminar.", required=True)
    async def set_valor_voto_jugador(self, ctx, usuario: discord.Member, peso: int):
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)
        datos.setdefault(server_id, {})
        datos[server_id].setdefault("weights", {})

        key = _user_key(usuario.id)
        if peso <= 1:
        # eliminar/restablecer a 1
            if key in datos[server_id]["weights"]:
                del datos[server_id]["weights"][key]
                guardar_json(config_file, datos)
                await ctx.respond(f"🔁 Peso de {usuario.display_name} restablecido/eliminado (ahora es 1).", ephemeral=False)
            else:
                await ctx.respond("ℹ️ No había peso personalizado para ese usuario.", ephemeral=True)
        else:
            datos[server_id]["weights"][key] = int(peso)
            guardar_json(config_file, datos)
            await ctx.respond(f"✅ Ahora el voto de {usuario.display_name} vale por **{peso}**.", ephemeral=False)


    @discord.slash_command(description="(MOD) Edita los votos que necesita un jugador para ser linchado. Ej: -2, -1, 0, 1, 2.")
    @discord.default_permissions(administrator=True)
    @option("usuario", description="Usuario al que aplicar el threshold", type=discord.Member)
    @option("multiplicador", description="Ej: 1.0 (default), 1.25, 1.5", required=True)
    async def set_vida_jugador(self, ctx, usuario: discord.Member, offset: int):
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)
        datos.setdefault(server_id, {})
        datos[server_id].setdefault("thresholds", {})

        key = _user_key(usuario.id)
        if offset == 0:
            # eliminar/restablecer
            if key in datos[server_id]["thresholds"]:
                del datos[server_id]["thresholds"][key]
                guardar_json(config_file, datos)
                await ctx.respond(f"🔁 Votos adicionales de {usuario.display_name} restablecidos a 0 (default).", ephemeral=False)
            else:
                await ctx.respond("ℹ️ No habían votos adicionales para ese usuario.", ephemeral=True)
        else:
            datos[server_id]["thresholds"][key] = int(offset)
            guardar_json(config_file, datos)
            await ctx.respond(f"✅ Ahora {usuario.display_name} necesita **{offset}** voto(s) adicional(es) para ser linchado.", ephemeral=False)


    @discord.slash_command(description="Vota por otro jugador.")
    @option("jugador", description="Selecciona al jugador que deseas votar.", type=discord.Member)
    async def votar(self, ctx, jugador: discord.Member):
        """Permite a un jugador votar por otro jugador."""

        # --- Cargar datos y verificar rol registrado ---
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        # --- Verificar configuraciones básicas ---
        if server_id not in datos or "rol_jugador" not in datos[server_id]:
            await ctx.respond("⚠️ No se ha registrado un rol de jugador en este servidor.", ephemeral=True)
            return

        if server_id not in datos or "rol_muerto" not in datos[server_id]:
            await ctx.respond("⚠️ No se ha registrado un rol de muerto en este servidor.", ephemeral=True)
            return

        if "canal_juego" not in datos[server_id]:
            await ctx.respond("⚠️ No se ha registrado un canal de juego en este servidor.", ephemeral=True)
            return

        # --- Validar canal ---
        canal_juego_id = datos[server_id]["canal_juego"]
        if ctx.channel.id != canal_juego_id:
            await ctx.respond("🚫 Solo puedes votar en el canal de juego.", ephemeral=True)
            return

        rol_id = datos[server_id]["rol_jugador"]
        canal_juego_id = datos[server_id]["canal_juego"]

        rol_jugador = ctx.guild.get_role(rol_id)
        canal_juego = ctx.guild.get_channel(canal_juego_id)

        # --- Requisitos de rol ---
        if not rol_jugador:
            await ctx.respond("⚠️ El rol de jugador registrado ya no existe en el servidor.", ephemeral=True)
            return

        # El usuario que vota debe tener el rol
        if rol_jugador not in ctx.author.roles:
            await ctx.respond("🚫 Solo los jugadores pueden votar.", ephemeral=True)
            return

        # El usuario votado también debe tener el rol
        if rol_jugador not in jugador.roles:
            await ctx.respond("🚫 Solo puedes votar por otro jugador.", ephemeral=True)
            return

        '''# No puedes votarte a ti mismo
        if jugador.id == ctx.author.id:
            await ctx.respond("🙃 No puedes votarte a ti mismo.", ephemeral=True)
            return'''

        # --- Registrar voto ---
        if "votos" not in datos[server_id]:
            datos[server_id]["votos"] = {}

        datos[server_id]["votos"][str(ctx.author.id)] = str(jugador.id)
        guardar_json(config_file, datos)

        await ctx.respond(f"🗳️ Has votado por **{jugador.display_name}**.", ephemeral=False)

        # --- Verificar mayoría usando votos ponderados ---
        jugadores = [m for m in ctx.guild.members if rol_jugador in m.roles]

        # Calcular el total ponderado posible (la suma de pesos de todos los jugadores)
        total_ponderado = 0
        for j in jugadores:
            total_ponderado += obtener_peso_votante(j, datos, server_id)

        base = (total_ponderado // 2) + 1  # mayoría absoluta ponderada

        conteo = {}  # votado_id -> total ponderado recibido
        votos = datos[server_id].get("votos", {})
        for votante_id, votado_id in votos.items():
            votante_member = ctx.guild.get_member(int(votante_id))
            peso = obtener_peso_votante(votante_member, datos, server_id) if votante_member else 1
            conteo[votado_id] = conteo.get(votado_id, 0) + peso

        # Comprobar thresholds offset y decidir ganador
        ganador_id = None
        ganador_total = 0
        ganador_needed = 0
        for votado_id, total_votes in conteo.items():
            votado_member = ctx.guild.get_member(int(votado_id))
            offset = obtener_threshold_offset(votado_member, datos, server_id) if votado_member else 0
            needed = max(1, base + offset)
            if total_votes >= needed:
                ganador_id = votado_id
                ganador_total = total_votes
                ganador_needed = needed
                break

        if ganador_id:
            ganador = ctx.guild.get_member(int(ganador_id))
            overwrite = canal_juego.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = False
            await canal_juego.set_permissions(ctx.guild.default_role, overwrite=overwrite)

            # Cambiar rol de jugador cuando sea linchado.
            if "rol_muerto" in datos[server_id]:
                rol_muerto = ctx.guild.get_role(datos[server_id]["rol_muerto"])
                rol_jugador = ctx.guild.get_role(datos[server_id]["rol_jugador"])

                if rol_muerto and ganador:
                    await ganador.add_roles(rol_muerto)
                    await ganador.remove_roles(rol_jugador)

                    nombre = ganador.display_name if ganador else f"Usuario {ganador_id}"
                    #await canal_juego.send(f":fire: :farmer: **{nombre}** ha alcanzado la mayoría ({ganador_total} ≥ {ganador_needed}).\n🔒 El canal ha sido bloqueado.")
                    await canal_juego.send(f":fire: :farmer: **{nombre}** ha alcanzado la mayoría de votos.")
                    await canal_juego.send(f"💀 **{ganador.display_name}** ha sido linchado y ahora está muerto. \n\n:city_sunset: El día ha terminado.")

            guardar_json(config_file, datos)
            return


    @discord.slash_command(description="Retira tu voto para linchar.")
    async def quitar_voto(self, ctx):
        """Permite a un jugador eliminar su voto ya emitido."""
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        # Verificar que exista configuracion para este server y rol_jugador
        if server_id not in datos or "rol_jugador" not in datos[server_id]:
            await ctx.respond("⚠️ No se ha registrado un rol de jugador en este servidor.", ephemeral=True)
            return

        canal_juego_id = datos[server_id]["canal_juego"]
        if ctx.channel.id != canal_juego_id:
            await ctx.respond("🚫 Solo puedes quitar tu voto en el canal de juego.", ephemeral=True)
            return

        rol_id = datos[server_id]["rol_jugador"]
        rol_jugador = ctx.guild.get_role(rol_id)
        if not rol_jugador:
            await ctx.respond("⚠️ El rol de jugador registrado ya no existe en el servidor.", ephemeral=True)
            return

        # Verificar que el autor tenga el rol de jugador
        if rol_jugador not in ctx.author.roles:
            await ctx.respond("🚫 Solo los jugadores pueden quitar su voto.", ephemeral=True)
            return

        # Verificar si hay votos en este servidor
        if "votos" not in datos[server_id] or not datos[server_id]["votos"]:
            await ctx.respond("ℹ️ Aún no hay votos registrados.", ephemeral=True)
            return

        votante_id = str(ctx.author.id)
        if votante_id not in datos[server_id]["votos"]:
            await ctx.respond("ℹ️ No tienes ningún voto registrado para quitar.", ephemeral=True)
            return

        # Eliminar el voto del usuario
        del datos[server_id]["votos"][votante_id]

        # Si 'votos' quedó vacío, lo dejamos como {} o lo eliminamos — opcional.
        # Aquí lo dejamos como dict vacío; si prefieres, puedes quitar la clave:
        #if not datos[server_id]["votos"]:
            # opcional: eliminar la clave "votos" para mantener JSON más limpio
        #    del datos[server_id]["votos"]

        guardar_json(config_file, datos)
        await ctx.respond("✅ Has retirado tu voto.", ephemeral=False)

    @discord.slash_command(description="(MOD) Limpia todos los votos.")
    @discord.default_permissions(administrator=True)
    async def limpiar_votos(self, ctx):
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        if server_id in datos and "votos" in datos[server_id]:
            del datos[server_id]["votos"]
            guardar_json(config_file, datos)
            await ctx.respond("🧹 Todos los votos han sido eliminados.", ephemeral=False)
        else:
            await ctx.respond("ℹ️ No hay votos que eliminar.", ephemeral=True)

    @discord.slash_command(description="Muestra el estado actual de la votación.")
    async def status_votos(self, ctx):
        await ctx.defer()

        """Muestra cuántos votos tiene cada jugador y quiénes votaron por ellos."""
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        # Verificar si hay datos y votos
        if (
            server_id not in datos
            or "rol_jugador" not in datos[server_id]
        ):
            await ctx.respond("⚠️ No se ha registrado ningún rol de jugador en este servidor.", ephemeral=True)
            return

        rol_id = datos[server_id]["rol_jugador"]
        rol_jugador = ctx.guild.get_role(rol_id)
        if not rol_jugador:
            await ctx.respond("⚠️ El rol de jugador registrado ya no existe en el servidor.", ephemeral=True)
            return

        votos = datos[server_id].get("votos", {})

        if not votos:
            await ctx.respond("🗳️ No hay votos registrados todavía.", ephemeral=False)
            return

        # --- Calcular total ponderado de jugadores ---
        jugadores = [m for m in ctx.guild.members if rol_jugador in m.roles]

        total_ponderado = 0
        for j in jugadores:
            total_ponderado += obtener_peso_votante(j, datos, server_id)

        base = (total_ponderado // 2) + 1  # mayoría absoluta ponderada

        # --- Invertir votos y calcular totales ponderados ---
        conteo = {}  # votado_id -> lista de (votante_id, peso)
        for votante_id, votado_id in votos.items():
            votante_member = ctx.guild.get_member(int(votante_id))
            peso = obtener_peso_votante(votante_member, datos, server_id) if votante_member else 1
            conteo.setdefault(votado_id, []).append((votante_id, peso))

        mensaje = "📊 **Estado actual de la votación:**\n"
        mensaje += f"Se necesitan **{base} votos** para cerrar la votación.\n\n"

        # --- Mostrar cada jugador votado ---
        for votado_id, votantes in sorted(conteo.items(), key=lambda x: sum(p for _, p in x[1]), reverse=True):
            votado = ctx.guild.get_member(int(votado_id))
            nombre_votado = votado.display_name if votado else f"Usuario {votado_id}"

            # Calcular total ponderado recibido
            total_ponderado_recibido = sum(p for _, p in votantes)

            # Threshold personalizado
            offset = obtener_threshold_offset(votado, datos, server_id) if votado else 0
            needed = max(1, base + offset)

            lista_votantes = []
            for v_id, peso in votantes:
                miembro = ctx.guild.get_member(int(v_id))
                nombre_votante = miembro.display_name if miembro else f"Usuario {v_id}"
                if peso > 1:
                    lista_votantes.append(f"{nombre_votante} (x{peso})")
                else:
                    lista_votantes.append(nombre_votante)

            palabra = "voto" if total_ponderado_recibido == 1 else "votos"
            mensaje += (
                f"**{nombre_votado}** ({total_ponderado_recibido} {palabra} de {needed} votos necesarios.): "
                f"{', '.join(lista_votantes)}\n"
            )

        await ctx.followup.send(mensaje)


    @discord.slash_command(description="(MOD) Muestra todos los jugadores con su peso de voto y threshold, incluyendo muertos.")
    @discord.default_permissions(administrator=True)
    async def status_jugadores(self, ctx):
        """Muestra todos los jugadores (vivos, muertos o ausentes) con su peso y threshold."""
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        if server_id not in datos or "rol_jugador" not in datos[server_id]:
            await ctx.respond("⚠️ No se ha configurado el rol de jugador en este servidor.", ephemeral=True)
            return

        rol_id = datos[server_id]["rol_jugador"]
        rol_jugador = ctx.guild.get_role(rol_id)
        if not rol_jugador:
            await ctx.respond("⚠️ El rol de jugador configurado ya no existe.", ephemeral=True)
            return

        # --- Obtener todos los jugadores vivos (rol actual) ---
        jugadores_vivos = [m for m in ctx.guild.members if rol_jugador in m.roles]

        # --- Obtener datos guardados del JSON ---
        weights = datos[server_id].get("weights", {})
        thresholds = datos[server_id].get("thresholds", {})

        mensaje = "📋 **Estado de los jugadores:**\n\n"

        # --- Combinar jugadores del JSON y del servidor ---
        jugadores_ids = set()
        jugadores_ids.update(int(k.replace("user_", "")) for k in weights.keys())
        jugadores_ids.update(int(k.replace("user_", "")) for k in thresholds.keys())

        # Agregar también jugadores vivos que no estén en el JSON
        jugadores_ids.update([m.id for m in jugadores_vivos])

        # --- Construir lista ---
        for jugador_id in sorted(jugadores_ids):
            miembro = ctx.guild.get_member(jugador_id)
            clave = f"user_{jugador_id}"

            # Valores por defecto
            peso = weights.get(clave, 1)
            offset = thresholds.get(clave, 0)

            # Normalizar tipos
            try:
                peso = int(peso)
                if peso < 1:
                    peso = 1
            except:
                peso = 1

            try:
                offset = int(offset)
            except:
                offset = 0

            # Signo del threshold
            signo = f"{offset:+d}"  # Esto garantiza que se muestre el signo (+ o -)

            # Estado del jugador
            if miembro:
                nombre = miembro.display_name
                if rol_jugador in miembro.roles:
                    estado_icono = "🟢"
                else:
                    estado_icono = "💀"
            else:
                nombre = f"(ID: {jugador_id})"
                estado_icono = "🕸️"

            mensaje += f"{estado_icono} **{nombre}** → 🏋️ Peso: `{peso}` | 🎯 Threshold: `{signo}`\n"

        mensaje += f"\n👥 Total registrados: {len(jugadores_ids)}"
        await ctx.respond(mensaje, ephemeral=False)



    @discord.slash_command(description="Muestra todos los jugadores vivos y muertos.")
    async def lista_de_jugadores(self, ctx):
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        # Verificar que existan los roles configurados
        if server_id not in datos:
            await ctx.respond("⚠️ No se ha configurado este servidor en la base de datos.", ephemeral=True)
            return

        def obtener_rol(nombre_campo: str, descripcion: str):
            """Devuelve el rol configurado o responde con error."""
            if nombre_campo not in datos[server_id]:
                raise ValueError(f"⚠️ No se ha configurado el rol de {descripcion}.")
            rol = ctx.guild.get_role(datos[server_id][nombre_campo])
            if not rol:
                raise ValueError(f"⚠️ El rol de {descripcion} configurado ya no existe.")
            return rol

        try:
            rol_jugador = obtener_rol("rol_jugador", "jugador")
            rol_muerto = obtener_rol("rol_muerto", "muerto")
        except ValueError as e:
            await ctx.respond(str(e), ephemeral=True)
            return

        # Clasificar los miembros del servidor
        vivos = []
        muertos = []
        for miembro in ctx.guild.members:
            if rol_muerto in miembro.roles:
                muertos.append(miembro)
            elif rol_jugador in miembro.roles:
                vivos.append(miembro)

        # Construir los mensajes
        if not vivos and not muertos:
            await ctx.respond("ℹ️ No hay jugadores registrados con los roles configurados.", ephemeral=True)
            return

        mensaje = "## Lista de jugadores vivos: ##\n"
        if vivos:
            mensaje += "\n".join(f"- **{m.display_name}**" for m in sorted(vivos, key=lambda x: x.display_name.lower()))
        else:
            mensaje += "- Nadie 😢"

        mensaje += f"\n\n👥 Total jugadores vivos: {len(vivos)}\n\n\n"
        mensaje += "## Lista de jugadores muertos: ## \n"

        if muertos:
            mensaje += "\n".join(f"- **{m.display_name}**" for m in sorted(muertos, key=lambda x: x.display_name.lower()))
        else:
            mensaje += "- Nadie 👻"

        mensaje += f"\n\n:skull: Total fiambres: {len(muertos)}"

        await ctx.respond(mensaje, ephemeral=False)



    @discord.slash_command(description="(MOD) Muestra los canales y roles actualmente configurados (acciones, votaciones, jugador, muerto).")
    @discord.default_permissions(administrator=True)
    async def status_config(self, ctx):
        """Muestra los canales y roles actualmente configurados (acciones, votaciones, jugador, muerto)."""
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        if server_id not in datos:
            await ctx.respond("⚠️ No hay configuraciones guardadas para este servidor.", ephemeral=True)
            return

        cfg = datos[server_id]

        # Buscar canales y roles si existen
        canal_acciones = ctx.guild.get_channel(cfg.get("canal_acciones"))
        canal_juego = ctx.guild.get_channel(cfg.get("canal_juego"))
        rol_jugador = ctx.guild.get_role(cfg.get("rol_jugador"))
        rol_muerto = ctx.guild.get_role(cfg.get("rol_muerto"))

        # Armar respuesta con menciones o avisos
        def fmt(item, tipo):
            if item:
                return f"{item.mention} (`{item.id}`)"
            else:
                #return f"⚠️ *No configurado* ({tipo})"
                return f"⚠️ *No configurado*"

        mensaje = (
            "🧾 **Configuración actual del servidor:**\n\n"
            f"• 🎯 **Canal de acciones:** {fmt(canal_acciones, 'canal')}\n"
            f"• 🗳️ **Canal de juego:** {fmt(canal_juego, 'canal')}\n"
            f"• 🧍 **Rol de jugadores:** {fmt(rol_jugador, 'rol')}\n"
            f"• 💀 **Rol de muertos:** {fmt(rol_muerto, 'rol')}\n"
        )

        await ctx.respond(mensaje, ephemeral=False)


    # ----------------------------------------------------------
    # Iniciar día (bloquea canal + limpia votos si es para terminar el día)
    # ----------------------------------------------------------
    @discord.slash_command(description="(MOD) Desbloquea el canal (si inicia un día, sino no) y limpia todos los votos.")
    @discord.default_permissions(administrator=True)
    @option("fase", str, description="Día o noche", choices=[
            discord.OptionChoice("dia"),
            discord.OptionChoice("noche")
        ]
    )
    async def fase_iniciar(self, ctx, fase):
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        # --- Verificar configuraciones ---
        if server_id not in datos or "canal_juego" not in datos[server_id]:
            await ctx.respond("⚠️ No se ha registrado un canal de juego en este servidor.", ephemeral=True)
            return

        canal_juego_id = datos[server_id]["canal_juego"]
        canal_juego = ctx.guild.get_channel(canal_juego_id)

        if not canal_juego:
            await ctx.respond("⚠️ El canal de juego configurado ya no existe.", ephemeral=True)
            return

        # --- Limpiar votos ---
        if "votos" in datos[server_id]:
            datos[server_id]["votos"] = {}
            guardar_json(config_file, datos)
        

        if fase == "dia":
            await ctx.respond(f"🔓 El canal {canal_juego.mention} ha sido desbloqueado.")

            await canal_juego.send(":sunrise_over_mountains: **Ha iniciado un nuevo día.** Pueden usar sus habilidades diurnas.")

            # --- Desbloquear canal ---
            overwrite = canal_juego.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = True
            await canal_juego.set_permissions(ctx.guild.default_role, overwrite=overwrite)

        elif fase == "noche":
            await canal_juego.send(":night_with_stars: **Ha iniciado una nueva noche.** Pueden usar sus habilidades nocturnas.")
        


    # ----------------------------------------------------------
    # Terminar día (bloquea canal solamente)
    # ----------------------------------------------------------

    @discord.slash_command(description="(MOD) Cierra el canal para que no se puedan enviar más mensajes. No borra los votos guardados.")
    @discord.default_permissions(administrator=True)
    async def fase_terminar_dia(self, ctx):
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        if server_id not in datos or "canal_juego" not in datos[server_id]:
            await ctx.respond("⚠️ No hay un canal de juego registrado.", ephemeral=True)
            return

        canal_juego = ctx.guild.get_channel(datos[server_id]["canal_juego"])
        if not canal_juego:
            await ctx.respond("⚠️ El canal registrado ya no existe.", ephemeral=True)
            return
        
        try:
            overwrite = canal_juego.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = False
            await canal_juego.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        except:
            pass

        await ctx.respond(f":city_dusk: El día ha terminado. El canal {canal_juego.mention} ha sido bloqueado.", ephemeral=False)

    @discord.slash_command(description="Lanza un dado de X cantidad de caras. (Por defecto: 6 caras)")
    async def dado(self, ctx, caras: int = 6):
        if caras < 2:
            await ctx.respond("⚠️ El dado debe tener al menos 2 caras.", ephemeral=True)
            return

        if caras > 100:
            await ctx.respond("⚠️ El dado no puede tener más de 100 caras.", ephemeral=True)
            return
        
        dado1 = random.randint(1, caras)
        dado2 = random.randint(1, caras)
        dado3 = random.randint(1, caras)
        dado_final = random.choice([dado1, dado2, dado3])

        await ctx.respond(f"🎲 Rueda el dado de {caras} caras y cae un... **{dado_final}**")

    @discord.slash_command(description="(MOD) Necesitas saber cómo funciona el bot? Empieza por acá.")
    @discord.default_permissions(administrator=True)
    async def introduccion_al_bot(self, ctx):
        
        '''await ctx.respond("Este bot implementa el sistema de votaciones y gestión de fases (día/noche) de un juego tipo **Mafia** / **Werewolf** en Discord." +
            "Permite registrar canales, roles, cambiar el valor de los votos, cambiar cuántos votos necesita un jugador para ser linchado y manejar automáticamente el flujo del juego." + 
            "\n\n\nPara empezar, debes registrar los canales y roles relacionados con el juego:\n\n" + 
            "- `/set_canal_juego canal:<TextChannel>` -  Registra el canal donde se desarrollará el juego.\n" + 
            "- `/set_rol_jugadores rol:<Role>` -  Asigna el rol que tendrán los jugadores vivos.\n" +
            "- `/set_rol_muertos rol:<Role>` -  Asigna el rol que tendrán los jugadores muertos.\n" 
            )'''

        embed = discord.Embed(
            title="🧾 Guía del Sistema de Juego — MafiaBot",
            description="Aquí tienes una guía rápida de todos los comandos y su función dentro del sistema de **Mafia**.",
            color=discord.Color.gold()
        )
        embed.set_author(name="MafiaBot", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        embed.set_footer(text="Desarrollado por Khaeroth (https://github.com/Khaeroth)")

        # --- Explicación ---
        embed.add_field(
            name="¿Cómo funciona?",
            value=(
                "- El bot gestiona el juego a través de un canal designado como `canal de juego` y de roles para `jugador` y posteriormente `muertos`.\n"
                "- Allí, los usuarios con rol de `jugador` podrán debatir y luego votar para linchar a alguien.\n"
                "- Las votaciones toman en cuenta el número de `jugadores` para calcular cuántos votos hacen falta para linchar.\n"
                "- Si un `jugador` es linchado, este perderá su rol y pasará a tener rol de `muerto`.\n"
                "- Los usuarios `muertos` no se tendrán en cuenta para el cálculo de votos al linchar.\n"
                "- Si necesitas, puedes cambiar el valor del voto de un jugador en específico, o también cuántos votos hacen falta para linchar a alguien (menos votos o más votos).\n"
                "- También puedes usar el bot para las fases de día y noche. Estos cambian los permisos del canal para que los usuarios no puedan seguir enviando mensajes durante la noche. Al iniciar el día, se limpian los votos del día anterior y se restauran los permisos.\n"
            ),
            inline=False
        )

        # --- Flujo ---
        embed.add_field(
            name="🧩 Flujo del juego",
            value=(
                ":one: Crea los canales y roles en el servidor de Discord."
                ":two: Configura canales y roles con el bot.\n"
                ":three: Inicia el día con `/fase_iniciar dia`.\n"
                ":four: Los jugadores debaten y luego votan con (`/votar`).\n"
                ":five: Si alguien alcanza la mayoría → linchamiento automático.\n"
                ":six: Cierra el día con `/fase_terminar_dia`.\n"
                ":seven: Inicia la noche con `/fase_iniciar noche`.\n"
            ),
            inline=False
        )

        # --- Configuración inicial ---
        embed.add_field(
            name="⚙️ Configuración inicial",
            value=(
                "1️⃣ `/set_canal_juego #canal` — Define el canal donde se jugará.\n"
                "2️⃣ `/set_rol_jugadores @Rol` — Define el rol de los jugadores vivos.\n"
                "3️⃣ `/set_rol_muertos @Rol` — Define el rol de los jugadores muertos.\n"
                "4️⃣ `/status_config` — Muestra la configuración actual.\n"
                "5️⃣ `/reset_config` — Reinicia toda la configuración del servidor.\n"
            ),
            inline=False
        )

        # --- Fases ---
        embed.add_field(
            name="🌅 Fases del juego",
            value=(
                "`/fase_iniciar dia` — Limpia votos y desbloquea el canal para el día.\n"
                "`/fase_iniciar noche` — Limpia votos (no desbloquea el canal) y anuncia el inicio de la noche.\n"
                "`/fase_terminar_dia` — Bloquea el canal al finalizar el día.\n"
                "*No hay comando para terminar la noche porque no tiene sentido. Solo usa `/fase_iniciar dia` directamente.*\n"
            ),
            inline=False
        )

        # --- Gestión de jugadores ---
        embed.add_field(
            name="👥 Gestión de jugadores",
            value=(
                "`/set_valor_voto_jugador @jugador peso` — Cambia cuánto vale el voto del jugador.\n"
                "`/set_vida_jugador @jugador offset` — Cambia cuántos votos necesita para ser linchado.\n"
                "`/status_jugadores` — Muestra todos los jugadores, pesos y 'vidas' configuradas.\n"
            ),
            inline=False
        )

        # --- Votaciones ---
        embed.add_field(
            name="🗳️ Votaciones",
            value=(
                "`/votar @jugador` — Vota por alguien.\n"
                "`/quitar_voto` — Retira tu voto actual.\n"
                "`/status_votos` — Muestra el conteo de votos actual.\n"
                "`/limpiar_votos` — Limpia todos los votos del servidor.\n"
            ),
            inline=False
        )

        # --- Si tienes el Cog de Acciones, lo explica: ---
        if os.path.exists("cogs/acciones.py"):
            embed.add_field(
            name=":dagger: Módulo de acciones",
            value=(
                "¡Has instalado el módulo de acciones! Con esto puedes gestionar un poco las habilidades de los usuarios.\n"
                "Puedes configurar un canal para llevar el registro de las habilidades que usan los jugadores.\n"
                "Los `jugadores` pueden usar el comando `/accion` para registrar el uso de sus habilidades. Estas se copiarán al canal designado.\n\n"
                "`/set_canal_acciones` — Define el canal donde se copiarán los mensajes.\n"
                "`/accion` - Registra una acción y la envía al canal designado.\n"
            ),
            inline=False
        )
        else:
            pass

        # --- Si tienes el Cog de Admin, lo explica: ---
        if os.path.exists("cogs/admin.py"):
            embed.add_field(
            name=":crown: Módulo de Moderación",
            value=(
                "¡Has instalado el módulo de moderación! Con esto puedes utilizar un par de comandos para tareas administrativas.\n"
                "`/anunciar` - Envía un mensaje al `canal de juego` configurado usando el bot. Puedes usarlo para dar avisos *anónimos* a los jugadores.\n"
                "`/borrar_mensajes` - Borra una cantidad de mensajes recientes del canal actual (máximo 100). \n"
                "`/cuenta_atras_iniciar` - Inicia una cuenta regresiva que enviará un aviso cuando termine el tiempo. Puede usarse para anunciar el tiempo que durará un día, o noche. Solo puede haber una cuenta regresiva a la vez.\n"
                "`/cuenta_atras_status` - Muestra cuánto tiempo falta para que termine la cuenta regresiva actual.\n"
                "`/cuenta_atras_cancelar` - Cancela la cuenta regresiva activa, si existe.\n"
                "`/ping` - Comprueba si el bot está respondiendo correctamente.\n"
            ),
            inline=False
        )
        else:
            pass

        # --- Notas ---
        embed.add_field(
            name="💡 Notas",
            value=(
                "- Los El `valor de los votos` no se puede configurar para ser menor que 1.\n"
                "- La `vida` puede ser **positiva o negativa**, pero que no sea menor a la cantidad de jugadores porque puede romper el juego.\n"
                "- La configuración se guarda con el bot, se mantiene en caso de que se caiga.\n"
                "- Hay un comando de `/dado` para lanzar un dado de entre 2 y 100 caras.\n"
                "- Solo los administradores pueden ver y usar los comandos que dicen `(MOD)` en la descripción."
            ),
            inline=False
        )

        await ctx.respond(embed=embed, ephemeral=False)
        pass

    @discord.slash_command(description="(MOD) Elimina toda la configuración del servidor.")
    @discord.default_permissions(administrator=True)
    async def reset_config(self, ctx):
        """Elimina toda la configuración del servidor actual del archivo JSON, con confirmación previa."""
        datos = cargar_json(config_file)
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
                datos = cargar_json(config_file)
                server_id = str(ctx.guild.id)

                if server_id in datos:
                    del datos[server_id]
                    guardar_json(config_file, datos)

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


# --- Setup del cog ---
def setup(bot):
    bot.add_cog(Votaciones(bot))
