import os
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import json
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Albion Online Data Project API
BASE_URL = "https://west.albion-online-data.com/api/v2/stats/prices"
SEARCH_URL = "https://gameinfo-ams.albiononline.com/api/gameinfo/search"
RENDER_URL = "https://render.albiononline.com/v1/item"

CITIES = ["Caerleon", "Bridgewatch", "Fort Sterling", "Lymhurst", "Martlock", "Thetford", "Black Market"]
CITY_EMOJIS = {
    "Caerleon": "🔴",
    "Bridgewatch": "🟠",
    "Fort Sterling": "⚪",
    "Lymhurst": "🟢",
    "Martlock": "🔵",
    "Thetford": "🟣",
    "Black Market": "⚫",
}

QUALITY_NAMES = {
    1: "Normal",
    2: "Good",
    3: "Outstanding",
    4: "Excellent",
    5: "Masterpiece",
}

ENCHANT_COLORS = {
    0: 0x808080,  # None - gray
    1: 0x5b9bd5,  # .1 - blue
    2: 0x70ad47,  # .2 - green
    3: 0xffc000,  # .3 - gold
    4: 0xff0000,  # .4 - red
}

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


def format_price(price: int) -> str:
    """Format price with thousands separator."""
    if price == 0:
        return "N/A"
    return f"{price:,}"


def get_enchant_from_id(item_id: str) -> int:
    """Get enchantment level from item ID (e.g. T4_SWORD@1 -> 1)."""
    if "@" in item_id:
        return int(item_id.split("@")[-1])
    return 0


async def search_items(query: str) -> list[dict]:
    """Search for items by name using Albion's gameinfo API."""
    async with aiohttp.ClientSession() as session:
        params = {"q": query}
        try:
            async with session.get(SEARCH_URL, params=params, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("items", [])
        except Exception:
            pass
    return []


async def get_prices(item_id: str, qualities: str = "1,2,3,4,5") -> list[dict]:
    """Fetch prices for an item from the Albion Online Data Project."""
    cities_str = ",".join(CITIES)
    url = f"{BASE_URL}/{item_id}"
    params = {
        "locations": cities_str,
        "qualities": qualities,
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception:
            pass
    return []


def build_price_embed(item_name: str, item_id: str, prices_data: list[dict]) -> discord.Embed:
    """Build a Discord embed with price information."""
    enchant = get_enchant_from_id(item_id)
    embed_color = ENCHANT_COLORS.get(enchant, 0x808080)

    embed = discord.Embed(
        title=f"📊 {item_name}",
        description=f"`{item_id}`",
        color=embed_color,
    )

    # Item icon
    base_id = item_id.split("@")[0]
    embed.set_thumbnail(url=f"{RENDER_URL}/{item_id}.png")

    # Group by city, take best (lowest sell / highest buy) per quality
    city_data: dict[str, dict] = {}
    for entry in prices_data:
        city = entry.get("city", "")
        quality = entry.get("quality", 1)
        sell = entry.get("sell_price_min", 0)
        buy = entry.get("buy_price_max", 0)
        updated = entry.get("sell_price_min_date", "")[:10]

        if city not in city_data:
            city_data[city] = {}
        if quality not in city_data[city]:
            city_data[city][quality] = {"sell": sell, "buy": buy, "updated": updated}

    # Build fields per city (only show cities with data)
    has_data = False
    for city in CITIES:
        if city not in city_data:
            continue
        qualities_data = city_data[city]
        # Filter out entries with no data
        valid = {q: v for q, v in qualities_data.items() if v["sell"] > 0 or v["buy"] > 0}
        if not valid:
            continue

        has_data = True
        emoji = CITY_EMOJIS.get(city, "🏙️")

        lines = []
        for q in sorted(valid.keys()):
            v = valid[q]
            q_name = QUALITY_NAMES.get(q, f"Q{q}")
            sell_str = f"🔴 {format_price(v['sell'])}" if v["sell"] > 0 else "🔴 N/A"
            buy_str = f"🟢 {format_price(v['buy'])}" if v["buy"] > 0 else "🟢 N/A"
            lines.append(f"**{q_name}** — {sell_str} | {buy_str}")

        updated_str = valid[min(valid.keys())]["updated"] if valid else "?"
        field_value = "\n".join(lines) + f"\n*Updated: {updated_str}*"
        embed.add_field(name=f"{emoji} {city}", value=field_value, inline=False)

    if not has_data:
        embed.add_field(
            name="⚠️ Sin datos",
            value="No hay precios disponibles para este item en ninguna ciudad.\nAsegúrate de tener el [Albion Data Client](https://www.albion-online-data.com/) activo.",
            inline=False,
        )

    embed.set_footer(text="Datos de albion-online-data.com • 🔴 Venta mínima | 🟢 Compra máxima")
    return embed


# ── Slash Commands ──────────────────────────────────────────────────────────

@tree.command(name="precio", description="Busca el precio de un item en el mercado de Albion Online")
@app_commands.describe(
    item="Nombre del item (ej: T4 Sword, Adept's Broadsword)",
    calidad="Filtrar por calidad (1=Normal ... 5=Masterpiece). Vacío = todas",
)
async def precio(
    interaction: discord.Interaction,
    item: str,
    calidad: Optional[int] = None,
):
    await interaction.response.defer(thinking=True)

    # Search for the item
    results = await search_items(item)
    if not results:
        await interaction.followup.send(
            f"❌ No se encontró ningún item con el nombre **{item}**.\nIntenta con el nombre en inglés.",
            ephemeral=True,
        )
        return

    # Take the first result
    found = results[0]
    item_id = found.get("id", "")
    item_name = found.get("localizedNames", {}).get("ES-ES") or found.get("localizedNames", {}).get("EN-US") or item_id

    qualities = str(calidad) if calidad else "1,2,3,4,5"
    prices_data = await get_prices(item_id, qualities)

    embed = build_price_embed(item_name, item_id, prices_data)

    # Add buttons
    view = ItemView(item_id, item_name, results)
    await interaction.followup.send(embed=embed, view=view)


@tree.command(name="buscar", description="Busca items por nombre y muestra una lista de resultados")
@app_commands.describe(query="Nombre o parte del nombre del item")
async def buscar(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)

    results = await search_items(query)
    if not results:
        await interaction.followup.send(f"❌ No se encontraron items para **{query}**.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"🔍 Resultados para: {query}",
        color=0x5865F2,
        description="Usa `/precio` con el nombre exacto para ver precios.",
    )

    for r in results[:10]:
        rid = r.get("id", "N/A")
        name_es = r.get("localizedNames", {}).get("ES-ES", "")
        name_en = r.get("localizedNames", {}).get("EN-US", rid)
        display = f"{name_es} / {name_en}" if name_es and name_es != name_en else name_en
        embed.add_field(name=display, value=f"`{rid}`", inline=False)

    await interaction.followup.send(embed=embed)


@tree.command(name="ayuda", description="Muestra los comandos disponibles del bot de Albion")
async def ayuda(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🗡️ Albion Market Bot — Ayuda",
        color=0xf5a623,
        description="Bot para consultar precios del mercado de **Albion Online**.",
    )
    embed.add_field(
        name="/precio `<item>` `[calidad]`",
        value="Muestra el precio de venta y compra de un item en todas las ciudades.\nEj: `/precio Adept's Broadsword`",
        inline=False,
    )
    embed.add_field(
        name="/buscar `<query>`",
        value="Busca items por nombre y muestra una lista con sus IDs.\nEj: `/buscar druid robe`",
        inline=False,
    )
    embed.add_field(
        name="📡 Datos en tiempo real",
        value="Los precios provienen de [Albion Online Data Project](https://www.albion-online-data.com/).\nPara mejores datos, instala el **Albion Data Client** mientras juegas.",
        inline=False,
    )
    embed.set_footer(text="Hecho con ❤️ para Albion Online")
    await interaction.response.send_message(embed=embed)


# ── UI Components ───────────────────────────────────────────────────────────

class ItemView(discord.ui.View):
    def __init__(self, item_id: str, item_name: str, search_results: list):
        super().__init__(timeout=120)
        self.item_id = item_id
        self.item_name = item_name
        self.search_results = search_results
        self.current_index = 0

        # Botón de link (debe estar aquí dentro)
        self.add_item(discord.ui.Button(
            label="🌐 Ver en web",
            style=discord.ButtonStyle.link,
            url="https://www.albiononline2d.com/en/item/id/"
        ))

        # Add select if multiple results
        if len(search_results) > 1:
            options = []
            for i, r in enumerate(search_results[:10]):
                rid = r.get("id", "")
                name_en = r.get("localizedNames", {}).get("EN-US", rid)
                name_es = r.get("localizedNames", {}).get("ES-ES", "")
                label = name_es or name_en
                label = label[:100]
                options.append(discord.SelectOption(label=label, value=str(i), description=rid[:100]))
            select = ItemSelect(options, self)
            self.add_item(select)

    @discord.ui.button(label="🔄 Actualizar", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        prices_data = await get_prices(self.item_id)
        embed = build_price_embed(self.item_name, self.item_id, prices_data)
        await interaction.edit_original_response(embed=embed, view=self)


class ItemSelect(discord.ui.Select):
    def __init__(self, options, parent_view: ItemView):
        super().__init__(placeholder="Selecciona un item...", options=options, min_values=1, max_values=1)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        idx = int(self.values[0])
        selected = self.parent_view.search_results[idx]
        item_id = selected.get("id", "")
        item_name = (
            selected.get("localizedNames", {}).get("ES-ES")
            or selected.get("localizedNames", {}).get("EN-US")
            or item_id
        )
        self.parent_view.item_id = item_id
        self.parent_view.item_name = item_name
        prices_data = await get_prices(item_id)
        embed = build_price_embed(item_name, item_id, prices_data)
        await interaction.edit_original_response(embed=embed, view=self.parent_view)


# ── Events ──────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot conectado como {bot.user} (ID: {bot.user.id})")
    print("📡 Comandos sincronizados con Discord.")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="el mercado de Albion 📈")
    )


if __name__ == "__main__":
    if not TOKEN:
        print("❌ Error: DISCORD_TOKEN no encontrado en el archivo .env")
        exit(1)
    bot.run(TOKEN)
