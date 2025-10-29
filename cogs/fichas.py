# cogs/fichas.py
import discord
from discord import option
from discord.ext import commands
from io import BytesIO
from datetime import datetime, date
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests

class Fichas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(description="¡Rellena la info y crea tu ficha de Stardew Valley!")
    @option("nombre", description="Tu nombre o usuario", required=True)
    @option("cumpleaños", description="Debe tener el formato dd/mm/yy. Por ejemplo: 01/12/98", required=True)
    @option("signo", description="Tu signo del zodiaco", required=True)
    @option("pais", description="En qué país o ciudad naciste?", required=True)
    @option("ubicacion", description="En qué país o ciudad estás ahora?", required=True)
    @option("profesion", description="A qué te dedicas? / Qué estudiaste?", required=True)
    @option("estatura", description="Cuánto mides? (en metros)", required=True)
    @option("gustos", description="Qué cosas te gustan?", required=True)
    @option("disgustos", description="Qué cosas no te gustan?", required=True)
    @option("funfact", description="Cuéntamos algo curioso sobre ti, o una frase", required=True)
    @option("anime_fav", description="(OPCIONAL) Cuál es tu anime favorito?", required=False, default="")
    @option("muslos", description="(OPCIONAL) Diametro en centímetros (?", required=False, default="")
    async def ficha(self, 
                    ctx,
                    nombre: str = None,
                    cumpleaños: str = None,
                    signo: str = None,
                    pais: str = None,
                    ubicacion: str = None,
                    profesion: str = None,
                    estatura: str = None,
                    gustos: str = None,
                    disgustos: str = None,
                    funfact: str = None,
                    anime_fav: str = None,
                    muslos: str = None
                    ):

        # Carga imagen de fondo
        img_raw = Image.open("img/bg.png").convert("RGBA")
        img = img_raw.resize((800,500))

        # Tablas de fondo
        tabla_raw = Image.open("img/tabla.png").convert("RGBA")
        tabla = tabla_raw.resize((770,400))

        # Marco para el avatar
        frame_raw = Image.open("img/box.png").convert("RGBA")
        frame = frame_raw.resize((155,170))

        # Cajita para las respuestas
        box_raw = Image.open("img/box-2.png").convert("RGBA")
        box = box_raw.resize((375,20))
        
        img.paste(tabla, (15,50), tabla)
        img.paste(frame, (70,85), frame)

        draw = ImageDraw.Draw(img) 

        # Fuente (usa una básica si no tienes ttf instalado)
        try:
            font_thin = ImageFont.truetype("fonts/LSANS.TTF", size=12)
            font_l_bold = ImageFont.truetype("fonts/LSANSD.TTF", size=18)
            font_bold = ImageFont.truetype("fonts/svbold.ttf", size=18)
            font_caps = ImageFont.truetype("fonts/Stardew Valley Regular.ttf", size=48)
        except:
            font_thin = ImageFont.load_default()

        # Titulo
        draw.text((380, 85), "FICHA", fill=(0, 0, 0), font=font_caps)

        # Dibujar texto en el centro
            # X
        margen = 240
        margen2 = margen+140
    
            # Y
        linea = 110
        
            # Interlineado
        espacio = 22
    
        # Límite de caracteres
        limite = 45
        if len(nombre) > limite or len(signo) > limite or len(pais) > limite or len(ubicacion) > limite or len(profesion) > limite or len(estatura) > limite or len(gustos) > limite or len(disgustos) > limite or len(funfact) > limite:
             await ctx.respond("Error: Ningún campo debe tener más de 45 caractéres.", ephemeral=True)
             return
    
        # Username
        try:
            text = f"@{ctx.author.display_name}"
            if len(text) > 15:
                text = f"@{ctx.author.name}"
        
            bbox = draw.textbbox((0, 0), text, font=font_l_bold)  # ancho y alto del texto
            ancho_texto = bbox[2] - bbox[0]
            alto_texto = bbox[3] - bbox[1]

            # Centro del frame (x)
            frame_x = 70
            frame_y = 85
            frame_w = 155
            frame_h = 170

            x = frame_x + (frame_w - ancho_texto) // 2
            y = frame_y + frame_h + 8  # 10px debajo del frame

            draw.text((x, y), text, fill=(0, 0, 0), font=font_l_bold)
        
        except Exception as e:
            print(f"Error al dibujar username: {e}")
    
        # Nombre
        try:
            indice = 1
            img.paste(box, (margen2-15, (linea + espacio*indice)+2), box)
            draw.text((margen, linea + espacio*indice), "Nombre", fill=(0, 0, 0), font=font_bold)
            draw.text((margen2, (linea + espacio*indice)+5), nombre, fill=(0, 0, 0), font=font_thin)
        except: 
            await ctx.respond("Error: Debes llenar el campo 'nombre'.", ephemeral=True)
    
        # Cumpleaños
        try:
            indice = indice + 1
            img.paste(box, (margen2-15, (linea + espacio*indice)+2), box)
            draw.text((margen, linea + espacio*indice), "Cumpleanos", fill=(0, 0, 0), font=font_bold)
            draw.text((margen2, (linea + espacio*indice)+5), cumpleaños, fill=(0, 0, 0), font=font_thin)
        except:
            await ctx.respond("Error: Debes llenar el campo 'cumpleaños'.", ephemeral=True)
    
        # Edad
        try:
            nacimiento = datetime.strptime(cumpleaños, "%d/%m/%y").date()
            hoy = date.today()
            edad = hoy.year - nacimiento.year
            if (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day):
                edad -= 1

            indice = indice + 1
            img.paste(box, (margen2-15, (linea + espacio*indice)+2), box)
            draw.text((margen, linea + espacio*indice), "Edad", fill=(0, 0, 0), font=font_bold)
            draw.text((margen2, (linea + espacio*indice)+5), f"{str(edad)} años", fill=(0, 0, 0), font=font_thin)
        except:
            await ctx.respond("Error: Coloca tu cumpleaños en este formato: dd/mm/yy.", ephemeral=True)
            return

        # Signo
        try:
            indice = indice + 1
            img.paste(box, (margen2-15, (linea + espacio*indice)+2), box)
            draw.text((margen, linea + espacio*indice), "Signo", fill=(0, 0, 0), font=font_bold)
            draw.text((margen2, (linea + espacio*indice)+5), signo, fill=(0, 0, 0), font=font_thin)
        except:
            await ctx.respond("Error: Debes llenar el campo 'signo'.", ephemeral=True)
        
        # Pais
        try:
            indice = indice + 1
            img.paste(box, (margen2-15, (linea + espacio*indice)+2), box)
            draw.text((margen, linea + espacio*indice), "Pais", fill=(0, 0, 0), font=font_bold)
            draw.text((margen2, (linea + espacio*indice)+5), pais, fill=(0, 0, 0), font=font_thin)
        except:
            await ctx.respond("Error: Debes llenar el campo 'pais'.", ephemeral=True)

        # Ubicación
        try:
            indice = indice + 1
            img.paste(box, (margen2-15, (linea + espacio*indice)+2), box)
            draw.text((margen, linea + espacio*indice), "Ubicacion", fill=(0, 0, 0), font=font_bold)
            draw.text((margen2, (linea + espacio*indice)+5), ubicacion, fill=(0, 0, 0), font=font_thin)
        except:
            await ctx.respond("Error: Debes llenar el campo 'ubicacion'.", ephemeral=True)

        # Profesión
        try:
            indice = indice + 1
            img.paste(box, (margen2-15, (linea + espacio*indice)+2), box)
            draw.text((margen, linea + espacio*indice), "Profesion", fill=(0, 0, 0), font=font_bold)
            draw.text((margen2, (linea + espacio*indice)+5), profesion, fill=(0, 0, 0), font=font_thin)
        except:
            await ctx.respond("Error: Debes llenar el campo 'profesion'.", ephemeral=True)

        # Estatura
        try:
            indice = indice + 1
            img.paste(box, (margen2-15, (linea + espacio*indice)+2), box)
            draw.text((margen, linea + espacio*indice), "Estatura", fill=(0, 0, 0), font=font_bold)
            draw.text((margen2, (linea + espacio*indice)+5), f"{estatura}", fill=(0, 0, 0), font=font_thin)
        except:
            await ctx.respond("Error: Debes llenar el campo 'estatura'.", ephemeral=True)

        # Gustos
        try:
            indice = indice + 1
            img.paste(box, (margen2-15, (linea + espacio*indice)+2), box)
            draw.text((margen, linea + espacio*indice), "Gustos", fill=(0, 0, 0), font=font_bold)
            draw.text((margen2, (linea + espacio*indice)+5), gustos, fill=(0, 0, 0), font=font_thin)
        except:
            await ctx.respond("Error: Debes llenar el campo 'gustos'.", ephemeral=True)

        # Disgustos
        try:
            indice = indice + 1
            img.paste(box, (margen2-15, (linea + espacio*indice)+2), box)
            draw.text((margen, linea + espacio*indice), "Disgustos", fill=(0, 0, 0), font=font_bold)
            draw.text((margen2, (linea + espacio*indice)+5), disgustos, fill=(0, 0, 0), font=font_thin)
        except:
            await ctx.respond("Error: Debes llenar el campo 'disgustos'.", ephemeral=True)

        # Funfact    
        try:
            indice = indice + 1
            img.paste(box, (margen2-15, (linea + espacio*indice)+2), box)
            draw.text((margen, linea + espacio*indice), "Datos Random", fill=(0, 0, 0), font=font_bold)
            draw.text((margen2, (linea + espacio*indice)+5), funfact, fill=(0, 0, 0), font=font_thin)        
        except:
            await ctx.respond("Error: Debes llenar el campo 'funfact'.", ephemeral=True)

        # Anime
        if anime_fav:
            indice = indice + 1
            img.paste(box, (margen2-15, (linea + espacio*indice)+2), box)
            draw.text((margen, linea + espacio*indice), "Anime Favorito", fill=(0, 0, 0), font=font_bold)
            draw.text((margen2, (linea + espacio*indice)+5), anime_fav, fill=(0, 0, 0), font=font_thin)    

        # Muslos
        if muslos:
            indice = indice + 1
            img.paste(box, (margen2-15, (linea + espacio*indice)+2), box)
            draw.text((margen, linea + espacio*indice), "Muslos (?", fill=(0, 0, 0), font=font_bold)
            draw.text((margen2, (linea + espacio*indice)+5), f"{muslos}", fill=(0, 0, 0), font=font_thin)


        # Avatar
        # Descargar avatar
        user = ctx.author
        avatar_url = user.display_avatar.replace(size=128).url
    
        try:
            # Pedimos la imagen con headers
            #response = requests.get(avatar_url)
            response = requests.get(avatar_url, headers={"User-Agent": "Mozilla/5.0"})
        
            # Validamos la respuesta
            if response.status_code != 200:
                await ctx.respond("⚠️ No se pudo descargar tu avatar.", ephemeral=True)
                return
        
            if "image" not in response.headers.get("Content-Type", ""):
                await ctx.respond("⚠️ El imagen de avatar no es una imagen válida.", ephemeral=True)
                return
            
            # Abrimos la imagen    
            avatar = Image.open(BytesIO(response.content)).convert("RGBA")
        
            # La recortamos cuadrada
            size = min(avatar.size)
            avatar = ImageOps.fit(avatar, (size, size), centering=(0.5, 0.5))

            img.paste(avatar, (83,107), avatar)

        except Exception as e:
            await ctx.respond(f"⚠️ No pude procesar tu avatar. Error: {e}", ephemeral=True)
            return        

        # Guardar en un buffer de memoria
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # Enviar como archivo en Discord
        file = discord.File(fp=buffer, filename="ficha.png")
        await ctx.respond(file=file)

def setup(bot):
    bot.add_cog(Fichas(bot))
