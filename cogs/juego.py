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


    @discord.slash_command(description='(MOD) Configura el "peso" del voto a un jugador. 0= no puede votar, 1 = normal, 2 = doble, etc.')
    @discord.default_permissions(administrator=True)
    @option("usuario", description="Usuario al que asignar peso", type=discord.Member)
    @option("peso", description="Valor numérico. 0 = no puede votar, 1 = normal, 2+ = voto mejorado.", required=True)
    async def set_valor_voto_jugador(self, ctx, usuario: discord.Member, peso: int):
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)
        datos.setdefault(server_id, {})
        datos[server_id].setdefault("weights", {})

        key = _user_key(usuario.id)

        # --- CASO: peso 0 (no puede votar) ---
        if peso == 0:
            datos[server_id]["weights"][key] = 0
            guardar_json(config_file, datos)
            await ctx.respond(f"⛔ {usuario.display_name} **no podrá votar** (peso 0 asignado).")
            return

        # --- CASO: peso 1 (volver a normal) ---
        if peso == 1:
            # eliminar peso personalizado
            if key in datos[server_id]["weights"]:
                del datos[server_id]["weights"][key]
                guardar_json(config_file, datos)
                await ctx.respond(f"🔁 Peso de {usuario.display_name} restablecido a **1** (normal).")
            else:
                await ctx.respond("ℹ️ Ese usuario ya tenía el peso normal (1).", ephemeral=True)
            return

        # --- CASO: peso 2+ ---
        if peso > 1:
            datos[server_id]["weights"][key] = int(peso)
            guardar_json(config_file, datos)
            await ctx.respond(f"✅ Ahora el voto de {usuario.display_name} vale por **{peso}**.")
            return

        # --- Si ponen valores negativos ---
        await ctx.respond("❌ El peso no puede ser negativo. Usa 0 para deshabilitar el voto.", ephemeral=True)


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

        # --- Validar peso del votante (bloqueo si su peso = 0) ---
        votante_key = _user_key(ctx.author.id)
        peso_votante = datos[server_id].get("weights", {}).get(votante_key, 1)

        if peso_votante == 0:
            await ctx.respond(
                "⛔ No puedes votar.", ephemeral=False)
            return
        
        # Registrar por quién votó el usuario
        datos[server_id]["votos"][str(ctx.author.id)] = str(jugador.id)
        guardar_json(config_file, datos)

        await ctx.respond(f"🗳️ Has votado por **{jugador.display_name}**.", ephemeral=False)

        # --- Verificar mayoría simple ---
        jugadores = [m for m in ctx.guild.members if rol_jugador in m.roles]

        num_jugadores = len(jugadores)
        base = (num_jugadores // 2) + 1  # mayoría simple real

        # --- Contar votos ponderados ---
        conteo = {}
        votos = datos[server_id].get("votos", {})

        for votante_id, votado_id in votos.items():
            votante_member = ctx.guild.get_member(int(votante_id))

            #Obtener peso
            peso = obtener_peso_votante(votante_member, datos, server_id) if votante_member else 1

            conteo[votado_id] = conteo.get(votado_id, 0) + peso

        # --- Revisar si alguien alcanzó mayoría + threshold ---
        ganador_id = None
        ganador_total = 0
        ganador_needed = 0

        for votado_id, total_votes in conteo.items():
            votado_member = ctx.guild.get_member(int(votado_id))

            # Threshold individual (puede ser -2, -1, 0, +1, +2, etc.)
            offset = obtener_threshold_offset(votado_member, datos, server_id) if votado_member else 0
            # Ajustar mayoría según threshold

            needed = max(1, base + offset)

            if total_votes >= needed:
                ganador_id = votado_id
                ganador_total = total_votes
                ganador_needed = needed
                break

        if ganador_id:
            ganador = ctx.guild.get_member(int(ganador_id))
            #overwrite = canal_juego.overwrites_for(ctx.guild.default_role)
            overwrite = canal_juego.overwrites_for(rol_jugador)
            overwrite.send_messages = False
            #await canal_juego.set_permissions(ctx.guild.default_role, overwrite=overwrite)
            await canal_juego.set_permissions(rol_jugador, overwrite=overwrite)

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

    @discord.slash_command(description="Vota para terminar el día antes. Si votas, no lo podrás retirar hasta terminar el día.")
    async def votar_terminar_dia_antes(self, ctx):

        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        # Verificar config básica
        if server_id not in datos or "rol_jugador" not in datos[server_id]:
            return await ctx.respond("⚠️ No hay rol de jugadores configurado.", ephemeral=True)

        if "canal_juego" not in datos[server_id]:
            return await ctx.respond("⚠️ No se ha configurado el canal de juego.", ephemeral=True)

        # Canal válido
        canal_juego_id = datos[server_id]["canal_juego"]
        if ctx.channel.id != canal_juego_id:
            return await ctx.respond("🚫 Solo puedes votar en el canal de juego.", ephemeral=True)

        rol_jugador = ctx.guild.get_role(datos[server_id]["rol_jugador"])
        rol_muerto = ctx.guild.get_role(datos[server_id]["rol_muerto"])

        # Solo vivos pueden votar para terminar el día
        if rol_jugador not in ctx.author.roles:
            return await ctx.respond("🚫 Solo los jugadores vivos pueden votar para terminar el día.", ephemeral=True)

        # Obtener o crear estructura
        datos.setdefault(server_id, {})
        datos[server_id].setdefault("votos_fin_dia", {})

        votos_fin = datos[server_id]["votos_fin_dia"]

        # Registrar voto
        votos_fin[str(ctx.author.id)] = True
        guardar_json(config_file, datos)

        # Calcular mayoría simple (solo vivos)
        jugadores_vivos = [m for m in ctx.guild.members if rol_jugador in m.roles]
        total_vivos = len(jugadores_vivos)
        needed = (total_vivos // 2) + 1

        total_votos = len(votos_fin)

        await ctx.respond(
            f"🗳️ **{ctx.author.display_name}** ha votado para terminar el día.\n"
            f"Votos: **{total_votos}/{needed}**"
        )

        # ¿Se alcanzó la mayoría?
        if total_votos >= needed:
            canal_juego = ctx.guild.get_channel(canal_juego_id)

            # Bloquear el canal
            rol_everyone = ctx.guild.default_role  # @everyone
            roles_a_bloquear = [rol_everyone, rol_jugador, rol_muerto]

            for rol in roles_a_bloquear:
                if rol:
                    overwrite = canal_juego.overwrites_for(rol)
                    overwrite.send_messages = False
                    await canal_juego.set_permissions(rol, overwrite=overwrite)

            await canal_juego.send(
                f"🌅 **La mayoría ha votado para terminar el día ({total_votos}/{needed}).**\n"
                f"🔒 El canal ha sido bloqueado.\n"
                f"☀️ Termina el día."
            )

            # Reset votos
            datos[server_id]["votos_fin_dia"] = {}
            guardar_json(config_file, datos)


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

        try:
            del datos[server_id]["votos_fin_dia"]
        except:
            pass

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
        votos_fin_dia = datos[server_id].get("votos_fin_dia", {})

        # --- Calcular total ponderado de jugadores ---
        jugadores = [m for m in ctx.guild.members if rol_jugador in m.roles]
        
        cantidad_vivos = len(jugadores)
        base = (cantidad_vivos // 2) + 1  # mayoría simple

        if not votos and not votos_fin_dia:
            await ctx.respond(
                f"🗳️ No hay votos registrados todavía.\n"
                f"📌 Para cerrar la votación con **{cantidad_vivos} jugadores vivos** se necesitan **{base} votos**.",
                ephemeral=False)
            return

        # --- Invertir votos y calcular totales ponderados ---
        conteo = {}  # votado_id -> lista de (votante_id, peso)
        for votante_id, votado_id in votos.items():
            votante_member = ctx.guild.get_member(int(votante_id))
            peso = obtener_peso_votante(votante_member, datos, server_id) if votante_member else 1
            conteo.setdefault(votado_id, []).append((votante_id, peso))

        mensaje = "📊 **Estado actual de la votación:**\n"
        mensaje += f"Con **{cantidad_vivos} jugadores vivos** se necesitan **{base} votos** para cerrar la votación.\n\n"

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
                f"- **{nombre_votado}** ({total_ponderado_recibido} {palabra} de {needed} votos necesarios.): "
                f"{', '.join(lista_votantes)}\n"
            )
        ##############################################################################################################

        # --- Mostrar votos para terminar el día antes ---
        votos_fin_dia = datos[server_id].get("votos_fin_dia", {})

        # Filtrar solo jugadores vivos
        votantes_fin_dia_validos = [
            ctx.guild.get_member(int(v_id))
            for v_id in votos_fin_dia.keys()
            if ctx.guild.get_member(int(v_id)) in jugadores
        ]

        cantidad_fin_dia = len(votantes_fin_dia_validos)
        faltan = max(0, base - cantidad_fin_dia)

        # Construir lista de nombres
        nombres_fin_dia = []
        for miembro in votantes_fin_dia_validos:
            nombres_fin_dia.append(miembro.display_name)

        mensaje += "\n\n⏳ **Votos para terminar el día antes:**\n"
        if cantidad_fin_dia < base:
            palabra = "voto" if cantidad_fin_dia == 1 else "votos"
            mensaje += f"Se necesitan **{faltan} {palabra} más** para cerrar el día anticipadamente.\n\n"
        else:
            mensaje += f"🟩 **¡Se alcanzó el mínimo de {base} votos!** El día puede finalizar anticipadamente.\n\n"

        if cantidad_fin_dia == 0:
            mensaje += "- **Nadie** ha votado aún para finalizar el día anticipadamente.\n"
        else:
            mensaje += f"- **Votos:** {cantidad_fin_dia} ({', '.join(nombres_fin_dia)})\n"

        


        await ctx.followup.send(mensaje)

    @discord.slash_command(description="(MOD) Muestra todos los jugadores con su peso de voto y threshold, incluyendo muertos.")
    @discord.default_permissions(administrator=True)
    async def status_jugadores(self, ctx):
        """Muestra todos los jugadores con su peso y threshold."""
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        server_data = datos.setdefault(server_id, {})
        server_data.setdefault("weights", {})
        server_data.setdefault("thresholds", {})

        pesos = server_data["weights"]
        thresholds = server_data["thresholds"]

        # Obtener roles desde el JSON
        rol_vivo_id = server_data.get("rol_jugador")
        rol_muerto_id = server_data.get("rol_muerto")

        if not rol_vivo_id and not rol_muerto_id:
            return await ctx.respond("⚠️ No hay roles de vivo/muerto configurados.", ephemeral=True)

        rol_vivo = ctx.guild.get_role(rol_vivo_id) if rol_vivo_id else None
        rol_muerto = ctx.guild.get_role(rol_muerto_id) if rol_muerto_id else None

        vivos = rol_vivo.members if rol_vivo else []
        muertos = rol_muerto.members if rol_muerto else []

        # Construcción de filas
        filas = []

        # Encabezado de la tabla
        filas.append(f"{'Estado':<8} | {'Jugador':<20} | {'Peso':<4} | {'Threshold':<9}")
        filas.append("-" * 50)

        # Función de acceso seguro
        def obtener(uid, dicc, default):
            return dicc.get(uid, default)

        # Agregar vivos primero
        for m in vivos:
            uid = _user_key(m.id)
            peso = obtener(uid, pesos, 1)
            th = obtener(uid, thresholds, 0)

            filas.append(f"{'Vivo':<8} | {m.display_name:<20} | {peso:<4} | {th:<9}")

        # Luego muertos
        for m in muertos:
            uid = _user_key(m.id)
            peso = obtener(uid, pesos, 1)
            th = obtener(uid, thresholds, 0)

            filas.append(f"{'Muerto':<8} | {m.display_name:<20} | {peso:<4} | {th:<9}")

        tabla = "```\n" + "\n".join(filas) + "\n```"

        embed = discord.Embed(
            title="📊 Estado de los jugadores",
            description=tabla,
            color=discord.Color.dark_blue()
        )

        await ctx.respond(embed=embed)


    @discord.slash_command(description="Muestra todos los jugadores vivos y muertos.")
    async def lista_de_jugadores(self, ctx):
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        if server_id not in datos:
            await ctx.respond("⚠️ No se ha configurado este servidor en la base de datos.", ephemeral=True)
            return

        def obtener_rol(nombre_campo: str, descripcion: str):
            if nombre_campo not in datos[server_id]:
                raise ValueError(f"⚠️ No se ha configurado el rol de {descripcion}.")
            rol = ctx.guild.get_role(datos[server_id][nombre_campo])
            if not rol:
                raise ValueError(f"⚠️ El rol de {descripcion} configurado ya no existe.")
            return rol

        try:
            rol_vivo = obtener_rol("rol_jugador", "jugador")
            rol_muerto = obtener_rol("rol_muerto", "muerto")
        except ValueError as e:
            await ctx.respond(str(e), ephemeral=True)
            return

        # Clasificar miembros
        vivos = sorted([m for m in ctx.guild.members if rol_vivo in m.roles], key=lambda x: x.display_name.lower())
        muertos = sorted([m for m in ctx.guild.members if rol_muerto in m.roles], key=lambda x: x.display_name.lower())

        if not vivos and not muertos:
            return await ctx.respond("ℹ️ No hay jugadores registrados con los roles configurados.", ephemeral=True)

        # TABLA
        filas = []
        filas.append(f"{'Estado':<7}   | {'Jugador':<20}")
        filas.append("-" * 32)

        for m in vivos:
            filas.append(f"🟢 Vivo   | {m.display_name:<20}")

        for m in muertos:
            filas.append(f"⚫ Muerto | {m.display_name:<20}")

        tabla = "```\n" + "\n".join(filas) + "\n```"

        embed = discord.Embed(
            title="📋 Lista de Jugadores",
            description=(
                f"**Vivos:** {len(vivos)}\n"
                f"**Fiambres:** {len(muertos)}\n\n"
                f"{tabla}"
            ),
            color=discord.Color.teal()
        )

        await ctx.respond(embed=embed)


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

        # Formateador
        def fmt(item):
            return item.mention if item else "⠀⚠️ *No configurado*"

        # Crear embed
        embed = discord.Embed(
            title="🧾 Configuración del Servidor",
            description="Estado actual de los canales y roles configurados.",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="🎯 Canal de acciones",
            value=f"⠀⠀⠀{fmt(canal_acciones)}",
            inline=False
        )

        embed.add_field(
            name="🗳️ Canal de juego",
            value=f"⠀⠀⠀{fmt(canal_juego)}",
            inline=False
        )

        embed.add_field(
            name="🧍 Rol de jugadores",
            value=f"⠀⠀⠀{fmt(rol_jugador)}",
            inline=False
        )

        embed.add_field(
            name="💀 Rol de muertos",
            value=f"⠀⠀⠀{fmt(rol_muerto)}",
            inline=False
        )

        embed.set_footer(text=f"Servidor: {ctx.guild.name}")

        await ctx.respond(embed=embed, ephemeral=False)

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

        if "rol_jugador" not in datos[server_id]:
            await ctx.respond("⚠️ No se ha registrado un rol de jugador.", ephemeral=True)
            return

        rol_jugadores_id = datos[server_id].get("rol_jugador")
        rol_jugadores = ctx.guild.get_role(rol_jugadores_id)


        if not canal_juego:
            await ctx.respond("⚠️ El canal de juego configurado ya no existe.", ephemeral=True)
            return

        # --- Limpiar votos ---
        datos[server_id]["votos_fin_dia"] = {}

        if "votos" in datos[server_id]:
            datos[server_id]["votos"] = {}
        
        guardar_json(config_file, datos)
        

        if fase == "dia":
            await ctx.respond(f"🔓 El canal {canal_juego.mention} ha sido desbloqueado.")

            await canal_juego.send(":sunrise_over_mountains: **Ha iniciado un nuevo día.** Pueden usar sus habilidades diurnas.")

            # --- Desbloquear canal ---
            #overwrite = canal_juego.overwrites_for(rol_jugadores)
            #overwrite.send_messages = True
            #await canal_juego.set_permissions(rol_jugadores, overwrite=overwrite)
            await canal_juego.set_permissions(rol_jugadores, send_messages=True)

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

        if "rol_jugador" not in datos[server_id]:
            await ctx.respond("⚠️ No se ha registrado un rol de jugador.", ephemeral=True)
            return

        rol_jugadores_id = datos[server_id].get("rol_jugador")
        rol_jugadores = ctx.guild.get_role(rol_jugadores_id)
        
        # Bloquear a @everyone
        await canal_juego.set_permissions(ctx.guild.default_role, send_messages=False)

        # Bloquear al rol de jugadores
        await canal_juego.set_permissions(rol_jugadores, send_messages=False)

        await ctx.respond(f":city_dusk: El día ha terminado. El canal {canal_juego.mention} ha sido bloqueado.")


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

    @discord.slash_command(description="Elige un usuario al azar entre los que tienen un rol específico.")
    @option("rol", discord.Role, description="Rol del que se elegirá un usuario al azar")
    async def ruleta_jugadores(self, ctx, rol: discord.Role):

        # Obtener todos los miembros del servidor que tengan el rol
        miembros = [m for m in ctx.guild.members if rol in m.roles]

        if not miembros:
            await ctx.respond(f"⚠️ No hay usuarios con el rol {rol.mention}.")
            return
        
        elegido = random.choice(miembros)
        await ctx.respond(f":game_die: El usuario elegido al azar fue: **{elegido.mention}**")

    @discord.slash_command(name="choose",description="Elige una opción al azar entre varias que escribas.")
    @option("opciones",str,description="Escribe varias opciones separadas por espacios.",required=True)
    async def choose(self, ctx, opciones: str):
        # Dividir las opciones por espacios
        lista = opciones.split()

        if len(lista) < 2:
            await ctx.respond("⚠️ Debes escribir al menos **dos opciones**.")
            return

        elegido = random.choice(lista)
        await ctx.respond(f"🎲 La opción elegida al azar es: **{elegido}**")


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
                "- También puedes usar el bot para las fases de día y noche. Estos cambian los permisos del canal durante la noche. Al iniciar el día, se limpian los votos del día anterior y se restauran los permisos.\n"
                "- Incluye un comando para que los jugadores puedan votar y terminar el día antes, en caso de que no puedan llegar a un acuerdo.\n"
            ),
            inline=False
        )

        # --- Flujo ---
        embed.add_field(
            name="🧩 Flujo del juego",
            value=(
                ":one: Crea los canales y roles en el servidor de Discord.\n"
                ":two: Configura canales y roles con el bot.\n"
                ":three: Inicia el día con `/fase_iniciar dia`.\n"
                ":four: Los jugadores debaten y luego votan con (`/votar`).\n"
                ":five: Si alguien alcanza la mayoría → linchamiento automático.\n"
                ":six: Cierra el día con `/fase_terminar_dia`.\n"
                ":seven: Inicia la noche con `/fase_iniciar noche`.\n"
                "Alternativamente, los jugadores pueden usar el comando `/votar_terminar_dia_antes` si están de acuerdo en que no pueden llegar a un consenso sobre a quién linchar.\n"
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
                "`/lista_de_jugadores ` — Muestra un listado de los jugadores vivos y muertos.\n"
                "`/set_valor_voto_jugador @jugador peso` — Cambia cuánto vale el voto del jugador.\n"
                "`/set_vida_jugador @jugador offset` — Cambia cuántos votos necesita para ser linchado.\n"
                "`/status_jugadores` — Muestra todos los jugadores, valor de los votos y 'vidas' configuradas.\n"
                "`/reset_votosadicionales_y_vida ` — Resetea la configuración de todos los jugadores en cuanto a 'valor de los votos' y 'vidas'.\n"
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
                "- `/anunciar` - Envía un mensaje al `canal de juego` configurado usando el bot. Puedes usarlo para dar avisos *anónimos* a los jugadores.\n"
                "- `/borrar_mensajes` - Borra una cantidad de mensajes recientes del canal actual (máximo 100). \n"
                "- `/cuenta_atras_iniciar` - Inicia una cuenta regresiva que enviará un aviso cuando termine el tiempo. Puede usarse para anunciar el tiempo que durará un día, o noche. Solo puede haber una cuenta regresiva a la vez.\n"
                "- `/cuenta_atras_status` - Muestra cuánto tiempo falta para que termine la cuenta regresiva actual.\n"
                "- `/cuenta_atras_cancelar` - Cancela la cuenta regresiva activa, si existe.\n"
                "- `/ping` - Comprueba si el bot está respondiendo correctamente.\n"
            ),
            inline=False
        )
        else:
            pass

        # --- Notas ---
        embed.add_field(
            name="💡 Notas",
            value=(
                "- El `valor de los votos` puede configurarse como 0 en caso de que sea necesario que un jugador no pueda votar.\n"
                "- La `vida` puede ser **positiva o negativa**, pero que no sea menor a la cantidad de jugadores porque puede romper el juego.\n"
                "- La configuración se guarda con el bot, se mantiene en caso de que este se desconecte.\n"
                "- Hay un comando de `/dado` para lanzar un dado de entre 2 y 100 caras.\n"
                "- Hay un comando de `/ruleta` para elegir a un jugador al azar de entre los jugadores vivos.\n"
                "- Hay un comando de `/choose` para elegir al azar una de las opciones ofrecidas.\n"
                "- Solo los administradores pueden ver y usar los comandos que dicen `(MOD)` en la descripción."
            ),
            inline=False
        )

        await ctx.respond(embed=embed, ephemeral=False)
        pass

    @discord.slash_command(description="(MOD) Listado de comandos que pueden usar los jugadores..")
    @discord.default_permissions(administrator=True)
    async def comandos_jugadores(self, ctx):
        
        embed = discord.Embed(
            title="🧾 Comandos para jugadores",
            description="Puedes usar los siguientes comandos:.",
            color=discord.Color.gold()
        )
        embed.set_author(name="MafiaBot", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        #embed.set_footer(text="Desarrollado por Khaeroth (https://github.com/Khaeroth)")

        # --- Votaciones ---
        embed.add_field(
            name=":ballot_box: Votaciones",
            value=(
                "`/votar @jugador` — Vota por alguien para que sea linchado. \n"
                "`/votar_terminar_dia_antes` — En caso de que no deseas linchar a nadie, puedes votar para que termine el día antes. Este voto no se puede quitar hasta que finalice el día, piénsalo bien.\n"
                "`/quitar_voto` — Usa este comando si quieres quitar tu voto hacia un jugado. Este comando NO elimina el voto para terminar el día. \n"
                "`/status_votos` — Muestra cuántos votos van para linchar a un jugador. \n"
            ),
            inline=False
        )

        # --- Gameplay ---
        embed.add_field(
            name="🧩 Gameplay",
            value=(
                "`/accion` — Usa este comando para informar que usarás una habilidad. Si no actuarás durante la noche, envía también una acción diciendo 'No actuaré'. \n"
                "`/dado` — Rueda un dado de entre 2 y 100 caras. Si no se coloca cuantas caras, se usarán 6 por defecto. \n"
                "`/ruleta` — Rueda una ruleta para elegir a un jugador dentro de un rol en específico. \n"
                "`/choose` — El bot eligirá por ti una opción de entre las que coloques separadas por espacios. \n"
            ),
            inline=False
        )

        # --- Información ---
        embed.add_field(
            name=":information_source: Información",
            value=(
                "`/cuenta_atras_status` — Puedes ver cuánto tiempo falta para que termine el contador actual (si es que hay uno activo). \n"
                "`/lista_de_jugadores` — Muestra un listado de los jugadores vivos y muertos.\n"
            ),
            inline=False
        )

        await ctx.respond(embed=embed, ephemeral=False)
        pass

    @discord.slash_command(description="(MOD) Borra toda la configuración de pesos y thresholds del servidor actual.")
    @discord.default_permissions(administrator=True)
    async def reset_votosadicionales_y_vida(self, ctx):
        datos = cargar_json(config_file)
        server_id = str(ctx.guild.id)

        if server_id not in datos:
            await ctx.respond("⚠️ Este servidor no tiene configuraciones registradas.", ephemeral=True)
            return

        # Verificar si hay algo que borrar
        tiene_pesos = "weights" in datos[server_id] and datos[server_id]["weights"]
        tiene_thresholds = "thresholds" in datos[server_id] and datos[server_id]["thresholds"]

        if not tiene_pesos and not tiene_thresholds:
            await ctx.respond("ℹ️ No hay pesos ni thresholds configurados en este servidor.", ephemeral=True)
            return

        # Eliminar solo esas secciones
        datos[server_id]["weights"] = {}
        datos[server_id]["thresholds"] = {}

        guardar_json(config_file, datos)

        await ctx.respond(
            "🧹 **Pesos y thresholds eliminados correctamente.**\n"
            "Todos los jugadores vuelven a valores por defecto.",
            ephemeral=False
        )


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
