import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput, Select
import asyncio
from datetime import datetime
import json
import os
import sys
import re
import aiohttp

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERRO: Token do Discord não encontrado!")
    sys.exit(1)

# IDs fornecidos e atualizados
CARGO_00_ID = 1083520579564478555
CARGO_01_ID = 1083540466676539483
CARGO_02_ID = 1083540964959854612
CARGO_GERENTE_ID = 1083541691866292296
CARGO_MEMBRO_ID = 1083543319189143583

CANAL_SOLICITAR_SET_ID = 1236307426366591079
CANAL_REGISTROS_SET_ID = 1497880182265086106
CATEGORIA_FARMS_ID = 1515876568424255661
CATEGORIA_PAINEL_ID = 1515869907814973440
CATEGORIA_PEDIDOS_ID = 1515879443586088991
CANAL_LOGS_GERAL_ID = 1516104445510009412
CANAL_RANKING_ID = 1516104445510009413
CANAL_COMPRA_VENDA_ID = 1516104445510009414
CANAL_LIVES_ID = 1516104445510009415
CANAL_SISTEMA_RESERVA_ID = 1516463426396749844  # ID ATUALIZADO CONFORME SOLICITADO
CANAL_PAINEL_FARMS_ID = 1516104445510009417

# Banco de dados temporário em JSON
DATA_FILE = "bot_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"farms": {}, "reservas": {}, "ranking": {}, "membros": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- MODALS E VIEWS ---

class FarmModal(Modal):
    def __init__(self, produto):
        super().__init__(title=f"Depositar - {produto}")
        self.produto = produto
        self.quantidade = TextInput(label="Quantidade", placeholder="Ex: 5000", required=True)
        self.print_url = TextInput(label="Link do Print (Imgur, Discord, etc.)", placeholder="https://...", required=True)
        self.add_item(self.quantidade)
        self.add_item(self.print_url)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qtd = int(self.quantidade.value)
        except ValueError:
            await interaction.response.send_message("❌ Quantidade inválida! Digite apenas números.", ephemeral=True)
            return

        url = self.print_url.value
        if not url.startswith("http"):
            await interaction.response.send_message("❌ Link do print inválido! Deve começar com http:// ou https://.", ephemeral=True)
            return

        data = load_data()
        user_id = str(interaction.user.id)
        
        if user_id not in data["membros"]:
            data["membros"][user_id] = {"nome": interaction.user.display_name, "total_farm": 0}
        
        data["membros"][user_id]["total_farm"] += qtd
        
        if self.produto not in data["farms"]:
            data["farms"][self.produto] = 0
        data["farms"][self.produto] += qtd
        
        save_data(data)

        # Log
        canal_logs = bot.get_channel(CANAL_LOGS_GERAL_ID)
        if canal_logs:
            embed = discord.Embed(title="🚜 NOVO DEPÓSITO DE FARM", color=0x00ff00, timestamp=datetime.utcnow())
            embed.add_field(name="Membro", value=interaction.user.mention, inline=True)
            embed.add_field(name="Produto", value=self.produto, inline=True)
            embed.add_field(name="Quantidade", value=f"{qtd:,}", inline=True)
            embed.set_image(url=url)
            await canal_logs.send(embed=embed)

        await interaction.response.send_message(f"✅ Depósito de {qtd:,} {self.produto} registrado com sucesso!", ephemeral=True)
        await atualizar_ranking()

class FarmSelectView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
        select = Select(
            placeholder="Selecione o produto que deseja depositar...",
            custom_id="select_farm_product",
            options=[
                discord.SelectOption(label="Metanfetamina", value="Metanfetamina", emoji="💎"),
                discord.SelectOption(label="Cocaína", value="Cocaína", emoji="❄️"),
                discord.SelectOption(label="Maconha", value="Maconha", emoji="🌿"),
                discord.SelectOption(label="Armas", value="Armas", emoji="🔫"),
                discord.SelectOption(label="Munições", value="Munições", emoji="📦")
            ]
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        produto = interaction.data['values'][0]
        await interaction.response.send_modal(FarmModal(produto))

class PainelFarmsView(View):
    def __init__(self):
        super().__init__(timeout=None)

    # NOME DO BOTÃO ALTERADO PARA DEPOSITAR FARM E REFORÇADA A PERSISTÊNCIA
    @discord.ui.button(label="Depositar Farm", style=discord.ButtonStyle.green, custom_id="btn_farm_produtos")
    async def farm_produtos(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Escolha o produto abaixo:", view=FarmSelectView(), ephemeral=True)

class CompraVendaModal(Modal):
    def __init__(self, tipo):
        super().__init__(title=f"Registrar {tipo}")
        self.tipo = tipo
        self.descricao = TextInput(label="Descrição do Negócio", placeholder="Ex: Venda de 50k de munição para Facção X", style=discord.TextStyle.paragraph, required=True)
        self.valor = TextInput(label="Valor Total (R$)", placeholder="Ex: 500000", required=True)
        self.print_url = TextInput(label="Link do Print do Baú / Transação", placeholder="https://...", required=True)
        self.add_item(self.descricao)
        self.add_item(self.valor)
        self.add_item(self.print_url)

    async def on_submit(self, interaction: discord.Interaction):
        url = self.print_url.value
        if not url.startswith("http"):
            await interaction.response.send_message("❌ Link inválido!", ephemeral=True)
            return

        canal_logs = bot.get_channel(CANAL_LOGS_GERAL_ID)
        if canal_logs:
            embed = discord.Embed(title=f"💸 REGISTRO DE {self.tipo.upper()}", color=0xffa500 if self.tipo == "Compra" else 0x0000ff, timestamp=datetime.utcnow())
            embed.add_field(name="Responsável", value=interaction.user.mention, inline=True)
            embed.add_field(name="Valor", value=f"R$ {self.valor.value}", inline=True)
            embed.add_field(name="Descrição", value=self.descricao.value, inline=False)
            embed.set_image(url=url)
            await canal_logs.send(embed=embed)

        await interaction.response.send_message(f"✅ {self.tipo} registrada com sucesso!", ephemeral=True)

class CompraVendaView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💸 Venda de Munição", style=discord.ButtonStyle.danger, custom_id="btn_venda")
    async def venda(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CompraVendaModal("Venda"))

    @discord.ui.button(label="🛒 Compra de Produto", style=discord.ButtonStyle.success, custom_id="btn_compra")
    async def compra(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CompraVendaModal("Compra"))

class ReservaModal(Modal):
    def __init__(self):
        super().__init__(title="Solicitar Reserva de Farm")
        self.local = TextInput(label="Local / Farm desejado", placeholder="Ex: Farm de Metanfetamina Norte", required=True)
        self.tempo = TextInput(label="Tempo de permanência", placeholder="Ex: 2 horas", required=True)
        self.add_item(self.local)
        self.add_item(self.tempo)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        reserva_id = str(interaction.id)
        
        data["reservas"][reserva_id] = {
            "user": interaction.user.display_name,
            "user_id": interaction.user.id,
            "local": self.local.value,
            "tempo": self.tempo.value,
            "status": "Pendente"
        }
        save_data(data)

        canal_logs = bot.get_channel(CANAL_LOGS_GERAL_ID)
        if canal_logs:
            embed = discord.Embed(title="📅 NOVA SOLICITAÇÃO DE RESERVA", color=0xffff00, timestamp=datetime.utcnow())
            embed.add_field(name="Membro", value=interaction.user.mention, inline=True)
            embed.add_field(name="Local", value=self.local.value, inline=True)
            embed.add_field(name="Tempo", value=self.tempo.value, inline=True)
            
            view_aprovar = View(timeout=None)
            btn_approv = Button(label="Aprovar", style=discord.ButtonStyle.success, custom_id=f"approve_{reserva_id}")
            btn_deny = Button(label="Recusar", style=discord.ButtonStyle.danger, custom_id=f"deny_{reserva_id}")
            
            async def approve_callback(inter: discord.Interaction):
                if not any(r.id in [CARGO_GERENTE_ID, CARGO_00_ID, CARGO_01_ID, CARGO_02_ID] for r in inter.user.roles):
                    await inter.response.send_message("❌ Você não tem permissão para aprovar.", ephemeral=True)
                    return
                d = load_data()
                if reserva_id in d["reservas"]:
                    d["reservas"][reserva_id]["status"] = "Aprovado"
                    save_data(d)
                    embed.color = 0x00ff00
                    embed.title = "📅 RESERVA APROVADA"
                    btn_approv.disabled = True
                    btn_deny.disabled = True
                    await inter.response.edit_message(embed=embed, view=view_aprovar)
                    
                    u = bot.get_user(d["reservas"][reserva_id]["user_id"])
                    if u:
                        try: await u.send(f"✅ Sua reserva para **{d['reservas'][reserva_id]['local']}** foi aprovada!")
                        except: pass

            async def deny_callback(inter: discord.Interaction):
                if not any(r.id in [CARGO_GERENTE_ID, CARGO_00_ID, CARGO_01_ID, CARGO_02_ID] for r in inter.user.roles):
                    await inter.response.send_message("❌ Você não tem permissão para recusar.", ephemeral=True)
                    return
                d = load_data()
                if reserva_id in d["reservas"]:
                    d["reservas"][reserva_id]["status"] = "Recusado"
                    save_data(d)
                    embed.color = 0xff0000
                    embed.title = "📅 RESERVA RECUSADA"
                    btn_approv.disabled = True
                    btn_deny.disabled = True
                    await inter.response.edit_message(embed=embed, view=view_aprovar)
            
            btn_approv.callback = approve_callback
            btn_deny.callback = deny_callback
            view_aprovar.add_item(btn_approv)
            view_aprovar.add_item(btn_deny)
            
            await canal_logs.send(embed=embed, view=view_aprovar)

        await interaction.response.send_message("✅ Sua solicitação de reserva foi enviada para a gerência!", ephemeral=True)

class ReservaView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📅 Reservar Farm", style=discord.ButtonStyle.primary, custom_id="btn_reserva_farm")
    async def reservar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReservaModal())

class LiveConfigView(View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    async def build_embed(self):
        embed = discord.Embed(title="🎥 CONFIGURAÇÃO DE LIVES", description="Painel para gerenciamento de transmissões.", color=0x9146ff)
        return embed

# --- FUNÇÕES DE SUPORTE ---

async def atualizar_ranking():
    canal_ranking = bot.get_channel(CANAL_RANKING_ID)
    if not canal_ranking:
        return
    async for msg in canal_ranking.history(limit=5):
        if msg.author == bot.user:
            await msg.delete()
    
    data = load_data()
    membros_ordenados = sorted(data["membros"].items(), key=lambda x: x[1]["total_farm"], reverse=True)
    
    desc = "🏆 **RANKING DE COLABORAÇÃO (FARMS)** 🏆\n\n"
    for i, (uid, info) in enumerate(membros_ordenados[:10], start=1):
        desc += f"{i}º - <@{uid}> — `{info['total_farm']:,}` unidades\n"
        
    embed = discord.Embed(title="📊 RANKING GERAL", description=desc, color=0xffd700)
    await canal_ranking.send(embed=embed)

async def restaurar_canais_farms():
    pass

async def log_admin_embed(titulo, desc):
    canal_logs = bot.get_channel(CANAL_LOGS_GERAL_ID)
    if canal_logs:
        embed = discord.Embed(title=titulo, description=desc, color=0x2c2f33, timestamp=datetime.utcnow())
        await canal_logs.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Bot {bot.user.name} online!")
    
    # CORREÇÃO CRÍTICA: Registra as views globalmente para evitar falha de interação após reinicializações do Bot
    bot.add_view(PainelFarmsView())
    bot.add_view(CompraVendaView())
    bot.add_view(ReservaView())
    bot.add_view(FarmSelectView())

    for guild in bot.guilds:
        # Painel Farms
        canal_farms = guild.get_channel(CANAL_PAINEL_FARMS_ID)
        if canal_farms:
            async for msg in canal_farms.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            embed_farms = discord.Embed(title="🚜 PAINEL DE FARMS", description="Clique no botão abaixo para registrar seus farms.", color=0x00ff00)
            await canal_farms.send(embed=embed_farms, view=PainelFarmsView())

        # Painel Lives
        canal_lives = guild.get_channel(CANAL_LIVES_ID)
        if canal_lives:
            async for msg in canal_lives.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            view_lives = LiveConfigView(guild.id)
            embed_lives = await view_lives.build_embed()
            await canal_lives.send(embed=embed_lives, view=view_lives)

        # Painel Compra e Venda
        canal_compra_venda = guild.get_channel(CANAL_COMPRA_VENDA_ID)
        if canal_compra_venda:
            async for msg in canal_compra_venda.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            embed_compra_venda = discord.Embed(
                title="💸 SISTEMA DE COMPRA E VENDA",
                description="Clique nos botões abaixo para registrar uma **venda** ou **compra**.\n\n💸 **Venda de Munição** – Registre a venda de munição para outra facção.\n🛒 **Compra de Produto** – Registre a compra de produtos diversos.\n\nTodos os registros são salvos com print e enviados para o canal de logs.",
                color=0x2c2f33
            )
            await canal_compra_venda.send(embed=embed_compra_venda, view=CompraVendaView())

        # Painel de Sistema de Reserva (Atualizado para ler o novo ID do chat)
        canal_reserva = guild.get_channel(CANAL_SISTEMA_RESERVA_ID)
        if canal_reserva:
            async for msg in canal_reserva.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            embed_reserva = discord.Embed(
                title="📅 SISTEMA DE RESERVAS",
                description="Clique no botão abaixo para solicitar uma reserva de farm.",
                color=0x2c2f33
            )
            await canal_reserva.send(embed=embed_reserva, view=ReservaView())

    await restaurar_canais_farms()
    await atualizar_ranking()
    await log_admin_embed("🤖 BOT INICIADO", f"Bot {bot.user.mention} online!")

bot.run(TOKEN)
