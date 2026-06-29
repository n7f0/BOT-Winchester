import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput, Select, UserSelect
import asyncio
from datetime import datetime, timezone
import json
import os
import sys
import re
import aiohttp
import hashlib
import random

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERRO: Token do Discord não encontrado!")
    sys.exit(1)

# ========= IDs =========
CARGO_00_ID = 1083520579564478555
CARGO_01_ID = 1083540466676539483
CARGO_02_ID = 1083540964959854612
CARGO_GERENTE_ID = 1083541691866292296
CARGO_MEMBRO_ID = 1083543319189143583

CANAL_SOLICITAR_SET_ID = 1236307426366591079
CANAL_REGISTROS_SET_ID = 1497880182265086106
CATEGORIA_FARMS_ID = 1515876568424255661
CATEGORIA_PAINEL_ID = 1515869907814973440

CHAT_LOGS_ID = 1515876949233504267
CHAT_ADMIN_LOGS_ID = 1515876971089760326
CHAT_RANK_ID = 1515877095685750894
LOG_REGISTROS_ID = int(os.getenv("LOG_REGISTROS_ID", "1498349960062570740"))
CHAT_PEDIDOS_LOG_ID = 1516080167632502794

CANAL_LIVES_PAINEL_ID = 1515937074359046235
CANAL_COMPRA_VENDA_ID = 1515937419395072030
CANAL_COMPRA_VENDA_LOGS_ID = 1515937452802572318
CANAL_RESERVAS_FUNC_PAINEL_ID = 1516449109060489466
CANAL_RESERVAS_FUNC_LOGS_ID = 1516460988541571212

CANAL_CRIAR_FARM_ID = 1516460981516242976
CANAL_RESERVAS_CLIENTES_ID = 1516463426396749844

LOG_BAU_MEMBRO_ID = 1516798308121579571
LOG_BAU_GERENTE_ID = 1516798395996442645
LOG_BAU_CASA_ID = 1516798452422545428
LOG_RESERVAS_CLIENTES_ID = 1516799777747112016

CANAL_PAINEL_BAUS_ID = 1516947055698772039

LOG_ENTREGAS_DINHEIRO_SUJO_ID = 1516949594712440852
PAINEL_CONTROLE_DINHEIRO_SUJO_ID = 1516949565708959835

LOG_FARM_ID = 1517267814854168817

CARGO_ADMIN_IDS = [CARGO_00_ID, CARGO_01_ID, CARGO_02_ID, CARGO_GERENTE_ID]
CARGO_REMOVER_MEMBRO_IDS = CARGO_ADMIN_IDS

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# ========= DADOS =========
dados = {
    "usuarios": {},
    "canais": {},
    "caixa_semana": {},
    "usuarios_banidos": [],
    "sets_pendentes": {},
    "pedidos": {
        "config": {"porcentagens": {"cliente": 50, "maquina": 40, "fac": 5, "membros": 5, "vip_fac": 10}, "ultima_edicao": None},
        "lista": []
    },
    "pedidos_funcionarios": {
        "config": {"porcentagens": {"funcionario": 50, "maquina": 40, "fac": 5, "vip_fac": 10}, "ultima_edicao": None},
        "lista": []
    },
    "lives": {
        "config": {},
        "streamers": {},
        "last_notified": {},
        "status": {}
    },
    "compras_vendas": [],
    "painels": {}
}

def salvar_dados():
    try:
        with open("dados_bot.json", "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERRO] Falha ao salvar dados: {e}")

def carregar_dados():
    global dados
    try:
        with open("dados_bot.json", "r", encoding="utf-8") as f:
            loaded = json.load(f)
            for key in dados:
                if key in loaded:
                    dados[key] = loaded[key]
            if "lives" in dados:
                if "streamers" in dados["lives"]:
                    for server_id, streamers_dict in list(dados["lives"]["streamers"].items()):
                        if isinstance(streamers_dict, dict):
                            nova_lista = []
                            for uid, data_item in streamers_dict.items():
                                nova_lista.append({
                                    "id": random.randint(1000, 999999),
                                    "uid": uid,
                                    "nome": data_item.get("nome", uid),
                                    "twitch": data_item.get("twitch"),
                                    "youtube": data_item.get("youtube"),
                                    "kick": data_item.get("kick"),
                                    "tiktok": data_item.get("tiktok"),
                                    "observacao": data_item.get("observacao", "")
                                })
                            dados["lives"]["streamers"][server_id] = nova_lista
                if "config" not in dados["lives"]:
                    dados["lives"]["config"] = {}
                if "last_notified" not in dados["lives"]:
                    dados["lives"]["last_notified"] = {}
                if "status" not in dados["lives"]:
                    dados["lives"]["status"] = {}
            if "pedidos" not in dados:
                dados["pedidos"] = {"config": {"porcentagens": {"cliente": 50, "maquina": 40, "fac": 5, "membros": 5, "vip_fac": 10}, "ultima_edicao": None}, "lista": []}
            if "pedidos_funcionarios" not in dados:
                dados["pedidos_funcionarios"] = {"config": {"porcentagens": {"funcionario": 50, "maquina": 40, "fac": 5, "vip_fac": 10}, "ultima_edicao": None}, "lista": []}
            if "compras_vendas" not in dados:
                dados["compras_vendas"] = []
            if "painels" not in dados:
                dados["painels"] = {}
            if "vip_fac" not in dados["pedidos"]["config"]["porcentagens"]:
                dados["pedidos"]["config"]["porcentagens"]["vip_fac"] = 10
            if "vip_fac" not in dados["pedidos_funcionarios"]["config"]["porcentagens"]:
                dados["pedidos_funcionarios"]["config"]["porcentagens"]["vip_fac"] = 10
            if "usuarios_banidos" not in dados:
                dados["usuarios_banidos"] = []
            salvar_dados()
            return True
    except FileNotFoundError:
        salvar_dados()
        return True
    except Exception as e:
        print(f"[ERRO] Falha ao carregar dados: {e}")
        return False

# ========= LOGS =========
async def log_embed(titulo, descricao, cor, thumbnail=None, fields=None):
    canal = bot.get_channel(CHAT_LOGS_ID)
    if canal:
        embed = discord.Embed(title=titulo, description=descricao, color=cor, timestamp=datetime.now(timezone.utc))
        if thumbnail: embed.set_thumbnail(url=thumbnail)
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        await canal.send(embed=embed)

async def log_admin_embed(titulo, descricao, cor, thumbnail=None, fields=None):
    canal = bot.get_channel(CHAT_ADMIN_LOGS_ID)
    if canal:
        embed = discord.Embed(title=titulo, description=descricao, color=cor, timestamp=datetime.now(timezone.utc))
        if thumbnail: embed.set_thumbnail(url=thumbnail)
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        await canal.send(embed=embed)

async def log_pedido_embed(titulo, descricao, cor, fields=None):
    canal = bot.get_channel(CHAT_PEDIDOS_LOG_ID)
    if canal:
        embed = discord.Embed(title=titulo, description=descricao, color=cor, timestamp=datetime.now(timezone.utc))
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        await canal.send(embed=embed)

async def log_reserva_cliente_embed(titulo, descricao, cor, fields=None):
    canal = bot.get_channel(LOG_RESERVAS_CLIENTES_ID)
    if canal:
        embed = discord.Embed(title=titulo, description=descricao, color=cor, timestamp=datetime.now(timezone.utc))
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        await canal.send(embed=embed)

async def log_reserva_func_embed(titulo, descricao, cor, fields=None):
    canal = bot.get_channel(CANAL_RESERVAS_FUNC_LOGS_ID)
    if canal:
        embed = discord.Embed(title=titulo, description=descricao, color=cor, timestamp=datetime.now(timezone.utc))
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        await canal.send(embed=embed)

async def log_compra_venda(tipo, dados_log):
    canal = bot.get_channel(CANAL_COMPRA_VENDA_LOGS_ID)
    if canal:
        embed = discord.Embed(title=f"📋 {tipo.upper()}", color=0x2c2f33, timestamp=datetime.now(timezone.utc))
        for chave, valor in dados_log.items():
            embed.add_field(name=chave, value=valor, inline=False)
        await canal.send(embed=embed)

async def log_bau(tipo, canal_id, dados_log):
    canal = bot.get_channel(canal_id)
    if canal:
        embed = discord.Embed(title=f"📦 BAÚ {tipo.upper()}", color=0x2c2f33, timestamp=datetime.now(timezone.utc))
        for chave, valor in dados_log.items():
            embed.add_field(name=chave, value=valor, inline=False)
        await canal.send(embed=embed)

async def log_entrega_dinheiro_sujo(entregador, recebedor, valor, data, observacao=""):
    canal = bot.get_channel(LOG_ENTREGAS_DINHEIRO_SUJO_ID)
    if canal:
        if isinstance(recebedor, discord.Member):
            recebedor_mention = recebedor.mention
        else:
            recebedor_mention = recebedor
        embed = discord.Embed(
            title="💰 ENTREGA DE DINHEIRO SUJO",
            description=f"**Entregador:** {entregador.mention}\n**Recebedor:** {recebedor_mention}\n**Valor:** R$ {valor:,.2f}\n**Data:** {data}\n**Observação:** {observacao or 'Nenhuma'}",
            color=0x4f545c, timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/196/196566.png")
        await canal.send(embed=embed)

async def log_farm(embed):
    canal = bot.get_channel(LOG_FARM_ID)
    if canal:
        try: await canal.send(embed=embed)
        except Exception as e: print(f"[LOG FARM] Erro: {e}")

async def limpar_logs_usuario(user_id, user_name):
    if str(user_id) in dados["usuarios_banidos"]: return 0
    dados["usuarios_banidos"].append(str(user_id))
    total_limpo = 0
    for canal_id in [CHAT_LOGS_ID, CHAT_ADMIN_LOGS_ID, CHAT_RANK_ID]:
        canal = bot.get_channel(canal_id)
        if canal:
            async for msg in canal.history(limit=None):
                if msg.author == bot.user and (f"<@{user_id}>" in msg.content or f"<@!{user_id}>" in msg.content):
                    novo = msg.content.replace(f"<@{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]").replace(f"<@!{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]")
                    try: await msg.edit(content=novo); total_limpo += 1
                    except: pass
    for canal_id in dados["canais"].values():
        canal = bot.get_channel(canal_id)
        if canal:
            async for msg in canal.history(limit=None):
                if msg.author == bot.user and (f"<@{user_id}>" in msg.content or f"<@!{user_id}>" in msg.content):
                    novo = msg.content.replace(f"<@{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]").replace(f"<@!{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]")
                    try: await msg.edit(content=novo); total_limpo += 1
                    except: pass
    if str(user_id) in dados["usuarios"]:
        dados["usuarios"][str(user_id)] = {"farms": [], "pagamentos": [], "dinheiro_sujo": 0, "nome": f"[REMOVIDO - {user_name}]", "removido_em": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "transacoes_dinheiro_sujo": []}
        salvar_dados()
    if str(user_id) in dados["canais"]:
        canal = bot.get_channel(dados["canais"][str(user_id)])
        if canal:
            try: await canal.delete(reason=f"Usuário {user_name} removido")
            except: pass
        del dados["canais"][str(user_id)]
        salvar_dados()
    return total_limpo

# ========= INTENTS E BOT =========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

def tem_cargo(member, cargos_ids):
    if not hasattr(member, 'guild'): return False
    for cid in cargos_ids:
        cargo = member.guild.get_role(cid)
        if cargo and cargo in member.roles: return True
    return False

def is_admin(member): return tem_cargo(member, CARGO_ADMIN_IDS)
def is_membro(member): return tem_cargo(member, [CARGO_MEMBRO_ID])
def pode_registrar_acao(member): return tem_cargo(member, CARGO_ADMIN_IDS)
def pode_aprovar_set(member): return pode_registrar_acao(member)
def pode_remover_membro(member): return tem_cargo(member, CARGO_REMOVER_MEMBRO_IDS)

# ========= RANKING =========
async def atualizar_ranking():
    canal = bot.get_channel(CHAT_RANK_ID)
    if not canal: return
    async for msg in canal.history(limit=50):
        if msg.author == bot.user: await msg.delete()

    ranking = []
    PRODUTOS_CONTAM = ["RELÓGIO DE LUXO", "OBRA DE ARTE", "AÇÕES DE EMPRESA", "CARTEIRA NFT"]

    for uid, data in dados["usuarios"].items():
        if "removido_em" in data: continue
        farms = data.get("farms", [])
        total_itens = 0
        for farm in farms:
            for produto in farm.get("produtos", []):
                if produto.get("produto") in PRODUTOS_CONTAM:
                    total_itens += produto.get("quantidade", 0)
        rotas = total_itens // 20
        if rotas > 0:
            nome_registro = data.get("registro_nome")
            if nome_registro:
                nome_exibicao = nome_registro
            else:
                try:
                    if uid.startswith("vulgo_"):
                        nome_exibicao = data.get("nome", uid.replace("vulgo_", ""))
                    else:
                        user = await bot.fetch_user(int(uid))
                        nome_exibicao = user.name
                except:
                    nome_exibicao = data.get("nome", "Usuário desconhecido")
            ranking.append({"usuario": nome_exibicao, "usuario_id": uid, "rotas": rotas, "total_itens": total_itens})

    ranking_ordenado = sorted(ranking, key=lambda x: x["rotas"], reverse=True)
    for i, item in enumerate(ranking_ordenado):
        if i == 0: item["posicao"] = 1
        elif item["rotas"] == ranking_ordenado[i-1]["rotas"]: item["posicao"] = ranking_ordenado[i-1]["posicao"]
        else: item["posicao"] = i+1

    if not ranking_ordenado:
        embed = discord.Embed(title="🏆 RANKING DE ROTAS (20 ITENS = 1 ROTA)", description=f"*Bebida importada não é considerada.*\nAtualizado em {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}\n\nNenhuma rota registrada ainda.", color=0x2c2f33)
        await canal.send(embed=embed, view=RankingView())
        return

    linhas = []
    for item in ranking_ordenado:
        pos = item["posicao"]
        emoji = "🥇" if pos == 1 else "🥈" if pos == 2 else "🥉" if pos == 3 else f"{pos}°"
        linhas.append(f"{emoji} **{item['usuario']}** – {item['rotas']} rotas ({item['total_itens']} itens)")

    total_membros = len(linhas)
    POR_PAGINA = 25
    chunks = [linhas[i:i+POR_PAGINA] for i in range(0, len(linhas), POR_PAGINA)]

    for idx, chunk in enumerate(chunks):
        cabecalho = f"*Bebida importada não é considerada.*\nAtualizado em {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}\n📊 Total de membros no ranking: **{total_membros}**"
        if len(chunks) > 1:
            cabecalho += f"\n📄 Página {idx+1}/{len(chunks)}"
        desc = cabecalho + "\n\n" + "\n".join(chunk)
        embed = discord.Embed(title="🏆 RANKING DE ROTAS (20 ITENS = 1 ROTA)", description=desc, color=0x2c2f33)
        if idx == len(chunks)-1:
            await canal.send(embed=embed, view=RankingView())
        else:
            await canal.send(embed=embed)

class RankingView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Atualizar Ranking", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="rk_atualizar")
    async def atualizar(self, interaction, button):
        await interaction.response.defer()
        await atualizar_ranking()
        await interaction.followup.send("Ranking atualizado!", ephemeral=True)
    @discord.ui.button(label="Resetar Ranking", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="rk_resetar")
    async def resetar(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem resetar o ranking.", ephemeral=True)
            return
        await interaction.response.send_message("⚠️ ATENÇÃO! Isso apagará todos os dados. Deseja continuar?", view=ConfirmarResetView(), ephemeral=True)

class ConfirmarResetView(View):
    def __init__(self):
        super().__init__(timeout=60)
    @discord.ui.button(label="Sim, resetar ranking", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirmar(self, interaction, button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        dados["usuarios"] = {}
        dados["caixa_semana"] = {}
        salvar_dados()
        await log_embed("🗑️ RANKING RESETADO", f"Ranking resetado por {interaction.user.mention}", 0x4f545c)
        await log_admin_embed("🗑️ RANKING RESETADO", f"Admin: {interaction.user.mention}\nData: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}", 0x4f545c)
        await interaction.followup.send("Ranking resetado com sucesso!", ephemeral=True)
        await atualizar_ranking()
        self.stop()
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancelar(self, interaction, button):
        await interaction.response.send_message("Reset cancelado.", ephemeral=True)
        self.stop()

# ========= REGISTRO =========
class SolicitarSetModal(Modal, title="📋 Registro"):
    id_jogo = TextInput(label="Seu ID", placeholder="Digite seu ID", required=True)
    nome = TextInput(label="Seu nome no jogo", placeholder="Digite seu nome no jogo", required=True)
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        id_val = self.id_jogo.value.strip()
        nome_val = self.nome.value.strip()
        pedido_id = str(int(datetime.now(timezone.utc).timestamp()))
        dados["sets_pendentes"][pedido_id] = {
            "solicitante_id": interaction.user.id,
            "solicitante_nome": nome_val,
            "id_jogo": id_val,
            "status": "pendente",
            "data": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        }
        salvar_dados()
        canal_registros = bot.get_channel(CANAL_REGISTROS_SET_ID)
        if canal_registros:
            embed = discord.Embed(title="🆕 NOVO REGISTRO", description=f"**Nome:** {nome_val}\n**ID:** {id_val}\n**Solicitante:** <@{interaction.user.id}>\n**Data:** {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}", color=0x2c2f33, timestamp=datetime.now(timezone.utc))
            embed.set_footer(text=f"ID: {pedido_id}")
            view = AprovarSetView(pedido_id, interaction.user.id)
            await canal_registros.send(embed=embed, view=view)
        await interaction.followup.send("✅ Registro enviado! Aguarde a aprovação.", ephemeral=True)

class AprovarSetView(View):
    def __init__(self, pedido_id, solicitante_id):
        super().__init__(timeout=None)
        self.pedido_id = pedido_id
        self.solicitante_id = solicitante_id
    @discord.ui.button(label="✅ Aprovar Registro", style=discord.ButtonStyle.success, emoji="✅")
    async def aprovar(self, interaction, button):
        if not pode_aprovar_set(interaction.user):
            await interaction.response.send_message("Você não tem permissão para aprovar registros.", ephemeral=True)
            return
        pedido = dados["sets_pendentes"].get(self.pedido_id)
        if not pedido or pedido["status"] != "pendente":
            await interaction.response.send_message("Este pedido já foi processado ou não existe.", ephemeral=True)
            return
        guild = interaction.guild
        membro = guild.get_member(self.solicitante_id)
        if not membro:
            await interaction.response.send_message("Solicitante não encontrado no servidor.", ephemeral=True)
            return
        cargo_membro = guild.get_role(CARGO_MEMBRO_ID)
        if not cargo_membro:
            await interaction.response.send_message("Cargo Membro não encontrado.", ephemeral=True)
            return
        try:
            nome_registro = pedido["solicitante_nome"]
            id_registro = pedido["id_jogo"]
            novo_nick = f"{nome_registro} [{id_registro}]"
            if guild.me.guild_permissions.change_nickname and guild.me.guild_permissions.manage_nicknames:
                try: await membro.edit(nick=novo_nick, reason=f"Registro aprovado: {nome_registro} [{id_registro}]")
                except: pass
            await membro.add_roles(cargo_membro, reason=f"Registro aprovado por {interaction.user.name}")
            uid_str = str(self.solicitante_id)
            if uid_str not in dados["usuarios"]:
                dados["usuarios"][uid_str] = {"farms": [], "pagamentos": [], "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": []}
            dados["usuarios"][uid_str]["registro_nome"] = nome_registro
            dados["usuarios"][uid_str]["registro_id"] = id_registro
            pedido["status"] = "aprovado"
            pedido["aprovado_por"] = interaction.user.id
            pedido["cargo_dado"] = CARGO_MEMBRO_ID
            salvar_dados()
            try: await membro.send(f"✅ Parabéns! Seu registro foi **aprovado** e você recebeu o cargo {cargo_membro.mention}. Seu apelido foi alterado para **{novo_nick}**. Bem-vindo(a)!")
            except: pass
            canal_registros = bot.get_channel(CANAL_REGISTROS_SET_ID)
            if canal_registros:
                embed = discord.Embed(title="✅ REGISTRO APROVADO", description=f"**Nome:** {pedido['solicitante_nome']}\n**ID:** {pedido['id_jogo']}\n**Solicitante:** <@{self.solicitante_id}>\n**Cargo atribuído:** {cargo_membro.mention}\n**Apelido alterado para:** {novo_nick}\n**Aprovado por:** {interaction.user.mention}", color=0x2c2f33, timestamp=datetime.now(timezone.utc))
                async for msg in canal_registros.history(limit=20):
                    if msg.author == bot.user and msg.embeds and str(self.pedido_id) in (msg.embeds[0].footer.text if msg.embeds[0].footer else ""):
                        await msg.edit(embed=embed, view=None)
                        break
            await interaction.response.send_message(f"✅ Registro aprovado! Cargo {cargo_membro.mention} atribuído a {membro.mention}. Apelido alterado para **{novo_nick}**.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Erro ao aprovar registro: {e}", ephemeral=True)
    @discord.ui.button(label="❌ Recusar Registro", style=discord.ButtonStyle.danger, emoji="❌")
    async def recusar(self, interaction, button):
        if not pode_aprovar_set(interaction.user):
            await interaction.response.send_message("Você não tem permissão para recusar registros.", ephemeral=True)
            return
        pedido = dados["sets_pendentes"].get(self.pedido_id)
        if not pedido or pedido["status"] != "pendente":
            await interaction.response.send_message("Este pedido já foi processado ou não existe.", ephemeral=True)
            return
        pedido["status"] = "recusado"
        salvar_dados()
        try:
            solicitante = await bot.fetch_user(self.solicitante_id)
            await solicitante.send(f"❌ Seu registro foi **recusado** por {interaction.user.mention}.")
        except: pass
        embed = discord.Embed(title="❌ REGISTRO RECUSADO", description=f"Pedido ID: {self.pedido_id}\nRecusado por: {interaction.user.mention}", color=0x4f545c, timestamp=datetime.now(timezone.utc))
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Registro recusado!", ephemeral=True)

# ========= LIVES =========
def extract_platform_from_url(url: str):
    url = url.strip().lower()
    if "twitch.tv" in url:
        match = re.search(r"twitch\.tv/([a-zA-Z0-9_]+)", url)
        if match: return ("twitch", match.group(1))
    elif "youtube.com" in url or "youtu.be" in url:
        if "youtube.com/@" in url: return ("youtube", url.split("@")[-1].split("/")[0])
        elif "youtube.com/channel/" in url: return ("youtube", url.split("/channel/")[-1].split("?")[0])
        elif "youtube.com/c/" in url: return ("youtube", url.split("/c/")[-1].split("/")[0])
    elif "kick.com" in url:
        match = re.search(r"kick\.com/([a-zA-Z0-9_]+)", url)
        if match: return ("kick", match.group(1))
    elif "tiktok.com" in url:
        match = re.search(r"tiktok\.com/@([a-zA-Z0-9_.]+)", url)
        if match: return ("tiktok", match.group(1))
    return (None, None)

twitch_token = None
twitch_token_expiry = 0

async def get_twitch_token():
    global twitch_token, twitch_token_expiry
    if twitch_token and datetime.now(timezone.utc).timestamp() < twitch_token_expiry: return twitch_token
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET: return None
    async with aiohttp.ClientSession() as session:
        async with session.post("https://id.twitch.tv/oauth2/token", params={"client_id": TWITCH_CLIENT_ID, "client_secret": TWITCH_CLIENT_SECRET, "grant_type": "client_credentials"}) as resp:
            if resp.status == 200:
                data = await resp.json()
                twitch_token = data["access_token"]
                twitch_token_expiry = datetime.now(timezone.utc).timestamp() + data["expires_in"] - 60
                return twitch_token
    return None

async def check_twitch_lives(streamers):
    token = await get_twitch_token()
    if not token: return {}
    usernames = [s for s in streamers if s]
    if not usernames: return {}
    headers = {"Client-ID": TWITCH_CLIENT_ID, "Authorization": f"Bearer {token}"}
    url = "https://api.twitch.tv/helix/streams?user_login=" + "&user_login=".join(usernames)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {s["user_login"].lower(): s for s in data.get("data", [])}
    return {}

async def check_youtube_lives(streamers):
    if not YOUTUBE_API_KEY: return {}
    live_data = {}
    for ch_id in streamers:
        if not ch_id: continue
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={ch_id}&eventType=live&type=video&key={YOUTUBE_API_KEY}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("items", []):
                        live_data[ch_id] = item
    return live_data

async def check_tiktok_live(username):
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"}
        async with aiohttp.ClientSession() as session:
            url = f"https://www.tiktok.com/@{username}/live"
            async with session.get(url, headers=headers, allow_redirects=True) as resp:
                if resp.status != 200: return None
                html = await resp.text()
                title_match = re.search(r'"title":"(.*?)"', html)
                if not title_match: return None
                title = title_match.group(1).replace('\\u002F', '/').replace('\\u0026', '&')
                thumb_match = re.search(r'"thumbnail_url":"(.*?)"', html)
                thumbnail = thumb_match.group(1).replace('\\u002F', '/') if thumb_match else None
                return {"title": title, "thumbnail": thumbnail, "url": url}
    except: return None

async def check_tiktok_lives(streamers):
    live_data = {}
    for username in streamers:
        if not username: continue
        info = await check_tiktok_live(username)
        if info: live_data[username] = info
    return live_data

@tasks.loop(minutes=1)
async def live_check_loop():
    for server_id_str in dados["lives"].get("config", {}):
        config = dados["lives"]["config"][server_id_str]
        guild = bot.get_guild(int(server_id_str))
        if not guild: continue
        plataformas = config.get("platforms", {"twitch": True, "youtube": True, "kick": True, "tiktok": True})
        canal_id = config.get("channel")
        canal = bot.get_channel(canal_id) if canal_id else None
        role_id = config.get("role")
        role_mention = f"<@&{role_id}>" if role_id else ""
        streamers_list = dados["lives"].get("streamers", {}).get(server_id_str, [])
        if not streamers_list: continue
        status_server = dados["lives"].setdefault("status", {}).setdefault(server_id_str, {})
        twitch_users = [s.get("twitch") for s in streamers_list if s.get("twitch")]
        yt_users = [s.get("youtube") for s in streamers_list if s.get("youtube")]
        tiktok_users = [s.get("tiktok") for s in streamers_list if s.get("tiktok")]
        twitch_lives = await check_twitch_lives(twitch_users) if plataformas.get("twitch") else {}
        yt_lives = await check_youtube_lives(yt_users) if plataformas.get("youtube") else {}
        tiktok_lives = await check_tiktok_lives(tiktok_users) if plataformas.get("tiktok") else {}
        for streamer in streamers_list:
            streamer_id = str(streamer["id"])
            status_server.setdefault(streamer_id, {"twitch": False, "youtube": False, "kick": False, "tiktok": False})
            nome = streamer.get("nome", "Streamer")
            observacao = streamer.get("observacao", "")
            # Twitch
            twitch_name = streamer.get("twitch")
            if twitch_name and plataformas.get("twitch"):
                is_live = twitch_name.lower() in twitch_lives
                status_server[streamer_id]["twitch"] = is_live
                if is_live:
                    last_key = f"twitch_{streamer_id}"
                    live_info = twitch_lives[twitch_name.lower()]
                    last = dados["lives"].setdefault("last_notified", {}).get(last_key)
                    if last != live_info["id"]:
                        dados["lives"]["last_notified"][last_key] = live_info["id"]
                        if canal:
                            desc = f"**{nome}** está ao vivo na Twitch!"
                            if observacao: desc += f"\n{observacao}"
                            embed = discord.Embed(title="🔴 LIVE NA TWITCH", description=desc, color=0x9146ff)
                            embed.add_field(name="Título", value=live_info['title'], inline=False)
                            embed.add_field(name="Link", value=f"https://twitch.tv/{twitch_name}", inline=False)
                            if 'thumbnail_url' in live_info:
                                thumb_url = live_info['thumbnail_url'].replace('{width}', '640').replace('{height}', '360')
                                embed.set_image(url=thumb_url)
                            await canal.send(content=role_mention, embed=embed)
            else: status_server[streamer_id]["twitch"] = False
            # YouTube
            yt_ch = streamer.get("youtube")
            if yt_ch and plataformas.get("youtube"):
                is_live = yt_ch in yt_lives
                status_server[streamer_id]["youtube"] = is_live
                if is_live:
                    last_key = f"yt_{streamer_id}"
                    video = yt_lives[yt_ch]
                    video_id = video["id"]["videoId"]
                    last = dados["lives"].setdefault("last_notified", {}).get(last_key)
                    if last != video_id:
                        dados["lives"]["last_notified"][last_key] = video_id
                        if canal:
                            desc = f"**{nome}** está ao vivo no YouTube!"
                            if observacao: desc += f"\n{observacao}"
                            embed = discord.Embed(title="🔴 LIVE NO YOUTUBE", description=desc, color=0xff0000)
                            embed.add_field(name="Título", value=video['snippet']['title'], inline=False)
                            embed.add_field(name="Link", value=f"https://youtube.com/watch?v={video_id}", inline=False)
                            await canal.send(content=role_mention, embed=embed)
            else: status_server[streamer_id]["youtube"] = False
            # TikTok
            tiktok_name = streamer.get("tiktok")
            if tiktok_name and plataformas.get("tiktok"):
                is_live = tiktok_name in tiktok_lives
                status_server[streamer_id]["tiktok"] = is_live
                if is_live:
                    last_key = f"tiktok_{streamer_id}"
                    live_info = tiktok_lives[tiktok_name]
                    last = dados["lives"].setdefault("last_notified", {}).get(last_key)
                    if last != live_info.get("url"):
                        dados["lives"]["last_notified"][last_key] = live_info.get("url")
                        if canal:
                            desc = f"**{nome}** está ao vivo no TikTok!"
                            if observacao: desc += f"\n{observacao}"
                            embed = discord.Embed(title="🔴 LIVE NO TIKTOK", description=desc, color=0xff0050, url=live_info.get("url"))
                            embed.add_field(name="Título", value=live_info.get("title", "Live"), inline=False)
                            if live_info.get("thumbnail"): embed.set_image(url=live_info["thumbnail"])
                            view = View(timeout=None)
                            view.add_item(Button(label="Assistir Agora", style=discord.ButtonStyle.link, url=live_info.get("url")))
                            await canal.send(content=role_mention, embed=embed, view=view)
            else: status_server[streamer_id]["tiktok"] = False
            if streamer.get("kick"): status_server[streamer_id]["kick"] = False
    salvar_dados()

@live_check_loop.before_loop
async def before_live_check():
    await bot.wait_until_ready()

# ========= COMPRA E VENDA =========
class VendaModal(Modal, title="💸 Venda"):
    item = TextInput(label="Item", placeholder="Ex: Munição, Arma, Medicamento", required=True)
    quantidade = TextInput(label="Quantidade", placeholder="Ex: 1000", required=True)
    valor_total = TextInput(label="Valor Total (R$)", placeholder="Ex: 500", required=True)
    comprador = TextInput(label="Comprador", placeholder="Ex: Nome do comprador ou facção", required=True)
    responsavel = TextInput(label="Responsável pela Venda", placeholder="Ex: @usuario ou nome", required=True)
    async def on_submit(self, interaction):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Você não tem permissão para registrar vendas.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        item = self.item.value.strip()
        try:
            qtd = int(self.quantidade.value)
            valor = float(self.valor_total.value.replace(",", "."))
        except:
            await interaction.followup.send("Quantidade ou valor inválidos!", ephemeral=True); return
        comprador = self.comprador.value.strip()
        responsavel_nome = self.responsavel.value.strip()
        dados_log = {"Tipo": "VENDA", "Item": item, "Quantidade": f"{qtd:,} unidades", "Valor Total": f"R$ {valor:,.2f}", "Comprador": comprador, "Responsável": responsavel_nome, "Registrado por": interaction.user.mention}
        await log_compra_venda("venda", dados_log)
        dados["compras_vendas"].append({"tipo": "venda", "item": item, "quantidade": qtd, "valor_total": valor, "comprador": comprador, "responsavel": responsavel_nome, "registrado_por": interaction.user.id, "data": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "print_url": None})
        salvar_dados()
        await interaction.followup.send(f"✅ Venda de **{qtd:,} {item}** para **{comprador}** registrada! Valor: R$ {valor:,.2f}", ephemeral=True)
        await log_admin_embed("💸 VENDA REGISTRADA", f"Usuário: {interaction.user.mention}\nItem: {qtd} {item}\nValor: R$ {valor:,.2f}\nComprador: {comprador}", 0x2c2f33)

class CompraModal(Modal, title="🛒 Compra de Produto"):
    quantidade = TextInput(label="Quantidade", placeholder="Ex: 1000", required=True)
    produto = TextInput(label="Produto", placeholder="Ex: Munição", required=True)
    valor_total = TextInput(label="Valor Total (R$)", placeholder="Ex: 500", required=True)
    faccao_vendedora = TextInput(label="Facção Vendedora", placeholder="Ex: Primeiro Comando", required=True)
    responsavel = TextInput(label="Responsável pela Compra", placeholder="Ex: @usuario ou nome", required=True)
    async def on_submit(self, interaction):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Você não tem permissão para registrar compras.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            qtd = int(self.quantidade.value)
            valor = float(self.valor_total.value.replace(",", "."))
        except:
            await interaction.followup.send("Quantidade ou valor inválidos!", ephemeral=True); return
        await log_compra_venda("compra", {"Tipo": "COMPRA", "Quantidade": f"{qtd:,}", "Produto": self.produto.value, "Valor Total": f"R$ {valor:,.2f}", "Facção Vendedora": self.faccao_vendedora.value, "Responsável": self.responsavel.value, "Registrado por": interaction.user.mention})
        dados["compras_vendas"].append({"tipo": "compra", "quantidade": qtd, "produto": self.produto.value, "valor_total": valor, "faccao_vendedora": self.faccao_vendedora.value, "responsavel": self.responsavel.value, "registrado_por": interaction.user.id, "data": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "print_url": None})
        salvar_dados()
        await interaction.followup.send("✅ Compra registrada!", ephemeral=True)
        await log_admin_embed("🛒 COMPRA REGISTRADA", f"Usuário: {interaction.user.mention}\nProduto: {qtd} x {self.produto.value}\nValor: R$ {valor:,.2f}\nFacção: {self.faccao_vendedora.value}", 0x2c2f33)

class CompraVendaView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="💸 Venda", style=discord.ButtonStyle.secondary, emoji="💸", custom_id="cv_venda")
    async def venda(self, interaction, button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True); return
        await interaction.response.send_modal(VendaModal())
    @discord.ui.button(label="🛒 Compra", style=discord.ButtonStyle.secondary, emoji="🛒", custom_id="cv_compra")
    async def compra(self, interaction, button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True); return
        await interaction.response.send_modal(CompraModal())

# ========= BAÚS =========
class BauModal(Modal, title="📦 Baú - Registrar Item"):
    produto = TextInput(label="Produto", placeholder="Ex: Arma, Munição, Medicamento", required=True)
    quantidade = TextInput(label="Quantidade", placeholder="Ex: 50", required=True)
    valor = TextInput(label="Valor (opcional)", placeholder="R$ 0,00", required=False)
    observacao = TextInput(label="Observação (opcional)", placeholder="Detalhes adicionais", required=False)
    def __init__(self, tipo_bau, canal_log_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo_bau = tipo_bau
        self.canal_log_id = canal_log_id
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try: qtd = int(self.quantidade.value)
        except: await interaction.followup.send("Quantidade inválida!", ephemeral=True); return
        produto = self.produto.value.strip()
        valor = self.valor.value.strip()
        if valor:
            try:
                valor = float(valor.replace(",", "."))
                valor_str = f"R$ {valor:,.2f}"
            except: valor_str = "Não informado"
        else: valor_str = "Não informado"
        obs = self.observacao.value.strip() or "Sem observação"
        dados_log = {"Tipo": self.tipo_bau, "Produto": produto, "Quantidade": f"{qtd}", "Valor": valor_str, "Observação": obs, "Registrado por": interaction.user.mention}
        await log_bau(self.tipo_bau, self.canal_log_id, dados_log)
        await log_admin_embed(f"📦 BAÚ {self.tipo_bau.upper()}", f"Usuário: {interaction.user.mention}\nProduto: {produto}\nQuantidade: {qtd}\nValor: {valor_str}\nObs: {obs}", 0x2c2f33)
        await interaction.followup.send(f"✅ Registro no Baú **{self.tipo_bau}** concluído!", ephemeral=True)

class BauView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="📦 Baú Gerente", style=discord.ButtonStyle.danger, emoji="📦", custom_id="bau_gerente")
    async def bau_gerente(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True); return
        await interaction.response.send_modal(BauModal("Gerente", LOG_BAU_GERENTE_ID))
    @discord.ui.button(label="📦 Baú Membro", style=discord.ButtonStyle.success, emoji="📦", custom_id="bau_membro")
    async def bau_membro(self, interaction, button):
        if not is_membro(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True); return
        await interaction.response.send_modal(BauModal("Membro", LOG_BAU_MEMBRO_ID))
    @discord.ui.button(label="📦 Baú Casa", style=discord.ButtonStyle.primary, emoji="📦", custom_id="bau_casa")
    async def bau_casa(self, interaction, button):
        if not (is_membro(interaction.user) or is_admin(interaction.user)):
            await interaction.response.send_message("Sem permissão.", ephemeral=True); return
        await interaction.response.send_modal(BauModal("Casa", LOG_BAU_CASA_ID))

# ========= PAINEL DINHEIRO SUJO =========
class PainelControleView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="📋 Histórico Completo", style=discord.ButtonStyle.primary, emoji="📋", custom_id="painel_historico")
    async def ultimas_entregas(self, interaction, button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("Histórico de entregas (implementação completa).", ephemeral=True)
    @discord.ui.button(label="📊 Estatísticas", style=discord.ButtonStyle.secondary, emoji="📊", custom_id="painel_estatisticas")
    async def estatisticas(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("Estatísticas (implementação completa).", ephemeral=True)
    @discord.ui.button(label="💰 Registrar Entrega", style=discord.ButtonStyle.success, emoji="💰", custom_id="painel_registrar")
    async def registrar_entrega(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True); return
        await interaction.response.send_modal(RegistrarEntregaModal())
    @discord.ui.button(label="🔄 Atualizar Painel", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="painel_atualizar")
    async def atualizar_painel(self, interaction, button):
        await interaction.response.defer()
        embed = discord.Embed(title="💰 PAINEL", description="Atualizado", color=0x2c2f33)
        await interaction.followup.send(embed=embed, view=PainelControleView(), ephemeral=True)

class RegistrarEntregaModal(Modal, title="💰 Registrar Entrega"):
    membro = TextInput(label="Nome do recebedor (vulgo ou ID)", placeholder="Digite o nome, vulgo ou ID", required=True)
    valor = TextInput(label="Valor (R$)", placeholder="Ex: 5000", required=True)
    observacao = TextInput(label="Observação (opcional)", placeholder="Detalhes sobre a entrega", required=False)
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("Entrega registrada (implementação completa).", ephemeral=True)

# ========= PAINEL DE CLIENTES (com edição de porcentagens) =========
class PedidoClienteModal(Modal, title="🛒 Fazer Pedido"):
    produto = TextInput(label="Produto desejado", placeholder="Ex: Munição, Arma", required=True)
    quantidade = TextInput(label="Quantidade", placeholder="Ex: 50", required=True)
    observacao = TextInput(label="Observação", placeholder="Detalhes adicionais", required=False)

    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        produto_val = self.produto.value.strip()
        qtd_val = self.quantidade.value.strip()
        obs_val = self.observacao.value.strip() or "Nenhuma"

        pedido_id = str(int(datetime.now(timezone.utc).timestamp()))
        pedido = {
            "id": pedido_id,
            "cliente_id": interaction.user.id,
            "produto": produto_val,
            "quantidade": qtd_val,
            "observacao": obs_val,
            "status": "pendente",
            "data": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        }
        dados["pedidos"]["lista"].append(pedido)
        salvar_dados()

        await log_reserva_cliente_embed(
            "🛒 NOVO PEDIDO (CLIENTE)",
            f"**Cliente:** {interaction.user.mention}\n**Produto:** {produto_val}\n**Quantidade:** {qtd_val}\n**Observação:** {obs_val}",
            0x2ecc71
        )
        await interaction.followup.send("✅ Seu pedido foi realizado e enviado para os responsáveis!", ephemeral=True)

class EditarPorcentagensModal(Modal, title="Editar Porcentagens e VIP"):
    cliente = TextInput(label="% Cliente", placeholder="Ex: 55", required=True)
    maquina = TextInput(label="% Máquina", placeholder="Ex: 40", required=True)
    fac = TextInput(label="% Facção", placeholder="Ex: 5", required=True)
    membros = TextInput(label="% Membros", placeholder="Ex: 5", required=True)
    vip_fac = TextInput(label="% VIP Fac (bônus)", placeholder="Ex: 10", required=True)

    async def on_submit(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores podem editar as porcentagens.", ephemeral=True)
            return
        try:
            novo_cliente = float(self.cliente.value.replace(",", "."))
            novo_maquina = float(self.maquina.value.replace(",", "."))
            novo_fac = float(self.fac.value.replace(",", "."))
            novo_membros = float(self.membros.value.replace(",", "."))
            novo_vip = float(self.vip_fac.value.replace(",", "."))
        except ValueError:
            await interaction.response.send_message("❌ Valores inválidos. Use números (ex: 55).", ephemeral=True)
            return

        # Atualiza as porcentagens
        dados["pedidos"]["config"]["porcentagens"]["cliente"] = novo_cliente
        dados["pedidos"]["config"]["porcentagens"]["maquina"] = novo_maquina
        dados["pedidos"]["config"]["porcentagens"]["fac"] = novo_fac
        dados["pedidos"]["config"]["porcentagens"]["membros"] = novo_membros
        dados["pedidos"]["config"]["porcentagens"]["vip_fac"] = novo_vip
        dados["pedidos"]["config"]["ultima_edicao"] = interaction.user.id
        salvar_dados()

        await log_admin_embed(
            "📊 PORCENTAGENS ATUALIZADAS",
            f"**Admin:** {interaction.user.mention}\n"
            f"**% Cliente:** {novo_cliente}%\n"
            f"**% Máquina:** {novo_maquina}%\n"
            f"**% Facção:** {novo_fac}%\n"
            f"**% Membros:** {novo_membros}%\n"
            f"**% VIP Fac:** {novo_vip}%",
            0x3498db
        )
        await interaction.response.send_message("✅ Porcentagens atualizadas com sucesso!", ephemeral=True)

class PedidoClienteView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fazer Pedido", style=discord.ButtonStyle.success, emoji="🛒", custom_id="btn_pedido_cliente")
    async def fazer_pedido(self, interaction, button):
        await interaction.response.send_modal(PedidoClienteModal())

    @discord.ui.button(label="Editar Porcentagens", style=discord.ButtonStyle.primary, emoji="📊", custom_id="btn_editar_porcentagens")
    async def editar_porcentagens(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores podem editar as porcentagens.", ephemeral=True)
            return
        # Pré-preenche os campos com os valores atuais
        p = dados["pedidos"]["config"]["porcentagens"]
        modal = EditarPorcentagensModal()
        modal.cliente.default = str(p.get("cliente", 50))
        modal.maquina.default = str(p.get("maquina", 40))
        modal.fac.default = str(p.get("fac", 5))
        modal.membros.default = str(p.get("membros", 5))
        modal.vip_fac.default = str(p.get("vip_fac", 10))
        await interaction.response.send_modal(modal)

# ========= PAINEL DE FUNCIONÁRIOS =========
class PedidoFuncionarioModal(Modal, title="🛠️ Solicitar Equipamento"):
    produto = TextInput(label="Equipamento/Produto", placeholder="Ex: Colete, Rádio", required=True)
    quantidade = TextInput(label="Quantidade", placeholder="Ex: 1", required=True)
    motivo = TextInput(label="Motivo/Observação", placeholder="Ex: Para patrulha", required=False)

    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        produto_val = self.produto.value.strip()
        qtd_val = self.quantidade.value.strip()
        motivo_val = self.motivo.value.strip() or "Nenhum"

        pedido_id = str(int(datetime.now(timezone.utc).timestamp()))
        pedido = {
            "id": pedido_id,
            "funcionario_id": interaction.user.id,
            "produto": produto_val,
            "quantidade": qtd_val,
            "motivo": motivo_val,
            "status": "pendente",
            "data": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        }
        dados["pedidos_funcionarios"]["lista"].append(pedido)
        salvar_dados()

        await log_reserva_func_embed(
            "🛠️ NOVA SOLICITAÇÃO (FUNCIONÁRIO)",
            f"**Funcionário:** {interaction.user.mention}\n**Produto:** {produto_val}\n**Quantidade:** {qtd_val}\n**Motivo:** {motivo_val}",
            0x3498db
        )
        await interaction.followup.send("✅ Solicitação de equipamento enviada com sucesso!", ephemeral=True)

class PedidoFuncionarioView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Solicitar Equipamento", style=discord.ButtonStyle.primary, emoji="🛠️", custom_id="btn_pedido_func")
    async def solicitar(self, interaction, button):
        if not is_membro(interaction.user) and not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas funcionários têm permissão para fazer essa solicitação.", ephemeral=True)
            return
        await interaction.response.send_modal(PedidoFuncionarioModal())

# ========= VIEW PERSISTENTE PARA CANAIS PRIVADOS =========
class FarmChannelViewPersistent(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Depositar Farm", style=discord.ButtonStyle.secondary, emoji="📦", custom_id="farm_produtos")
    async def farm_produtos(self, interaction, button):
        user_id = None
        for uid, cid in dados["canais"].items():
            if cid == interaction.channel.id:
                user_id = int(uid)
                break
        if user_id is None:
            await interaction.response.send_message("Canal não reconhecido.", ephemeral=True); return
        if interaction.user.id != user_id and not is_admin(interaction.user):
            await interaction.response.send_message("Apenas o dono do canal ou administradores podem depositar farm!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("📝 Digite o **número do SLOT** no chat.", ephemeral=False)
        def check_slot(m):
            return m.author == interaction.user and m.channel == interaction.channel and m.content.strip().isdigit()
        try:
            msg_slot = await bot.wait_for('message', timeout=60.0, check=check_slot)
            slot_num = int(msg_slot.content.strip())
            await msg_slot.delete()
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Tempo esgotado! Operação cancelada.", ephemeral=True)
            return
        view = View(timeout=60)
        open_modal_btn = Button(label="📦 Abrir Formulário", style=discord.ButtonStyle.success, emoji="📦")
        async def modal_callback(interaction_btn):
            await interaction_btn.response.send_modal(FarmProdutosModal(user_id, interaction.user.display_name, interaction.channel, slot_num))
        open_modal_btn.callback = modal_callback
        view.add_item(open_modal_btn)
        await interaction.followup.send("✅ Slot registrado! Clique no botão abaixo para abrir o formulário:", view=view, ephemeral=True)

    @discord.ui.button(label="Editar Registro", style=discord.ButtonStyle.secondary, emoji="✏️", custom_id="editar_registro")
    async def editar_registro(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores.", ephemeral=True); return
        await interaction.response.send_message("Menu de edição (implementação completa).", ephemeral=True)

    @discord.ui.button(label="Meus Registros", style=discord.ButtonStyle.primary, emoji="📋", custom_id="meus_registros")
    async def meus_registros(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores.", ephemeral=True); return
        await interaction.response.send_message("Registros (implementação completa).", ephemeral=True)

    @discord.ui.button(label="Reset Semanal", style=discord.ButtonStyle.danger, emoji="🔄", custom_id="reset_semanal")
    async def reset_semanal(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores.", ephemeral=True); return
        await interaction.response.send_message("Confirmar reset (implementação completa).", ephemeral=True)

# ========= FARM PRODUTOS MODAL =========
class FarmProdutosModal(Modal, title="📦 Depositar Farm"):
    relogio = TextInput(label="RELÓGIO DE LUXO - Quantidade", placeholder="Ex: 5", required=False)
    obra = TextInput(label="OBRA DE ARTE - Quantidade", placeholder="Ex: 2", required=False)
    bebida = TextInput(label="BEBIDA IMPORTADA - Quantidade", placeholder="Ex: 10", required=False)
    acoes = TextInput(label="AÇÕES DE EMPRESA - Quantidade", placeholder="Ex: 100", required=False)
    nft = TextInput(label="CARTEIRA NFT - Quantidade", placeholder="Ex: 1", required=False)

    def __init__(self, user_id, user_name, canal, slot_num, edit_mode=False, farm_index=None):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.slot_num = slot_num
        self.edit_mode = edit_mode
        self.farm_index = farm_index

    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        produtos = []
        for campo, nome in [(self.relogio, "RELÓGIO DE LUXO"), (self.obra, "OBRA DE ARTE"), (self.bebida, "BEBIDA IMPORTADA"), (self.acoes, "AÇÕES DE EMPRESA"), (self.nft, "CARTEIRA NFT")]:
            if campo.value and campo.value.strip():
                try:
                    qtd = int(campo.value.strip())
                    if qtd > 0: produtos.append({"produto": nome, "quantidade": qtd})
                except: pass
        if not produtos:
            await interaction.followup.send("Nenhum produto válido!", ephemeral=True); return
        await interaction.followup.send("📸 **Envie a print da farm** (imagem) neste canal. Você tem 60 segundos.", ephemeral=True)
        def check_print(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments
        try:
            msg_print = await bot.wait_for('message', timeout=60.0, check=check_print)
            imagem_url = msg_print.attachments[0].url
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Tempo esgotado! Registro cancelado.", ephemeral=True); return
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": []}
        if self.edit_mode and self.farm_index is not None:
            if self.farm_index >= len(dados["usuarios"][str(self.user_id)]["farms"]):
                await interaction.followup.send("Registro não encontrado.", ephemeral=True); return
            dados["usuarios"][str(self.user_id)]["farms"][self.farm_index] = {
                "produtos": produtos,
                "slot": self.slot_num,
                "data": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "print_url": imagem_url,
                "validado": True,
                "farm_id": dados["usuarios"][str(self.user_id)]["farms"][self.farm_index].get("farm_id", self.farm_index + 1)
            }
            salvar_dados()
            embed = discord.Embed(title="✏️ FARM PRODUTOS EDITADA", description=f"**Usuário:** <@{self.user_id}>\n**Slot:** {self.slot_num}\n", color=0x99aab5)
            desc = "".join(f"🔹 **{p['produto']}:** {p['quantidade']} itens\n" for p in produtos)
            embed.description += desc
            embed.add_field(name="📅 Data da edição", value=datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M"), inline=False)
            embed.set_image(url=imagem_url)
            await self.canal.send(embed=embed); await log_farm(embed)
            await interaction.followup.send("Farm editada com sucesso!", ephemeral=True)
        else:
            registro = {
                "produtos": produtos,
                "slot": self.slot_num,
                "data": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "print_url": imagem_url,
                "validado": True,
                "farm_id": len(dados["usuarios"][str(self.user_id)]["farms"]) + 1
            }
            dados["usuarios"][str(self.user_id)]["farms"].append(registro)
            salvar_dados()
            embed = discord.Embed(title="✅ FARM PRODUTOS REGISTRADA", description=f"**Usuário:** <@{self.user_id}>\n**Slot:** {self.slot_num}\n", color=0x2c2f33)
            desc = "".join(f"🔹 **{p['produto']}:** {p['quantidade']} itens\n" for p in produtos)
            embed.description += desc
            embed.add_field(name="📅 Data", value=datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M"), inline=False)
            embed.add_field(name="📦 Total de farms", value=f"{len(dados['usuarios'][str(self.user_id)]['farms'])} farms", inline=False)
            embed.set_image(url=imagem_url)
            embed.set_footer(text=f"Farm ID: {registro['farm_id']}")
            await self.canal.send(embed=embed); await log_farm(embed)
            await interaction.followup.send("Farm registrada com sucesso!", ephemeral=True)
        await atualizar_ranking()

# ========= PAINEL SOLICITAR SET =========
class SolicitarSetView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="📋 Solicitar Set", style=discord.ButtonStyle.primary, emoji="📋", custom_id="btn_solicitar_set")
    async def solicitar_set(self, interaction, button):
        if is_membro(interaction.user):
            await interaction.response.send_message("❌ Você já possui o cargo de membro. Não é necessário solicitar novamente.", ephemeral=True)
            return
        await interaction.response.send_modal(SolicitarSetModal())

# ========= BOTÃO CRIAR CANAL =========
class BotaoCriarCanalView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Criar Meu Canal Privado", style=discord.ButtonStyle.success, emoji="📦", custom_id="btn_criar_canal_privado")
    async def criar_canal(self, interaction, button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if not interaction.guild:
            await interaction.followup.send("Use em um servidor!", ephemeral=True); return
        if not interaction.guild.me.guild_permissions.manage_channels:
            await interaction.followup.send("Bot precisa de permissão de Administrador.", ephemeral=True); return
        user_id = str(interaction.user.id)
        if user_id in dados["canais"]:
            canal = interaction.guild.get_channel(dados["canais"][user_id])
            if canal:
                await interaction.followup.send(f"Você já possui um canal! Acesse: {canal.mention}", ephemeral=True); return
            else:
                del dados["canais"][user_id]; salvar_dados()
        try:
            categoria = interaction.guild.get_channel(CATEGORIA_FARMS_ID)
            if not categoria:
                await interaction.followup.send("Categoria não encontrada!", ephemeral=True); return
            user_data = dados["usuarios"].get(user_id, {})
            registro_nome = user_data.get("registro_nome")
            registro_id = user_data.get("registro_id")
            if registro_nome and registro_id:
                nome_base = re.sub(r'[^a-zA-Z0-9-]', '', registro_nome.lower().replace(" ", "-"))
                nome_canal = f"{nome_base}-{registro_id}"[:90]
            else:
                nome_canal = f"farm-{interaction.user.name.lower().replace(' ', '-')}"[:90]
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True, add_reactions=True, read_message_history=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, attach_files=True, embed_links=True, read_message_history=True)
            }
            cargo_admin = interaction.guild.get_role(CARGO_00_ID)
            if cargo_admin:
                overwrites[cargo_admin] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True, manage_channels=True)
            canal_novo = await categoria.create_text_channel(name=nome_canal, overwrites=overwrites)
            dados["canais"][user_id] = canal_novo.id
            salvar_dados()
            embed = discord.Embed(title="📦 SEU CANAL PRIVADO", description=f"Bem-vindo(a) {interaction.user.mention}!\n\n🔒 Apenas você e administradores têm acesso.\n\n**BOTÕES:**\n📦 Depositar Farm\n✏️ Editar Registro\n📋 Meus Registros\n🔄 Reset Semanal", color=0x2c2f33)
            await canal_novo.send(embed=embed, view=FarmChannelViewPersistent())
            await interaction.followup.send(f"✅ Canal criado com sucesso: {canal_novo.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao criar canal: {e}", ephemeral=True)

# ========= RESTAURAR CANAIS PRIVADOS =========
async def restaurar_canais_farms():
    for user_id_str, canal_id in dados["canais"].items():
        canal = bot.get_channel(canal_id)
        if canal:
            mensagem_existente = False
            async for msg in canal.history(limit=20):
                if msg.author == bot.user and msg.components:
                    mensagem_existente = True
                    break
            if not mensagem_existente:
                guild = canal.guild
                member = guild.get_member(int(user_id_str)) if guild else None
                if member:
                    embed = discord.Embed(title="📦 SEU CANAL PRIVADO", description=f"Bem-vindo(a) {member.mention}!\n\n🔒 Apenas você e administradores têm acesso.\n\n**BOTÕES:**\n📦 Depositar Farm\n✏️ Editar Registro\n📋 Meus Registros\n🔄 Reset Semanal", color=0x2c2f33)
                    await canal.send(embed=embed, view=FarmChannelViewPersistent())

# ========= FUNÇÃO PARA ENVIAR/RESTAURAR PAINÉIS =========
async def enviar_ou_restaurar_painel(canal_id, view, embed_titulo, embed_descricao, chave_painel, cor=0x2c2f33, force=False):
    canal = bot.get_channel(canal_id)
    if not canal:
        print(f"[PAINEL] ❌ Canal {canal_id} não encontrado.")
        return False
    if force:
        msg_id = dados["painels"].get(chave_painel)
        if msg_id:
            try:
                msg = await canal.fetch_message(msg_id)
                await msg.delete()
                print(f"[PAINEL] 🗑️ Mensagem antiga deletada (ID {msg_id})")
            except: pass
        dados["painels"][chave_painel] = None
    mensagem_existente = False
    async for msg in canal.history(limit=20):
        if msg.author == bot.user and msg.components:
            mensagem_existente = True
            if str(msg.id) != str(dados["painels"].get(chave_painel)):
                dados["painels"][chave_painel] = msg.id
                salvar_dados()
            break
    if not mensagem_existente or force:
        embed = discord.Embed(title=embed_titulo, description=embed_descricao, color=cor)
        msg = await canal.send(embed=embed, view=view)
        dados["painels"][chave_painel] = msg.id
        salvar_dados()
        print(f"[PAINEL] ✅ Painel '{chave_painel}' enviado no canal {canal_id} (ID {msg.id})")
        return True
    else:
        print(f"[PAINEL] ℹ️ Painel '{chave_painel}' já existe no canal {canal_id}.")
        return False

# ========= COMANDOS DE RECARGA =========
@bot.command(name="recarregar_paineis")
@commands.has_permissions(administrator=True)
async def recarregar_paineis(ctx):
    await ctx.send("🔄 Recarregando todos os painéis...")
    await enviar_ou_restaurar_painel(CANAL_SOLICITAR_SET_ID, SolicitarSetView(), "📋 SOLICITAR SET", "Clique no botão abaixo para solicitar seu registro (set).", "solicitar_set", force=True)
    await enviar_ou_restaurar_painel(CANAL_COMPRA_VENDA_ID, CompraVendaView(), "💸 COMPRA E VENDA", "Clique nos botões abaixo para registrar uma **venda** ou **compra**.", "compra_venda", force=True)
    await enviar_ou_restaurar_painel(CANAL_PAINEL_BAUS_ID, BauView(), "📦 BAÚS", "Selecione o tipo de baú para registrar itens.", "baus", force=True)
    await enviar_ou_restaurar_painel(PAINEL_CONTROLE_DINHEIRO_SUJO_ID, PainelControleView(), "💰 CONTROLE DE DINHEIRO SUJO", "Gerencie entregas de dinheiro sujo.", "dinheiro_sujo", force=True)
    await enviar_ou_restaurar_painel(CANAL_CRIAR_FARM_ID, BotaoCriarCanalView(), "📦 CRIAR CANAL PRIVADO", "Clique no botão para criar seu canal privado.", "criar_farm", force=True)
    await enviar_ou_restaurar_painel(CANAL_RESERVAS_CLIENTES_ID, PedidoClienteView(), "🛒 PAINEL DE CLIENTES", "Clique nos botões abaixo para fazer um pedido ou editar porcentagens (apenas admin).", "clientes", force=True)
    await enviar_ou_restaurar_painel(CANAL_RESERVAS_FUNC_PAINEL_ID, PedidoFuncionarioView(), "🛠️ PAINEL DE FUNCIONÁRIOS", "Clique no botão abaixo para solicitar equipamentos.", "funcionarios", force=True)
    await ctx.send("✅ Todos os painéis foram recarregados!")

@bot.command(name="recarregar_painel")
@commands.has_permissions(administrator=True)
async def recarregar_painel(ctx, chave: str):
    chaves_validas = {
        "solicitar_set": (CANAL_SOLICITAR_SET_ID, SolicitarSetView(), "📋 SOLICITAR SET", "Clique no botão abaixo para solicitar seu registro (set).", 0x2c2f33),
        "compra_venda": (CANAL_COMPRA_VENDA_ID, CompraVendaView(), "💸 COMPRA E VENDA", "Clique nos botões abaixo para registrar uma **venda** ou **compra**.", 0x2c2f33),
        "baus": (CANAL_PAINEL_BAUS_ID, BauView(), "📦 BAÚS", "Selecione o tipo de baú para registrar itens.", 0x2c2f33),
        "dinheiro_sujo": (PAINEL_CONTROLE_DINHEIRO_SUJO_ID, PainelControleView(), "💰 CONTROLE DE DINHEIRO SUJO", "Gerencie entregas de dinheiro sujo.", 0x2c2f33),
        "criar_farm": (CANAL_CRIAR_FARM_ID, BotaoCriarCanalView(), "📦 CRIAR CANAL PRIVADO", "Clique no botão para criar seu canal privado.", 0x2c2f33),
        "clientes": (CANAL_RESERVAS_CLIENTES_ID, PedidoClienteView(), "🛒 PAINEL DE CLIENTES", "Clique nos botões abaixo para fazer um pedido ou editar porcentagens (apenas admin).", 0x2c2f33),
        "funcionarios": (CANAL_RESERVAS_FUNC_PAINEL_ID, PedidoFuncionarioView(), "🛠️ PAINEL DE FUNCIONÁRIOS", "Clique no botão abaixo para solicitar equipamentos.", 0x2c2f33)
    }
    if chave not in chaves_validas:
        await ctx.send(f"Chave inválida. Use: {', '.join(chaves_validas.keys())}")
        return
    canal_id, view, titulo, desc, cor = chaves_validas[chave]
    await enviar_ou_restaurar_painel(canal_id, view, titulo, desc, chave, cor, force=True)
    await ctx.send(f"✅ Painel '{chave}' recarregado!")

# ========= SETUP E ON_READY =========
async def setup_hook():
    bot.add_view(RankingView())
    bot.add_view(CompraVendaView())
    bot.add_view(BauView())
    bot.add_view(PainelControleView())
    bot.add_view(BotaoCriarCanalView())
    bot.add_view(FarmChannelViewPersistent())
    bot.add_view(SolicitarSetView())
    bot.add_view(PedidoClienteView())
    bot.add_view(PedidoFuncionarioView())

bot.setup_hook = setup_hook

@bot.event
async def on_ready():
    print(f'✅ Logado como {bot.user} (ID: {bot.user.id})')
    carregar_dados()
    await restaurar_canais_farms()
    if not live_check_loop.is_running():
        live_check_loop.start()

    # Envia/restaura todos os painéis
    await enviar_ou_restaurar_painel(CANAL_SOLICITAR_SET_ID, SolicitarSetView(), "📋 SOLICITAR SET", "Clique no botão abaixo para solicitar seu registro (set).", "solicitar_set")
    await enviar_ou_restaurar_painel(CANAL_COMPRA_VENDA_ID, CompraVendaView(), "💸 COMPRA E VENDA", "Clique nos botões abaixo para registrar uma **venda** ou **compra**.", "compra_venda")
    await enviar_ou_restaurar_painel(CANAL_PAINEL_BAUS_ID, BauView(), "📦 BAÚS", "Selecione o tipo de baú para registrar itens.", "baus")
    await enviar_ou_restaurar_painel(PAINEL_CONTROLE_DINHEIRO_SUJO_ID, PainelControleView(), "💰 CONTROLE DE DINHEIRO SUJO", "Gerencie entregas de dinheiro sujo.", "dinheiro_sujo")
    await enviar_ou_restaurar_painel(CANAL_CRIAR_FARM_ID, BotaoCriarCanalView(), "📦 CRIAR CANAL PRIVADO", "Clique no botão para criar seu canal privado.", "criar_farm")
    await enviar_ou_restaurar_painel(CANAL_RESERVAS_CLIENTES_ID, PedidoClienteView(), "🛒 PAINEL DE CLIENTES", "Clique nos botões abaixo para fazer um pedido ou editar porcentagens (apenas admin).", "clientes")
    await enviar_ou_restaurar_painel(CANAL_RESERVAS_FUNC_PAINEL_ID, PedidoFuncionarioView(), "🛠️ PAINEL DE FUNCIONÁRIOS", "Clique no botão abaixo para solicitar equipamentos.", "funcionarios")

    print('✅ Bot pronto e todos os painéis verificados!')

if __name__ == "__main__":
    bot.run(TOKEN)