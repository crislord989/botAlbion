# 🗡️ Albion Market Bot

Bot de Discord para consultar precios del mercado de **Albion Online** en tiempo real.

---

## ✨ Comandos

| Comando | Descripción |
|---|---|
| `/precio <item>` | Muestra precios de venta/compra en todas las ciudades |
| `/precio <item> <calidad>` | Filtra por calidad (1=Normal, 5=Masterpiece) |
| `/buscar <query>` | Lista items que coinciden con el nombre |
| `/ayuda` | Muestra esta ayuda |

---

## ⚙️ Instalación

### 1. Requisitos
- Python 3.10 o superior
- Una cuenta de Discord con permiso para crear bots

### 2. Crear el bot en Discord
1. Ve a [Discord Developer Portal](https://discord.com/developers/applications)
2. Haz clic en **New Application** → dale un nombre
3. Ve a la sección **Bot** → clic en **Add Bot**
4. En **Privileged Gateway Intents**, activa **Message Content Intent**
5. Copia el **Token** del bot

### 3. Invitar el bot a tu servidor
1. Ve a **OAuth2 → URL Generator**
2. Scopes: selecciona `bot` y `applications.commands`
3. Bot Permissions: `Send Messages`, `Embed Links`, `Use Slash Commands`
4. Abre la URL generada e invita el bot a tu servidor

### 4. Configurar y ejecutar
```bash
# Clonar / descargar los archivos
cd albion-bot

# Instalar dependencias
pip install -r requirements.txt

# Crear el archivo .env
cp .env.example .env
# Edita .env y pega tu token de Discord

# Ejecutar el bot
python bot.py
```

---

## 📡 Datos de mercado

Los precios provienen de **[Albion Online Data Project](https://www.albion-online-data.com/)**, una API pública y gratuita. Para que los datos estén actualizados, los jugadores necesitan tener instalado el **[Albion Data Client](https://www.albion-online-data.com/)** mientras juegan.

> Si ves "N/A" en muchos precios, es normal — solo significa que nadie con el cliente activo ha visitado ese mercado recientemente.

---

## 🏙️ Ciudades soportadas

- 🔴 Caerleon
- 🟠 Bridgewatch  
- ⚪ Fort Sterling
- 🟢 Lymhurst
- 🔵 Martlock
- 🟣 Thetford
- ⚫ Black Market
