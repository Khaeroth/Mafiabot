# MafiaBot

```markdown
🕵️‍♂️ **MafiaBot** es un bot para Pycord que permite gestionar partidas tipo *Mafia / Werewolf* en servidores de Discord.  
Incluye votaciones ponderadas, gestión de roles, fases día/noche, relojes de zona horaria y herramientas útiles para moderación de partidas.

## 🎮 Principales características

- Configuración de canales y roles para jugadores vivos y muertos.  
- Votos ponderados: permite que ciertos jugadores tengan mayor peso al votar.  
- Vida/Thresholds personalizados: puedes definir cuántos votos adicionales (o menos) necesita un jugador para ser linchado.  
- Flujo automático de fases: día, noche, bloqueo/desbloqueo de canal de juego.  
- Módulo adicional de Zonas Horarias: registra países con canales de voz que muestran la hora local cada 10 minutos.  
- Herramientas de moderación: envio de anuncios, purgado de mensajes, cuenta regresiva, etc.  
- Configuración persistente por servidor mediante archivos JSON.

## 🛠️ Instalación

1. Clona el repositorio:
```

git clone [https://github.com/Khaeroth/Mafiabot.git](https://github.com/Khaeroth/Mafiabot.git)
cd Mafiabot

````
2. Crea un entorno virtual (recomendado) e instala dependencias:
```bash
python -m venv venv
source venv/bin/activate  # en Windows: venv\Scripts\activate
pip install -r requirements.txt
````

3. Configura el bot:

   * Crea un archivo `.env` o similar con tu token de bot de Discord.
   * Asegúrate de que el bot tiene permisos adecuados en el servidor (leer mensajes, enviar mensajes, administrar canales/roles si usas bloqueo).
4. Inicia el bot:

   ```bash
   python main.py
   ```

## 📁 Estructura del proyecto

```
Mafiabot/
├── cogs/
│   ├── votos.py          # Cog principal de votación y flujo de juego
│   ├── reloj_mundial.py  # Cog del módulo de zonas horarias
│   └── …                 # Otros cogs auxiliares
├── utils/
│   └── funciones_json.py  # Módulo para cargar/guardar JSON
├── json/
│   ├── config.json        # Configuración de servidores (roles, canales, ponderaciones)
│   └── db_canales.json    # Registro de zonas horarias por servidor
├── MafiaBot.py                # Archivo de arranque del bot
└── README.md              # Este archivo
```

## 🧠 Uso rápido

Para mas información, usa el comando /introducción_al_bot

### Configuración inicial (moderador)

```bash
/set_canal_juego #canal-juego
/set_rol_jugadores @RolVivo
/set_rol_muertos @RolMuerto
/status_config
reset_config
```

### Gestión de jugadores

```bash
/set_valor_voto_jugador @Jugador 2    # el voto vale x2
/set_vida_jugador @Jugador -1         # necesita 1 voto menos para ser linchado
/status_jugadores                      # muestra pesos y thresholds
```

### Votaciones / flujo de juego

```bash
/fase_iniciar dia    # desbloquea canal, limpia votos
/fase_iniciar noche  # inicia la noche
/fase_terminar_dia   # bloquea canal al terminar el día
/votar @Jugador      # votas por un jugador
/quitar_voto         # quitas tu voto
/status_votos        # estado actual de la votación
/limpiar_votos       # elimina todos los votos
```

### Zonas horarias (módulo adicional)

```bash
/zh_registrar país:"Colombia" canal:#colombia zona:"America/Bogota"
/zh_eliminar país:"Colombia"
/zh_listado             # países registrados en este servidor
/zh_lista_completa      # todos los países en todos los servidores
/zh_reset_config        # elimina configuración de zonas horarias del servidor
```

## 📌 Archivos JSON de configuración

* `config.json`: Guarda por servidor la configuración de canales, roles, ponderaciones (`weights`) y thresholds.
  Ejemplo:

  ```json
  {
    "1420124484790128xxx": {
      "server": "Probando-ando",
      "rol_jugador": 1432783026495946xxx,
      "rol_muerto": 1432783061510127xxx,
      "canal_juego": 1432219468620238xxx,
      "weights": {
        "user_157029111124983xxx": 2
      },
      "thresholds": {
        "user_305534682156498xxx": -1,
        "user_157029111124983xxx": 2
      }
    }
  }
  ```
* `db_canales.json`: Registro de servidores, canales de voz y zonas horarias para módulo “Reloj Mundial”.

## 🧩 Contribuciones

Las contribuciones son bienvenidas. Puedes abrir un *pull request* o *issue* para mejoras o reportar bugs.
Por favor, antes de contribuir, abre una sugerencia para acordar la dirección de los cambios.

## 📄 Licencia

Este proyecto está licenciado bajo la [MIT License](LICENSE) — puedes redistribuirlo y modificarlo según los términos de la licencia.

```
