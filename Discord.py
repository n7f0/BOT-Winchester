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

# IDs fornecidos
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

CARGO_ADMIN_IDS = [CARGO_00_ID, CARGO_01_ID, CARGO_02_ID, CARGO_GERENTE_ID]
CARGO_REMOVER_MEMBRO_IDS = CARGO_ADMIN_IDS

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

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
    "compras_vendas": []
}

def salvar_dados():
    with open("dados_bot.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_dados():
    try:
        with open("dados_bot.json", "r", encoding="utf-8") as f:
            loaded = json.load(f)
            dados.update(loaded)
            if "pedidos" not in dados:
                dados["pedidos"] = {"config": {"porcentagens": {"cliente": 50, "maquina": 40, "fac": 5, "membros": 5, "vip_fac": 10}, "ultima_edicao": None}, "lista": []}
            if "pedidos_funcionarios" not in dados:
                dados["pedidos_funcionarios"] = {"config": {"porcentagens": {"funcionario": 50, "maquina": 40, "fac": 5, "vip_fac": 10}, "ultima_edicao": None}, "lista": []}
            if "lives" not in dados:
                dados["lives"] = {"config": {}, "streamers": {}, "last_notified": {}, "status": {}}
            if "compras_vendas" not in dados:
                dados["compras_vendas"] = []
            if "vip_fac" not in dados["pedidos"]["config"]["porcentagens"]:
                dados["pedidos"]["config"]["porcentagens"]["vip_fac"] = 10
            if "vip_fac" not in dados["pedidos_funcionarios"]["config"]["porcentagens"]:
                dados["pedidos_funcionarios"]["config"]["porcentagens"]["vip_fac"] = 10
        return True
    except:
        return False

async def log_embed(titulo, descricao, cor, thumbnail=None, fields=None):
    canal_logs = bot.get_channel(CHAT_LOGS_ID)
    if canal_logs:
        embed = discord.Embed(title=titulo, description=descricao, color=cor, timestamp=datetime.now())
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        await canal_logs.send(embed=embed)

async def log_admin_embed(titulo, descricao, cor, thumbnail=None, fields=None):
    canal = bot.get_channel(CHAT_ADMIN_LOGS_ID)
    if canal:
        embed = discord.Embed(title=titulo, description=descricao, color=cor, timestamp=datetime.now())
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        await canal.send(embed=embed)

async def log_pedido_embed(titulo, descricao, cor, fields=None):
    canal = bot.get_channel(CHAT_PEDIDOS_LOG_ID)
    if canal:
        embed = discord.Embed(title=titulo, description=descricao, color=cor, timestamp=datetime.now())
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        await canal.send(embed=embed)

async def log_reserva_func_embed(titulo, descricao, cor, fields=None):
    canal = bot.get_channel(CANAL_RESERVAS_FUNC_LOGS_ID)
    if canal:
        embed = discord.Embed(title=titulo, description=descricao, color=cor, timestamp=datetime.now())
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        await canal.send(embed=embed)

async def log_compra_venda(tipo, dados_log):
    canal = bot.get_channel(CANAL_COMPRA_VENDA_LOGS_ID)
    if canal:
        embed = discord.Embed(title=f"📋 {tipo.upper()}", color=0x2c2f33, timestamp=datetime.now())
        for chave, valor in dados_log.items():
            embed.add_field(name=chave, value=valor, inline=False)
        await canal.send(embed=embed)

async def limpar_logs_usuario(user_id, user_name):
    if str(user_id) in dados["usuarios_banidos"]:
        return 0
    dados["usuarios_banidos"].append(str(user_id))
    total_limpo = 0
    for canal_id in [CHAT_LOGS_ID, CHAT_ADMIN_LOGS_ID, CHAT_RANK_ID]:
        canal = bot.get_channel(canal_id)
        if canal:
            async for msg in canal.history(limit=None):
                if msg.author == bot.user and (f"<@{user_id}>" in msg.content or f"<@!{user_id}>" in msg.content):
                    novo = msg.content.replace(f"<@{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]").replace(f"<@!{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]")
                    try:
                        await msg.edit(content=novo)
                        total_limpo += 1
                    except:
                        pass
    for canal_id in dados["canais"].values():
        canal = bot.get_channel(canal_id)
        if canal:
            async for msg in canal.history(limit=None):
                if msg.author == bot.user and (f"<@{user_id}>" in msg.content or f"<@!{user_id}>" in msg.content):
                    novo = msg.content.replace(f"<@{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]").replace(f"<@!{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]")
                    try:
                        await msg.edit(content=novo)
                        total_limpo += 1
                    except:
                        pass
    if str(user_id) in dados["usuarios"]:
        dados["usuarios"][str(user_id)] = {"farms": [], "pagamentos": [], "dinheiro_sujo": 0, "nome": f"[REMOVIDO - {user_name}]", "removido_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "transacoes_dinheiro_sujo": []}
        salvar_dados()
    if str(user_id) in dados["canais"]:
        canal = bot.get_channel(dados["canais"][str(user_id)])
        if canal:
            try:
                await canal.delete(reason=f"Usuário {user_name} removido")
            except:
                pass
        del dados["canais"][str(user_id)]
        salvar_dados()
    return total_limpo

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

def tem_cargo(member, cargos_ids):
    if not hasattr(member, 'guild'):
        return False
    for cid in cargos_ids:
        cargo = member.guild.get_role(cid)
        if cargo and cargo in member.roles:
            return True
    return False

def is_admin(member):
    return tem_cargo(member, CARGO_ADMIN_IDS)

def is_membro(member):
    return tem_cargo(member, [CARGO_MEMBRO_ID])

def pode_registrar_acao(member):
    return tem_cargo(member, CARGO_ADMIN_IDS)

def pode_aprovar_set(member):
    return pode_registrar_acao(member)

def pode_remover_membro(member):
    return tem_cargo(member, CARGO_REMOVER_MEMBRO_IDS)

# ========= RANKING =========
async def atualizar_ranking():
    canal = bot.get_channel(CHAT_RANK_ID)
    if not canal:
        return
    async for msg in canal.history(limit=50):
        if msg.author == bot.user:
            await msg.delete()
    usuarios_data = []
    for uid, data in dados["usuarios"].items():
        if "removido_em" in data:
            continue
        try:
            user = await bot.fetch_user(int(uid))
            tot_relogio = sum(p.get("quantidade", 0) for f in data.get("farms", []) for p in f.get("produtos", []) if p.get("produto") == "RELÓGIO DE LUXO")
            tot_obra = sum(p.get("quantidade", 0) for f in data.get("farms", []) for p in f.get("produtos", []) if p.get("produto") == "OBRA DE ARTE")
            tot_bebida = sum(p.get("quantidade", 0) for f in data.get("farms", []) for p in f.get("produtos", []) if p.get("produto") == "BEBIDA IMPORTADA")
            tot_acoes = sum(p.get("quantidade", 0) for f in data.get("farms", []) for p in f.get("produtos", []) if p.get("produto") == "AÇÕES DE EMPRESA")
            tot_nft = sum(p.get("quantidade", 0) for f in data.get("farms", []) for p in f.get("produtos", []) if p.get("produto") == "CARTEIRA NFT")
            usuarios_data.append({
                "nome": user.name,
                "total_relogio": tot_relogio,
                "total_obra": tot_obra,
                "total_bebida": tot_bebida,
                "total_acoes": tot_acoes,
                "total_nft": tot_nft
            })
        except:
            continue
    emb = discord.Embed(title="🏆 RANKING GERAL", description=f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", color=0x2c2f33)
    for nome, key in [("RELÓGIO LUXO", "total_relogio"), ("OBRA ARTE", "total_obra"), ("BEBIDA IMPORTADA", "total_bebida"), ("AÇÕES", "total_acoes"), ("CARTEIRA NFT", "total_nft")]:
        lista = sorted(usuarios_data, key=lambda x: x[key], reverse=True)[:5]
        txt = ""
        for i, u in enumerate(lista, 1):
            if u[key] == 0:
                continue
            emoji_rank = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}°"
            txt += f"{emoji_rank} **{u['nome']}** - {u[key]:,} itens\n"
        emb.add_field(name=nome, value=txt or "Nenhum dado ainda", inline=False)
    await canal.send(embed=emb, view=RankingView())

class RankingView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Atualizar Ranking", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def atualizar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await atualizar_ranking()
        await interaction.followup.send("Ranking atualizado!", ephemeral=True)
    @discord.ui.button(label="Resetar Ranking", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def resetar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem resetar o ranking.", ephemeral=True)
            return
        await interaction.response.send_message("⚠️ ATENÇÃO! Isso apagará todo o ranking. Deseja continuar?", view=ConfirmarResetView(), ephemeral=True)

class ConfirmarResetView(View):
    def __init__(self):
        super().__init__(timeout=60)
    @discord.ui.button(label="Sim, resetar ranking", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        dados["usuarios"] = {}
        dados["caixa_semana"] = {}
        salvar_dados()
        await log_embed("🗑️ RANKING RESETADO", f"Ranking resetado por {interaction.user.mention}", 0x4f545c)
        await log_admin_embed("🗑️ RANKING RESETADO", f"Admin: {interaction.user.mention}\nData: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0x4f545c)
        await interaction.followup.send("Ranking resetado com sucesso!", ephemeral=True)
        await atualizar_ranking()
        self.stop()
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Reset cancelado.", ephemeral=True)
        self.stop()

# ========= SISTEMA DE REGISTRO =========
class SolicitarSetModal(Modal, title="📋 Registro"):
    id_jogo = TextInput(label="Seu ID", placeholder="Digite seu ID", required=True)
    nome = TextInput(label="Seu nome no jogo", placeholder="Digite seu nome no jogo", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        id_val = self.id_jogo.value.strip()
        nome_val = self.nome.value.strip()
        pedido_id = str(int(datetime.now().timestamp()))
        dados["sets_pendentes"][pedido_id] = {
            "solicitante_id": interaction.user.id,
            "solicitante_nome": nome_val,
            "id_jogo": id_val,
            "status": "pendente",
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        salvar_dados()
        canal_registros = bot.get_channel(CANAL_REGISTROS_SET_ID)
        if canal_registros:
            embed = discord.Embed(
                title="🆕 NOVO REGISTRO",
                description=f"**Nome:** {nome_val}\n**ID:** {id_val}\n**Solicitante:** <@{interaction.user.id}>\n**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                color=0x2c2f33,
                timestamp=datetime.now()
            )
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
    async def aprovar(self, interaction: discord.Interaction, button: Button):
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
                try:
                    await membro.edit(nick=novo_nick, reason=f"Registro aprovado: {nome_registro} [{id_registro}]")
                except:
                    pass
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
            try:
                await membro.send(f"✅ Parabéns! Seu registro foi **aprovado** e você recebeu o cargo {cargo_membro.mention}. Seu apelido foi alterado para **{novo_nick}**. Bem-vindo(a)!")
            except:
                pass
            canal_registros = bot.get_channel(CANAL_REGISTROS_SET_ID)
            if canal_registros:
                embed = discord.Embed(
                    title="✅ REGISTRO APROVADO",
                    description=f"**Nome:** {pedido['solicitante_nome']}\n**ID:** {pedido['id_jogo']}\n**Solicitante:** <@{self.solicitante_id}>\n**Cargo atribuído:** {cargo_membro.mention}\n**Apelido alterado para:** {novo_nick}\n**Aprovado por:** {interaction.user.mention}",
                    color=0x2c2f33,
                    timestamp=datetime.now()
                )
                async for msg in canal_registros.history(limit=20):
                    if msg.author == bot.user and msg.embeds and str(self.pedido_id) in (msg.embeds[0].footer.text if msg.embeds[0].footer else ""):
                        await msg.edit(embed=embed, view=None)
                        break
            await interaction.response.send_message(f"✅ Registro aprovado! Cargo {cargo_membro.mention} atribuído a {membro.mention}. Apelido alterado para **{novo_nick}**.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Erro ao aprovar registro: {e}", ephemeral=True)
    @discord.ui.button(label="❌ Recusar Registro", style=discord.ButtonStyle.danger, emoji="❌")
    async def recusar(self, interaction: discord.Interaction, button: Button):
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
        except:
            pass
        embed = discord.Embed(title="❌ REGISTRO RECUSADO", description=f"Pedido ID: {self.pedido_id}\nRecusado por: {interaction.user.mention}", color=0x4f545c, timestamp=datetime.now())
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Registro recusado!", ephemeral=True)

# ========= SISTEMA DE LIVES =========
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
    if twitch_token and datetime.utcnow().timestamp() < twitch_token_expiry:
        return twitch_token
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        return None
    async with aiohttp.ClientSession() as session:
        async with session.post("https://id.twitch.tv/oauth2/token", params={"client_id": TWITCH_CLIENT_ID, "client_secret": TWITCH_CLIENT_SECRET, "grant_type": "client_credentials"}) as resp:
            if resp.status == 200:
                data = await resp.json()
                twitch_token = data["access_token"]
                twitch_token_expiry = datetime.utcnow().timestamp() + data["expires_in"] - 60
                return twitch_token
    return None

async def check_twitch_lives(streamers):
    token = await get_twitch_token()
    if not token:
        return {}
    usernames = [s for s in streamers if s]
    if not usernames:
        return {}
    headers = {"Client-ID": TWITCH_CLIENT_ID, "Authorization": f"Bearer {token}"}
    url = "https://api.twitch.tv/helix/streams?user_login=" + "&user_login=".join(usernames)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {s["user_login"].lower(): s for s in data.get("data", [])}
    return {}

async def check_youtube_lives(streamers):
    if not YOUTUBE_API_KEY:
        return {}
    live_data = {}
    for ch_id in streamers:
        if not ch_id:
            continue
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
                if resp.status != 200:
                    return None
                html = await resp.text()
                title_match = re.search(r'"title":"(.*?)"', html)
                if not title_match:
                    return None
                title = title_match.group(1).replace('\\u002F', '/').replace('\\u0026', '&')
                thumb_match = re.search(r'"thumbnail_url":"(.*?)"', html)
                thumbnail = thumb_match.group(1).replace('\\u002F', '/') if thumb_match else None
                return {"title": title, "thumbnail": thumbnail, "url": url}
    except:
        return None

async def check_tiktok_lives(streamers):
    live_data = {}
    for username in streamers:
        if not username:
            continue
        info = await check_tiktok_live(username)
        if info:
            live_data[username] = info
    return live_data

@tasks.loop(minutes=1)
async def live_check_loop():
    for server_id_str in dados["lives"]["config"]:
        config = dados["lives"]["config"][server_id_str]
        guild = bot.get_guild(int(server_id_str))
        if not guild:
            continue
        plataformas = config.get("platforms", {"twitch": True, "youtube": True, "kick": True, "tiktok": True})
        canal_id = config.get("channel")
        canal = bot.get_channel(canal_id) if canal_id else None
        role_id = config.get("role")
        role_mention = f"<@&{role_id}>" if role_id else ""
        streamers_dict = dados["lives"]["streamers"].get(server_id_str, {})
        status_server = dados["lives"]["status"].setdefault(server_id_str, {})
        if plataformas.get("twitch"):
            twitch_users = [data.get("twitch") for data in streamers_dict.values() if data.get("twitch")]
            lives = await check_twitch_lives(twitch_users)
            for uid, data in streamers_dict.items():
                twitch_name = data.get("twitch")
                status_server.setdefault(uid, {})["twitch"] = twitch_name.lower() in lives if twitch_name else False
                if twitch_name and twitch_name.lower() in lives:
                    last_key = f"twitch_{uid}"
                    live_info = lives[twitch_name.lower()]
                    last = dados["lives"]["last_notified"].get(last_key)
                    if last != live_info["id"]:
                        dados["lives"]["last_notified"][last_key] = live_info["id"]
                        nome_streamer = data.get("nome", twitch_name)
                        observacao = data.get("observacao", "")
                        if canal:
                            desc = f"**{nome_streamer}** está ao vivo!"
                            if observacao:
                                desc += f"\n{observacao}"
                            embed = discord.Embed(title="🔴 LIVE NA TWITCH", description=desc, color=0x9146ff)
                            embed.add_field(name="Título", value=live_info['title'], inline=False)
                            embed.add_field(name="Link", value=f"https://twitch.tv/{twitch_name}", inline=False)
                            if 'thumbnail_url' in live_info:
                                thumb_url = live_info['thumbnail_url'].replace('{width}', '640').replace('{height}', '360')
                                embed.set_image(url=thumb_url)
                            await canal.send(content=role_mention, embed=embed)
        if plataformas.get("youtube"):
            yt_users = [data.get("youtube") for data in streamers_dict.values() if data.get("youtube")]
            lives = await check_youtube_lives(yt_users)
            for uid, data in streamers_dict.items():
                yt_ch = data.get("youtube")
                status_server.setdefault(uid, {})["youtube"] = yt_ch in lives if yt_ch else False
                if yt_ch and yt_ch in lives:
                    last_key = f"yt_{uid}"
                    video = lives[yt_ch]
                    video_id = video["id"]["videoId"]
                    last = dados["lives"]["last_notified"].get(last_key)
                    if last != video_id:
                        dados["lives"]["last_notified"][last_key] = video_id
                        nome_streamer = data.get("nome", yt_ch)
                        observacao = data.get("observacao", "")
                        if canal:
                            desc = f"**{nome_streamer}** está ao vivo!"
                            if observacao:
                                desc += f"\n{observacao}"
                            embed = discord.Embed(title="🔴 LIVE NO YOUTUBE", description=desc, color=0xff0000)
                            embed.add_field(name="Título", value=video['snippet']['title'], inline=False)
                            embed.add_field(name="Link", value=f"https://youtube.com/watch?v={video_id}", inline=False)
                            await canal.send(content=role_mention, embed=embed)
        if plataformas.get("tiktok"):
            tiktok_users = [data.get("tiktok") for data in streamers_dict.values() if data.get("tiktok")]
            lives = await check_tiktok_lives(tiktok_users)
            for uid, data in streamers_dict.items():
                tiktok_name = data.get("tiktok")
                status_server.setdefault(uid, {})["tiktok"] = tiktok_name in lives if tiktok_name else False
                if tiktok_name and tiktok_name in lives:
                    last_key = f"tiktok_{uid}"
                    live_info = lives[tiktok_name]
                    last = dados["lives"]["last_notified"].get(last_key)
                    if last != live_info.get("url"):
                        dados["lives"]["last_notified"][last_key] = live_info.get("url")
                        nome_streamer = data.get("nome", tiktok_name)
                        observacao = data.get("observacao", "")
                        if canal:
                            desc = f"**{nome_streamer}** está ao vivo no TikTok!"
                            if observacao:
                                desc += f"\n{observacao}"
                            embed = discord.Embed(title="🔴 LIVE NO TIKTOK", description=desc, color=0xff0050, url=live_info.get("url"))
                            embed.add_field(name="Título", value=live_info.get("title", "Live"), inline=False)
                            if live_info.get("thumbnail"):
                                embed.set_image(url=live_info["thumbnail"])
                            view = View(timeout=None)
                            view.add_item(Button(label="Assistir Agora", style=discord.ButtonStyle.link, url=live_info.get("url")))
                            await canal.send(content=role_mention, embed=embed, view=view)
        for uid, data in streamers_dict.items():
            if data.get("kick"):
                status_server.setdefault(uid, {})["kick"] = False
    salvar_dados()

@live_check_loop.before_loop
async def before_live_check():
    await bot.wait_until_ready()

class LiveConfigView(View):
    def __init__(self, server_id):
        super().__init__(timeout=None)
        self.server_id = server_id

    async def get_config(self):
        return dados["lives"]["config"].setdefault(str(self.server_id), {"channel": None, "role": None, "platforms": {"twitch": True, "youtube": True, "kick": True, "tiktok": True}})

    async def build_embed(self):
        config = await self.get_config()
        canal_info = f"<#{config['channel']}>" if config['channel'] else "Não definido"
        cargo_info = f"<@&{config['role']}>" if config['role'] else "Não definido"
        plats = config['platforms']
        embed = discord.Embed(title="🔔 NOTIFICAÇÃO DE LIVES", color=0x99aab5)
        embed.add_field(name="📢 Canal", value=canal_info, inline=False)
        embed.add_field(name="👥 Cargo (ping)", value=cargo_info, inline=False)
        status = "\n".join([f"Twitch: {'✅ Ativado' if plats['twitch'] else '❌ Desativado'}",
                           f"YouTube: {'✅ Ativado' if plats['youtube'] else '❌ Desativado'}",
                           f"Kick: {'✅ Ativado' if plats['kick'] else '❌ Desativado'}",
                           f"TikTok: {'✅ Ativado' if plats['tiktok'] else '❌ Desativado'}"])
        embed.add_field(name="🎮 Plataformas Monitoradas", value=status, inline=False)
        streamers = dados["lives"]["streamers"].get(str(self.server_id), {})
        if streamers:
            lista_streamers = ""
            for uid, data in streamers.items():
                nome = data.get("nome", uid)
                plats_list = []
                for p in ["twitch", "youtube", "kick", "tiktok"]:
                    if data.get(p):
                        online = dados["lives"]["status"].get(str(self.server_id), {}).get(uid, {}).get(p, False)
                        emoji = "🟢" if online else "🔴"
                        plats_list.append(f"{emoji} {p.capitalize()}: {data[p]}")
                if plats_list:
                    lista_streamers += f"**<@{uid}>**\n" + "\n".join(plats_list) + "\n\n"
            if lista_streamers:
                embed.add_field(name="📋 Streamers Cadastrados", value=lista_streamers[:1024], inline=False)
        return embed

    @discord.ui.button(label="📝 Definir Canal", style=discord.ButtonStyle.secondary, emoji="📝")
    async def set_channel(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return
        modal = SetCanalModal(self.server_id, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="⚙️ Configuração", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def configuracao(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return
        await interaction.response.defer()
        view = ConfigStreamersView(self.server_id, self)
        embed = discord.Embed(title="⚙️ CONFIGURAÇÃO DE STREAMERS", description="Gerencie os streamers e plataformas.", color=0x7289da)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="➕ Adicionar Streamer", style=discord.ButtonStyle.success, emoji="➕", row=1)
    async def adicionar(self, interaction: discord.Interaction, button: Button):
        if not (is_admin(interaction.user) or is_membro(interaction.user)):
            await interaction.response.send_message("Você não tem permissão para adicionar streamer.", ephemeral=True)
            return
        await interaction.response.send_modal(AddStreamerByLinkModal(self.server_id, self))

    @discord.ui.button(label="🔄 Atualizar Painel", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def atualizar_painel(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return
        await interaction.response.defer()
        embed = await self.build_embed()
        await interaction.message.edit(embed=embed, view=self)

class SetCanalModal(Modal, title="Definir Canal e Cargo"):
    canal_id = TextInput(label="ID do canal de notícias", required=True)
    cargo_id = TextInput(label="ID do cargo para mencionar", required=True)
    def __init__(self, server_id, parent_view):
        super().__init__()
        self.server_id = server_id
        self.parent_view = parent_view
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            cid = int(self.canal_id.value.strip())
            rid = int(self.cargo_id.value.strip())
            config = dados["lives"]["config"].setdefault(str(self.server_id), {"platforms": {"twitch": True, "youtube": True, "kick": True, "tiktok": True}})
            config["channel"] = cid
            config["role"] = rid
            salvar_dados()
            embed = await self.parent_view.build_embed()
            await interaction.message.edit(embed=embed, view=self.parent_view)
            await interaction.followup.send("✅ Canal e cargo definidos! Painel atualizado.", ephemeral=True)
        except:
            await interaction.followup.send("IDs inválidos.", ephemeral=True)

class ConfigStreamersView(View):
    def __init__(self, server_id, parent_view):
        super().__init__(timeout=None)
        self.server_id = server_id
        self.parent_view = parent_view
    @discord.ui.button(label="➕ Adicionar Streamer", style=discord.ButtonStyle.success, emoji="➕")
    async def add(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AddStreamerByLinkModal(self.server_id, self.parent_view))
    @discord.ui.button(label="🗑️ Remover Streamer", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remove(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        streamers = dados["lives"]["streamers"].get(str(self.server_id), {})
        if not streamers:
            await interaction.followup.send("Nenhum streamer cadastrado.", ephemeral=True)
            return
        view = RemoveStreamerSelectView(self.server_id, self.parent_view)
        await interaction.followup.send("Selecione o streamer para remover:", view=view, ephemeral=True)
    @discord.ui.button(label="📺 Twitch", style=discord.ButtonStyle.secondary, emoji="📺", row=1)
    async def toggle_twitch(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        config = dados["lives"]["config"].setdefault(str(self.server_id), {"platforms": {"twitch": True}})
        config["platforms"]["twitch"] = not config["platforms"].get("twitch", True)
        salvar_dados()
        await interaction.followup.send(f"Twitch {'ativado' if config['platforms']['twitch'] else 'desativado'}.", ephemeral=True)
    @discord.ui.button(label="▶️ YouTube", style=discord.ButtonStyle.danger, emoji="▶️", row=1)
    async def toggle_youtube(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        config = dados["lives"]["config"].setdefault(str(self.server_id), {"platforms": {"youtube": True}})
        config["platforms"]["youtube"] = not config["platforms"].get("youtube", True)
        salvar_dados()
        await interaction.followup.send(f"YouTube {'ativado' if config['platforms']['youtube'] else 'desativado'}.", ephemeral=True)
    @discord.ui.button(label="🟢 Kick", style=discord.ButtonStyle.success, emoji="🟢", row=1)
    async def toggle_kick(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        config = dados["lives"]["config"].setdefault(str(self.server_id), {"platforms": {"kick": True}})
        config["platforms"]["kick"] = not config["platforms"].get("kick", True)
        salvar_dados()
        await interaction.followup.send(f"Kick {'ativado' if config['platforms']['kick'] else 'desativado'}.", ephemeral=True)
    @discord.ui.button(label="🎵 TikTok", style=discord.ButtonStyle.secondary, emoji="🎵", row=1)
    async def toggle_tiktok(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        config = dados["lives"]["config"].setdefault(str(self.server_id), {"platforms": {"tiktok": True}})
        config["platforms"]["tiktok"] = not config["platforms"].get("tiktok", True)
        salvar_dados()
        await interaction.followup.send(f"TikTok {'ativado' if config['platforms']['tiktok'] else 'desativado'}.", ephemeral=True)
    @discord.ui.button(label="↩️ Voltar", style=discord.ButtonStyle.secondary, emoji="↩️", row=2)
    async def voltar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        embed = await self.parent_view.build_embed()
        await interaction.followup.send(embed=embed, view=self.parent_view, ephemeral=True)

class RemoveStreamerSelectView(View):
    def __init__(self, server_id, parent_view):
        super().__init__(timeout=120)
        self.server_id = server_id
        self.parent_view = parent_view
        streamers = dados["lives"]["streamers"].get(str(server_id), {})
        options = []
        for uid, data in streamers.items():
            nome = data.get("nome", uid)
            plats = []
            for p in ["twitch", "youtube", "kick", "tiktok"]:
                if data.get(p):
                    plats.append(p.capitalize())
            desc = f"{nome} ({', '.join(plats)})" if plats else nome
            options.append(discord.SelectOption(label=desc[:100], value=uid))
        if options:
            self.add_item(StreamerRemoveDropdown(options, server_id, parent_view))

class StreamerRemoveDropdown(Select):
    def __init__(self, options, server_id, parent_view):
        super().__init__(placeholder="Escolha um streamer para remover...", options=options)
        self.server_id = server_id
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uid = self.values[0]
        if str(self.server_id) in dados["lives"]["streamers"] and uid in dados["lives"]["streamers"][str(self.server_id)]:
            nome = dados["lives"]["streamers"][str(self.server_id)][uid].get("nome", uid)
            del dados["lives"]["streamers"][str(self.server_id)][uid]
            salvar_dados()
            await interaction.followup.send(f"Streamer **{nome}** removido com sucesso!", ephemeral=True)
            try:
                embed = await self.parent_view.build_embed()
                await interaction.message.edit(embed=embed, view=self.parent_view)
            except:
                pass
        else:
            await interaction.followup.send("Streamer não encontrado.", ephemeral=True)

class AddStreamerByLinkModal(Modal, title="Adicionar Streamer"):
    plataforma = TextInput(label="PLATAFORMA (twitch/youtube/kick/tiktok)", placeholder="Ex: twitch", required=True)
    username = TextInput(label="USERNAME DO STREAMER", placeholder="Ex: alanzoka", required=True)
    discord_user = TextInput(label="DISCORD DO STREAMER (opcional)", placeholder="ID ou @ do usuário", required=False)
    observacao = TextInput(label="OBSERVAÇÃO (mensagem padrão)", placeholder="Aparecerá na notificação da live", required=False)
    def __init__(self, server_id, parent_view):
        super().__init__()
        self.server_id = server_id
        self.parent_view = parent_view
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        plat_input = self.plataforma.value.strip().lower()
        username_input = self.username.value.strip()
        obs = self.observacao.value.strip()
        extracted_plat, extracted_id = extract_platform_from_url(username_input)
        if extracted_plat and extracted_id:
            platform = extracted_plat
            identifier = extracted_id
            nome_streamer = identifier
        else:
            if plat_input not in ["twitch", "youtube", "kick", "tiktok"]:
                await interaction.followup.send("Plataforma inválida.", ephemeral=True)
                return
            platform = plat_input
            identifier = username_input
            nome_streamer = identifier
        uid = str(interaction.user.id)
        if self.discord_user.value.strip():
            try:
                uid_str = self.discord_user.value.strip().replace("<@!", "").replace("<@", "").replace(">", "")
                uid = str(int(uid_str))
                member = interaction.guild.get_member(int(uid))
                if member:
                    nome_streamer = member.display_name
            except:
                pass
        if is_membro(interaction.user) and not is_admin(interaction.user):
            if uid != str(interaction.user.id):
                await interaction.followup.send("Você só pode adicionar seu próprio canal.", ephemeral=True)
                return
        if str(self.server_id) not in dados["lives"]["streamers"]:
            dados["lives"]["streamers"][str(self.server_id)] = {}
        if uid not in dados["lives"]["streamers"][str(self.server_id)]:
            dados["lives"]["streamers"][str(self.server_id)][uid] = {"nome": nome_streamer, "twitch": None, "youtube": None, "kick": None, "tiktok": None, "observacao": ""}
        dados["lives"]["streamers"][str(self.server_id)][uid][platform] = identifier
        dados["lives"]["streamers"][str(self.server_id)][uid]["nome"] = nome_streamer
        if obs:
            dados["lives"]["streamers"][str(self.server_id)][uid]["observacao"] = obs
        salvar_dados()
        await interaction.followup.send(f"Streamer **{nome_streamer}** adicionado em **{platform}**!", ephemeral=True)
        try:
            embed = await self.parent_view.build_embed()
            await interaction.message.edit(embed=embed, view=self.parent_view)
        except:
            pass

# ========= SISTEMA DE COMPRA E VENDA =========
class VendaModal(Modal, title="💸 Venda de Munição"):
    tipo_municao = TextInput(label="Tipo de Munição (PISTOLA/SUB/RIFLE/FUZIL)", placeholder="Ex: PISTOLA", required=True)
    quantidade = TextInput(label="Quantidade", placeholder="Ex: 1000", required=True)
    valor_total = TextInput(label="Valor Total (R$)", placeholder="Ex: 500", required=True)
    faccao_compradora = TextInput(label="Facção Compradora", placeholder="Ex: Primeiro Comando", required=True)
    responsavel = TextInput(label="Responsável pela Venda", placeholder="Ex: @usuario ou nome", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Você não tem permissão para registrar vendas.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        tipo = self.tipo_municao.value.strip().upper()
        if tipo not in ["PISTOLA", "SUB", "RIFLE", "FUZIL"]:
            await interaction.followup.send("Tipo de munição inválido!", ephemeral=True)
            return
        try:
            qtd = int(self.quantidade.value)
            valor = float(self.valor_total.value.replace(",", "."))
        except:
            await interaction.followup.send("Quantidade ou valor inválidos!", ephemeral=True)
            return
        faccao = self.faccao_compradora.value.strip()
        responsavel_nome = self.responsavel.value.strip()
        await interaction.followup.send("📸 Agora envie a **print do comprovante da venda**.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel and m.attachments
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
            imagem_url = msg.attachments[0].url
            await msg.delete()
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return
        dados_log = {"Tipo": "VENDA", "Munição": tipo, "Quantidade": f"{qtd:,} unidades", "Valor Total": f"R$ {valor:,.2f}", "Facção Compradora": faccao, "Responsável": responsavel_nome, "Registrado por": interaction.user.mention}
        await log_compra_venda("venda", dados_log)
        dados["compras_vendas"].append({"tipo": "venda", "municao": tipo, "quantidade": qtd, "valor_total": valor, "faccao_compradora": faccao, "responsavel": responsavel_nome, "registrado_por": interaction.user.id, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "print_url": imagem_url})
        salvar_dados()
        await interaction.followup.send(f"✅ Venda de **{qtd:,} {tipo}** para **{faccao}** registrada! Valor: R$ {valor:,.2f}", ephemeral=True)
        await log_admin_embed("💸 VENDA REGISTRADA", f"Usuário: {interaction.user.mention}\nMunição: {qtd} {tipo}\nValor: R$ {valor:,.2f}\nFacção: {faccao}", 0x2c2f33)

class CompraModal(Modal, title="🛒 Compra de Produto"):
    quantidade = TextInput(label="Quantidade", placeholder="Ex: 1000", required=True)
    produto = TextInput(label="Produto", placeholder="Ex: Munição", required=True)
    valor_total = TextInput(label="Valor Total (R$)", placeholder="Ex: 500", required=True)
    faccao_vendedora = TextInput(label="Facção Vendedora", placeholder="Ex: Primeiro Comando", required=True)
    responsavel = TextInput(label="Responsável pela Compra", placeholder="Ex: @usuario ou nome", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Você não tem permissão para registrar compras.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            qtd = int(self.quantidade.value)
            valor = float(self.valor_total.value.replace(",", "."))
        except:
            await interaction.followup.send("Quantidade ou valor inválidos!", ephemeral=True)
            return
        await interaction.followup.send("📸 Agora envie a **print do comprovante da compra**.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel and m.attachments
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
            imagem_url = msg.attachments[0].url
            await msg.delete()
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return
        await log_compra_venda("compra", {"Tipo": "COMPRA", "Quantidade": f"{qtd:,}", "Produto": self.produto.value, "Valor Total": f"R$ {valor:,.2f}", "Facção Vendedora": self.faccao_vendedora.value, "Responsável": self.responsavel.value, "Registrado por": interaction.user.mention})
        dados["compras_vendas"].append({"tipo": "compra", "quantidade": qtd, "produto": self.produto.value, "valor_total": valor, "faccao_vendedora": self.faccao_vendedora.value, "responsavel": self.responsavel.value, "registrado_por": interaction.user.id, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "print_url": imagem_url})
        salvar_dados()
        await interaction.followup.send("✅ Compra registrada!", ephemeral=True)
        await log_admin_embed("🛒 COMPRA REGISTRADA", f"Usuário: {interaction.user.mention}\nProduto: {qtd} x {self.produto.value}\nValor: R$ {valor:,.2f}\nFacção: {self.faccao_vendedora.value}", 0x2c2f33)

class CompraVendaView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="💸 Venda de Munição", style=discord.ButtonStyle.secondary, emoji="💸")
    async def venda(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(VendaModal())
    @discord.ui.button(label="🛒 Compra de Produto", style=discord.ButtonStyle.secondary, emoji="🛒")
    async def compra(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CompraModal())

# ========= RESTAURAÇÃO DE CANAIS DE FARM =========
async def restaurar_canais_farms():
    for user_id_str, canal_id in dados["canais"].items():
        canal = bot.get_channel(canal_id)
        if canal:
            async for msg in canal.history(limit=10):
                if msg.author == bot.user and msg.components:
                    break
            else:
                guild = canal.guild
                member = guild.get_member(int(user_id_str)) if guild else None
                if member:
                    view = FarmChannelView(member.id, member.display_name, canal.id)
                    embed = discord.Embed(
                        title="📦 SEU CANAL PRIVADO",
                        description=f"Bem-vindo(a) {member.mention}!\n\n🔒 Apenas você e administradores têm acesso.\n\n**BOTÕES:**\n📦 Depositar Farm\n💰 Registrar Dinheiro Sujo (Admin)\n✏️ Editar Registro\n📋 Meus Registros\n📊 Fechar Caixa\n🔄 Reset Semanal",
                        color=0x2c2f33
                    )
                    await canal.send(embed=embed, view=view)

# ========= MODAL DE FARM PRODUTOS (5 CAMPOS) =========
class FarmProdutosModal(Modal, title="📦 Depositar Farm"):
    slot = TextInput(label="SLOT (número)", placeholder="Ex: 1, 2, 3...", required=True)
    relogio = TextInput(label="RELÓGIO DE LUXO - Quantidade", placeholder="Ex: 5", required=False)
    obra = TextInput(label="OBRA DE ARTE - Quantidade", placeholder="Ex: 2", required=False)
    bebida = TextInput(label="BEBIDA IMPORTADA - Quantidade", placeholder="Ex: 10", required=False)
    acoes = TextInput(label="AÇÕES DE EMPRESA - Quantidade", placeholder="Ex: 100", required=False)

    def __init__(self, user_id, user_name, canal, edit_mode=False, farm_index=None):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.edit_mode = edit_mode
        self.farm_index = farm_index

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        slot_num = self.slot.value.strip()
        if not slot_num.isdigit():
            await interaction.followup.send("Slot deve ser um número!", ephemeral=True)
            return
        produtos = []
        for campo, nome in [(self.relogio, "RELÓGIO DE LUXO"), (self.obra, "OBRA DE ARTE"), (self.bebida, "BEBIDA IMPORTADA"), (self.acoes, "AÇÕES DE EMPRESA")]:
            if campo.value and campo.value.strip():
                try:
                    qtd = int(campo.value.strip())
                    if qtd > 0:
                        produtos.append({"produto": nome, "quantidade": qtd})
                except ValueError:
                    pass
        if not produtos:
            await interaction.followup.send("Nenhum produto válido!", ephemeral=True)
            return

        await interaction.followup.send("📸 Agora envie a **print da farm** aqui no canal.", ephemeral=True)
        def check_print(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments
        try:
            msg_print = await bot.wait_for('message', timeout=60.0, check=check_print)
            imagem_url = msg_print.attachments[0].url
            await msg_print.delete()
        except asyncio.TimeoutError:
            await self.canal.send("⏰ Tempo esgotado! Registro cancelado.", delete_after=10)
            return

        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": []}

        if self.edit_mode and self.farm_index is not None:
            if self.farm_index >= len(dados["usuarios"][str(self.user_id)]["farms"]):
                await interaction.followup.send("Registro não encontrado.", ephemeral=True)
                return
            dados["usuarios"][str(self.user_id)]["farms"][self.farm_index] = {
                "produtos": produtos,
                "slot": int(slot_num),
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "print_url": imagem_url,
                "validado": True,
                "farm_id": dados["usuarios"][str(self.user_id)]["farms"][self.farm_index].get("farm_id", self.farm_index + 1)
            }
            salvar_dados()
            embed = discord.Embed(title="✏️ FARM PRODUTOS EDITADA", description=f"**Usuário:** <@{self.user_id}>\n**Slot:** {slot_num}\n", color=0x99aab5)
            desc = "".join(f"🔹 **{p['produto']}:** {p['quantidade']} itens\n" for p in produtos)
            embed.description += desc
            embed.add_field(name="📅 Data da edição", value=datetime.now().strftime("%d/%m/%Y às %H:%M"), inline=False)
            embed.set_image(url=imagem_url)
            await self.canal.send(embed=embed)
            await log_embed("✏️ FARM PRODUTOS EDITADA", f"Usuário: <@{self.user_id}>\nSlot: {slot_num}\nProdutos: {desc}", 0x99aab5, thumbnail=interaction.user.display_avatar.url)
            await log_admin_embed("✏️ FARM PRODUTOS EDITADA", f"Usuário: {interaction.user.mention}\nProdutos: {desc}\nSlot: {slot_num}", 0x99aab5)
            await interaction.followup.send("Farm editada com sucesso!", ephemeral=True)
        else:
            registro = {
                "produtos": produtos,
                "slot": int(slot_num),
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "print_url": imagem_url,
                "validado": True,
                "farm_id": len(dados["usuarios"][str(self.user_id)]["farms"]) + 1
            }
            dados["usuarios"][str(self.user_id)]["farms"].append(registro)
            salvar_dados()
            embed = discord.Embed(title="✅ FARM PRODUTOS REGISTRADA", description=f"**Usuário:** <@{self.user_id}>\n**Slot:** {slot_num}\n", color=0x2c2f33)
            desc = "".join(f"🔹 **{p['produto']}:** {p['quantidade']} itens\n" for p in produtos)
            embed.description += desc
            embed.add_field(name="📅 Data", value=datetime.now().strftime("%d/%m/%Y às %H:%M"), inline=False)
            embed.add_field(name="📦 Total de farms", value=f"{len(dados['usuarios'][str(self.user_id)]['farms'])} farms", inline=False)
            embed.set_image(url=imagem_url)
            embed.set_footer(text=f"Farm ID: {registro['farm_id']}")
            await self.canal.send(embed=embed)
            await log_embed("📦 FARM PRODUTOS REGISTRADA", f"Usuário: <@{self.user_id}>\nSlot: {slot_num}\nProdutos: {desc}", 0x2c2f33, thumbnail=interaction.user.display_avatar.url)
            await log_admin_embed("📦 NOVA FARM PRODUTOS", f"Usuário: {interaction.user.mention}\nProdutos: {desc}\nSlot: {slot_num}", 0x2c2f33)
            await interaction.followup.send("Farm registrada com sucesso!", ephemeral=True)
        await atualizar_ranking()

# ========= MODAL ADMIN DINHEIRO SUJO =========
class DinheiroSujoAdminModal(Modal, title="💰 Registrar Dinheiro Sujo (Admin)"):
    valor = TextInput(label="Valor (R$)", placeholder="Ex: 5000", required=True)

    def __init__(self, user_id, user_name, canal):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal

    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Você não tem permissão para registrar dinheiro sujo.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            valor = float(self.valor.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Valor inválido!", ephemeral=True)
            return

        await interaction.followup.send("📸 Agora envie a **print do comprovante** aqui no canal.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
            imagem_url = msg.attachments[0].url
            await msg.delete()
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return

        view = SelecionarMembroView(self.user_id, self.user_name, self.canal, valor, imagem_url, interaction.user)
        await interaction.followup.send("Selecione o membro que recebeu o dinheiro:", view=view, ephemeral=True)

class SelecionarMembroView(View):
    def __init__(self, target_user_id, target_user_name, canal, valor, imagem_url, admin_user):
        super().__init__(timeout=120)
        self.target_user_id = target_user_id
        self.target_user_name = target_user_name
        self.canal = canal
        self.valor = valor
        self.imagem_url = imagem_url
        self.admin_user = admin_user
        select = UserSelect(placeholder="Escolha o membro que recebeu o dinheiro", min_values=1, max_values=1)
        select.callback = self.membro_selecionado
        self.add_item(select)

    async def membro_selecionado(self, interaction: discord.Interaction):
        if interaction.user.id != self.admin_user.id:
            await interaction.response.send_message("Apenas o admin que iniciou pode selecionar.", ephemeral=True)
            return
        membro_id = int(interaction.data["values"][0])
        membro_obj = interaction.guild.get_member(membro_id)
        if not membro_obj:
            await interaction.response.send_message("Membro não encontrado.", ephemeral=True)
            return

        if str(self.target_user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.target_user_id)] = {"farms": [], "pagamentos": [], "nome": self.target_user_name, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": []}
        if "transacoes_dinheiro_sujo" not in dados["usuarios"][str(self.target_user_id)]:
            dados["usuarios"][str(self.target_user_id)]["transacoes_dinheiro_sujo"] = []

        transacao = {
            "valor": self.valor,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "print_url": self.imagem_url,
            "registrado_por": interaction.user.id,
            "membro_recebedor": membro_id,
            "membro_nome": membro_obj.name
        }
        dados["usuarios"][str(self.target_user_id)]["transacoes_dinheiro_sujo"].append(transacao)
        dados["usuarios"][str(self.target_user_id)]["dinheiro_sujo"] = sum(t["valor"] for t in dados["usuarios"][str(self.target_user_id)]["transacoes_dinheiro_sujo"])
        salvar_dados()

        embed = discord.Embed(title="💰 DINHEIRO SUJO REGISTRADO", description=f"**Usuário:** <@{self.target_user_id}>\n**Valor:** R$ {self.valor:,.2f}\n**Membro que recebeu:** {membro_obj.mention}\n**Registrado por:** {interaction.user.mention}", color=0x4f545c, timestamp=datetime.now())
        embed.set_image(url=self.imagem_url)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/196/196566.png")
        await self.canal.send(embed=embed)
        await log_embed("💰 DINHEIRO SUJO REGISTRADO", f"Usuário: <@{self.target_user_id}>\nValor: R$ {self.valor:,.2f}\nMembro que recebeu: {membro_obj.mention}", 0x4f545c, thumbnail="https://cdn-icons-png.flaticon.com/512/196/196566.png")
        await log_admin_embed("💰 DINHEIRO SUJO REGISTRADO", f"Usuário: {self.target_user_name}\nValor: R$ {self.valor:,.2f}\nMembro: {membro_obj.name}", 0x4f545c)
        await interaction.response.send_message(f"R$ {self.valor:,.2f} registrado como dinheiro sujo para {self.target_user_name}!", ephemeral=True)
        await atualizar_ranking()
        self.stop()

# ========= VIEW DO CANAL PRIVADO =========
class FarmChannelView(View):
    def __init__(self, user_id, user_name, canal_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.user_name = user_name
        self.canal_id = canal_id
        self._add_buttons()

    def _add_buttons(self):
        farm_btn = Button(label="Depositar Farm", style=discord.ButtonStyle.secondary, emoji="📦", row=0, custom_id="farm_produtos")
        farm_btn.callback = self.farm_produtos_callback
        self.add_item(farm_btn)

        dinheiro_btn = Button(label="Registrar Dinheiro Sujo (Admin)", style=discord.ButtonStyle.danger, emoji="💰", row=0, custom_id="dinheiro_sujo_admin")
        dinheiro_btn.callback = self.dinheiro_sujo_admin_callback
        self.add_item(dinheiro_btn)

        editar_btn = Button(label="Editar Registro", style=discord.ButtonStyle.secondary, emoji="✏️", row=0, custom_id="editar_registro")
        editar_btn.callback = self.editar_registro_callback
        self.add_item(editar_btn)

        fechar_caixa_btn = Button(label="Fechar Caixa", style=discord.ButtonStyle.secondary, emoji="📊", row=1, custom_id="fechar_caixa")
        fechar_caixa_btn.callback = self.fechar_caixa_callback
        self.add_item(fechar_caixa_btn)

        meus_registros_btn = Button(label="Meus Registros", style=discord.ButtonStyle.primary, emoji="📋", row=2, custom_id="meus_registros")
        meus_registros_btn.callback = self.meus_registros_callback
        self.add_item(meus_registros_btn)

        reset_btn = Button(label="Reset Semanal", style=discord.ButtonStyle.danger, emoji="🔄", row=2, custom_id="reset_semanal")
        reset_btn.callback = self.reset_semanal_callback
        self.add_item(reset_btn)

    async def farm_produtos_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("Apenas o dono do canal ou administradores podem depositar farm!", ephemeral=True)
            return
        await interaction.response.send_modal(FarmProdutosModal(self.user_id, self.user_name, interaction.channel))

    async def dinheiro_sujo_admin_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem registrar dinheiro sujo.", ephemeral=True)
            return
        await interaction.response.send_modal(DinheiroSujoAdminModal(self.user_id, self.user_name, interaction.channel))

    async def editar_registro_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores.", ephemeral=True)
            return
        user_data = dados["usuarios"].get(str(self.user_id), {})
        farms = user_data.get("farms", [])
        if not farms:
            await interaction.response.send_message("Este usuário não possui registros para editar.", ephemeral=True)
            return
        options = []
        for idx, farm in enumerate(farms):
            farm_id = farm.get("farm_id", idx + 1)
            slot = farm.get("slot", "?")
            produtos_str = ", ".join(f"{p['produto']}: {p['quantidade']}" for p in farm["produtos"])
            label = f"Farm #{farm_id} (Slot {slot})"
            desc = produtos_str[:100]
            options.append(discord.SelectOption(label=label, description=desc, value=str(idx)))
        select = Select(placeholder="Escolha a farm para editar", options=options)
        view = View(timeout=60)
        view.add_item(select)
        async def select_callback(interaction_select):
            idx = int(interaction_select.data["values"][0])
            farm = farms[idx]
            modal = FarmProdutosModal(self.user_id, self.user_name, interaction.channel, edit_mode=True, farm_index=idx)
            modal.slot.default = str(farm.get("slot", ""))
            produtos_dict = {p["produto"]: p["quantidade"] for p in farm["produtos"]}
            modal.relogio.default = str(produtos_dict.get("RELÓGIO DE LUXO", ""))
            modal.obra.default = str(produtos_dict.get("OBRA DE ARTE", ""))
            modal.bebida.default = str(produtos_dict.get("BEBIDA IMPORTADA", ""))
            modal.acoes.default = str(produtos_dict.get("AÇÕES DE EMPRESA", ""))
            await interaction_select.response.send_modal(modal)
        select.callback = select_callback
        await interaction.response.send_message("Selecione a farm que deseja editar:", view=view, ephemeral=True)

    async def fechar_caixa_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores.", ephemeral=True)
            return
        await interaction.response.send_message("Função em desenvolvimento. Em breve!", ephemeral=True)

    async def meus_registros_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores.", ephemeral=True)
            return
        user_data = dados["usuarios"].get(str(self.user_id), {})
        farms = user_data.get("farms", [])
        if not farms:
            await interaction.response.send_message("Este usuário ainda não tem registros de farm.", ephemeral=True)
            return
        embed = discord.Embed(title=f"📋 REGISTROS DE {self.user_name}", color=0x2c2f33)
        for farm in farms[-10:]:
            produtos_str = ", ".join(f"{p['produto']}: {p['quantidade']}" for p in farm["produtos"])
            embed.add_field(name=f"Farm #{farm.get('farm_id','?')} - Slot {farm.get('slot','?')}", value=f"**Produtos:** {produtos_str}\n**Data:** {farm['data']}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def reset_semanal_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores.", ephemeral=True)
            return
        confirm_view = ConfirmResetSemanalView(self.user_id, self.user_name, interaction.channel)
        await interaction.response.send_message("⚠️ **Tem certeza que deseja resetar a semana?** Isso apagará todos os registros de farm, pagamentos e dinheiro sujo deste usuário.", view=confirm_view, ephemeral=True)

class ConfirmResetSemanalView(View):
    def __init__(self, user_id, user_name, canal):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
    @discord.ui.button(label="Sim, resetar semana", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        if str(self.user_id) in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)]["farms"] = []
            dados["usuarios"][str(self.user_id)]["pagamentos"] = []
            dados["usuarios"][str(self.user_id)]["dinheiro_sujo"] = 0.0
            dados["usuarios"][str(self.user_id)]["transacoes_dinheiro_sujo"] = []
            salvar_dados()
        await interaction.followup.send("✅ Semana resetada com sucesso!", ephemeral=True)
        embed = discord.Embed(title="🔄 RESET SEMANAL", description=f"Os registros de {self.user_name} foram resetados por {interaction.user.mention}.", color=0x4f545c)
        await self.canal.send(embed=embed)
        await log_admin_embed("🔄 RESET SEMANAL", f"Usuário: {self.user_name}\nAdmin: {interaction.user.mention}", 0x4f545c)
        await atualizar_ranking()
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Reset cancelado.", ephemeral=True)

# ========= BOTÃO CRIAR CANAL =========
class BotaoCriarCanalView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Criar Meu Canal Privado", style=discord.ButtonStyle.success, emoji="📦")
    async def criar_canal(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if interaction.guild is None:
            await interaction.followup.send("Use em um servidor!", ephemeral=True)
            return
        if not interaction.guild.me.guild_permissions.manage_channels:
            await interaction.followup.send("Bot precisa de permissão de Administrador.", ephemeral=True)
            return
        user_id = str(interaction.user.id)
        if user_id in dados["canais"]:
            canal = interaction.guild.get_channel(dados["canais"][user_id])
            if canal:
                await interaction.followup.send(f"Você já possui um canal! Acesse: {canal.mention}", ephemeral=True)
                return
            else:
                del dados["canais"][user_id]
                salvar_dados()
        try:
            categoria = interaction.guild.get_channel(CATEGORIA_FARMS_ID)
            if not categoria:
                await interaction.followup.send("Categoria não encontrada!", ephemeral=True)
                return
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
            canal = await categoria.create_text_channel(nome_canal, overwrites=overwrites)
            dados["canais"][user_id] = canal.id
            salvar_dados()
            view = FarmChannelView(interaction.user.id, interaction.user.name, canal.id)
            embed = discord.Embed(
                title="📦 SEU CANAL PRIVADO",
                description=f"Bem-vindo(a) {interaction.user.mention}!\n\n🔒 Apenas você e administradores têm acesso.\n\n**BOTÕES:**\n📦 Depositar Farm\n💰 Registrar Dinheiro Sujo (Admin)\n✏️ Editar Registro\n📋 Meus Registros\n📊 Fechar Caixa\n🔄 Reset Semanal",
                color=0x2c2f33
            )
            await canal.send(embed=embed, view=view)
            await log_embed("📦 CANAL CRIADO", f"{interaction.user.mention} criou seu canal privado: {canal.mention}", 0x2c2f33, thumbnail=interaction.user.display_avatar.url)
            await log_admin_embed("📦 CANAL CRIADO", f"Usuário: {interaction.user.mention}\nCanal: {canal.mention}", 0x2c2f33)
            await interaction.followup.send(f"✅ Canal criado! Acesse: {canal.mention}", ephemeral=True)
            await atualizar_ranking()
        except Exception as e:
            await interaction.followup.send(f"Erro: {str(e)[:200]}", ephemeral=True)

# ========= SISTEMA DE RESERVAS (CLIENTES) =========
class ReservaView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Nova reserva", style=discord.ButtonStyle.success, emoji="💸")
    async def nova_reserva(self, interaction: discord.Interaction, button: Button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Apenas cargos 00,01,02 ou Gerente podem criar reservas.", ephemeral=True)
            return
        await interaction.response.send_modal(NovaReservaModal())
    @discord.ui.button(label="Editar Porcentagens", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def editar_porcentagens(self, interaction: discord.Interaction, button: Button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Apenas cargos 00,01,02 ou Gerente podem editar porcentagens.", ephemeral=True)
            return
        await interaction.response.send_modal(EditarPorcentagensModal())

class NovaReservaModal(Modal, title="💸 Nova Reserva"):
    cliente = TextInput(label="Nome do Cliente", required=True)
    valor_total = TextInput(label="Valor Total Sujo (R$)", required=True)
    prazo_entrega = TextInput(label="Prazo de Entrega", required=True)
    descontado_caixa = TextInput(label="Descontado do Caixa? (Sim/Não/Pendente)", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            valor = float(self.valor_total.value.replace(",", "."))
        except:
            await interaction.followup.send("Valor inválido!", ephemeral=True)
            return
        descontado = self.descontado_caixa.value.strip().capitalize()
        if descontado not in ["Sim", "Não", "Pendente"]:
            await interaction.followup.send("Descontado deve ser Sim, Não ou Pendente.", ephemeral=True)
            return
        pcts = dados["pedidos"]["config"]["porcentagens"]
        vip = pcts.get("vip_fac", 0)
        fac_percent = pcts["fac"] + vip
        cliente_part = valor * pcts["cliente"] / 100
        maquina_part = valor * pcts["maquina"] / 100
        fac_part = valor * fac_percent / 100
        membros_part = valor * pcts["membros"] / 100
        reserva = {
            "id": len(dados["pedidos"]["lista"]) + 1,
            "cliente": self.cliente.value.strip(),
            "valor_total": valor,
            "prazo_entrega": self.prazo_entrega.value.strip(),
            "descontado_caixa": descontado,
            "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "criado_por": interaction.user.id,
            "distribuicao": {"cliente": cliente_part, "maquina": maquina_part, "fac": fac_part, "membros": membros_part, "vip_fac": vip},
            "pago": False
        }
        dados["pedidos"]["lista"].append(reserva)
        salvar_dados()
        embed = discord.Embed(title="💸 NOVA RESERVA CRIADA", color=0x2c2f33, timestamp=datetime.now())
        embed.add_field(name="Cliente", value=reserva["cliente"], inline=True)
        embed.add_field(name="Valor Total", value=f"R$ {valor:,.2f}", inline=True)
        embed.add_field(name="Prazo", value=reserva["prazo_entrega"], inline=True)
        embed.add_field(name="Descontado", value=descontado, inline=True)
        distrib = f"Cliente: R$ {cliente_part:,.2f} ({pcts['cliente']}%)\nMáquina: R$ {maquina_part:,.2f} ({pcts['maquina']}%)\nFacção: R$ {fac_part:,.2f} ({fac_percent}% incluindo VIP {vip}%)\nMembros: R$ {membros_part:,.2f} ({pcts['membros']}%)"
        embed.add_field(name="Distribuição", value=distrib, inline=False)
        embed.set_footer(text=f"Reserva #{reserva['id']} - Criado por {interaction.user.name}")
        await interaction.followup.send(embed=embed, ephemeral=True)
        await log_pedido_embed(
            "💸 NOVA RESERVA",
            f"Reserva #{reserva['id']} criada por {interaction.user.mention}",
            0x2c2f33,
            fields=[
                ("Cliente", reserva["cliente"], True),
                ("Valor Total", f"R$ {valor:,.2f}", True),
                ("Prazo", reserva["prazo_entrega"], True),
                ("Descontado", descontado, True),
                ("Distribuição", f"Cliente: R$ {cliente_part:,.2f} ({pcts['cliente']}%)\nMáquina: R$ {maquina_part:,.2f} ({pcts['maquina']}%)\nFacção: R$ {fac_part:,.2f} ({fac_percent}% incluindo VIP {vip}%)\nMembros: R$ {membros_part:,.2f} ({pcts['membros']}%)", False)
            ]
        )
        await log_admin_embed("💸 NOVA RESERVA", f"Reserva #{reserva['id']} criada por {interaction.user.mention}", 0x2c2f33)

class EditarPorcentagensModal(Modal, title="⚙️ Editar Porcentagens e VIP"):
    cliente = TextInput(label="% Cliente", default="50", required=True)
    maquina = TextInput(label="% Máquina", default="40", required=True)
    fac = TextInput(label="% Facção", default="5", required=True)
    membros = TextInput(label="% Membros", default="5", required=True)
    vip_fac = TextInput(label="% VIP Fac (bônus)", default="10", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return
        try:
            pcts = {
                "cliente": float(self.cliente.value.replace(",", ".")),
                "maquina": float(self.maquina.value.replace(",", ".")),
                "fac": float(self.fac.value.replace(",", ".")),
                "membros": float(self.membros.value.replace(",", ".")),
                "vip_fac": float(self.vip_fac.value.replace(",", "."))
            }
            dados["pedidos"]["config"]["porcentagens"] = pcts
            dados["pedidos"]["config"]["ultima_edicao"] = {"por": interaction.user.id, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            salvar_dados()
            total = pcts["cliente"] + pcts["maquina"] + pcts["fac"] + pcts["membros"] + pcts["vip_fac"]
            await interaction.response.send_message(f"✅ Porcentagens atualizadas!\nCliente {pcts['cliente']}% | Máquina {pcts['maquina']}% | Facção {pcts['fac']}% | Membros {pcts['membros']}% | VIP Fac {pcts['vip_fac']}% (total {total}%)", ephemeral=True)
            await log_pedido_embed(
                "⚙️ PORCENTAGENS EDITADAS",
                f"Porcentagens editadas por {interaction.user.mention}",
                0x2c2f33,
                fields=[
                    ("Cliente", f"{pcts['cliente']}%", True),
                    ("Máquina", f"{pcts['maquina']}%", True),
                    ("Facção", f"{pcts['fac']}%", True),
                    ("Membros", f"{pcts['membros']}%", True),
                    ("VIP Fac", f"{pcts['vip_fac']}%", True),
                    ("Total", f"{total}%", True)
                ]
            )
            await log_admin_embed("⚙️ PORCENTAGENS EDITADAS", f"Novas porcentagens: Cliente {pcts['cliente']}%, Máquina {pcts['maquina']}%, Facção {pcts['fac']}%, Membros {pcts['membros']}%, VIP Fac {pcts['vip_fac']}%", 0x2c2f33)
        except ValueError:
            await interaction.response.send_message("Valores inválidos. Use números.", ephemeral=True)

# ========= SISTEMA DE RESERVAS FUNCIONÁRIOS =========
class ReservaFuncView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Nova reserva (Func)", style=discord.ButtonStyle.success, emoji="💸")
    async def nova_reserva_func(self, interaction: discord.Interaction, button: Button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Apenas cargos 00,01,02 ou Gerente podem criar reservas de funcionários.", ephemeral=True)
            return
        await interaction.response.send_modal(NovaReservaFuncModal())
    @discord.ui.button(label="Editar Porcentagens (Func)", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def editar_porcentagens_func(self, interaction: discord.Interaction, button: Button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Apenas cargos 00,01,02 ou Gerente podem editar porcentagens.", ephemeral=True)
            return
        await interaction.response.send_modal(EditarPorcentagensFuncModal())

class NovaReservaFuncModal(Modal, title="💸 Nova Reserva (Funcionário)"):
    funcionario = TextInput(label="Nome do Funcionário", required=True)
    valor_total = TextInput(label="Valor Total Sujo (R$)", required=True)
    prazo_entrega = TextInput(label="Prazo de Entrega", required=True)
    descontado_caixa = TextInput(label="Descontado do Caixa? (Sim/Não/Pendente)", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            valor = float(self.valor_total.value.replace(",", "."))
        except:
            await interaction.followup.send("Valor inválido!", ephemeral=True)
            return
        descontado = self.descontado_caixa.value.strip().capitalize()
        if descontado not in ["Sim", "Não", "Pendente"]:
            await interaction.followup.send("Descontado deve ser Sim, Não ou Pendente.", ephemeral=True)
            return
        pcts = dados["pedidos_funcionarios"]["config"]["porcentagens"]
        vip = pcts.get("vip_fac", 0)
        fac_percent = pcts["fac"] + vip
        func_part = valor * pcts["funcionario"] / 100
        maquina_part = valor * pcts["maquina"] / 100
        fac_part = valor * fac_percent / 100
        reserva = {
            "id": len(dados["pedidos_funcionarios"]["lista"]) + 1,
            "funcionario": self.funcionario.value.strip(),
            "valor_total": valor,
            "prazo_entrega": self.prazo_entrega.value.strip(),
            "descontado_caixa": descontado,
            "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "criado_por": interaction.user.id,
            "distribuicao": {"funcionario": func_part, "maquina": maquina_part, "fac": fac_part, "vip_fac": vip},
            "pago": False
        }
        dados["pedidos_funcionarios"]["lista"].append(reserva)
        salvar_dados()
        embed = discord.Embed(title="💸 NOVA RESERVA (FUNCIONÁRIO)", color=0x2c2f33, timestamp=datetime.now())
        embed.add_field(name="Funcionário", value=reserva["funcionario"], inline=True)
        embed.add_field(name="Valor Total", value=f"R$ {valor:,.2f}", inline=True)
        embed.add_field(name="Prazo", value=reserva["prazo_entrega"], inline=True)
        embed.add_field(name="Descontado", value=descontado, inline=True)
        distrib = f"Funcionário: R$ {func_part:,.2f} ({pcts['funcionario']}%)\nMáquina: R$ {maquina_part:,.2f} ({pcts['maquina']}%)\nFacção: R$ {fac_part:,.2f} ({fac_percent}% incluindo VIP {vip}%)"
        embed.add_field(name="Distribuição", value=distrib, inline=False)
        embed.set_footer(text=f"Reserva #{reserva['id']} - Criado por {interaction.user.name}")
        await interaction.followup.send(embed=embed, ephemeral=True)
        await log_reserva_func_embed(
            "💸 NOVA RESERVA (FUNCIONÁRIO)",
            f"Reserva #{reserva['id']} criada por {interaction.user.mention}",
            0x2c2f33,
            fields=[
                ("Funcionário", reserva["funcionario"], True),
                ("Valor Total", f"R$ {valor:,.2f}", True),
                ("Prazo", reserva["prazo_entrega"], True),
                ("Descontado", descontado, True),
                ("Distribuição", f"Funcionário: R$ {func_part:,.2f} ({pcts['funcionario']}%)\nMáquina: R$ {maquina_part:,.2f} ({pcts['maquina']}%)\nFacção: R$ {fac_part:,.2f} ({fac_percent}% incluindo VIP {vip}%)", False)
            ]
        )
        await log_admin_embed("💸 NOVA RESERVA (FUNCIONÁRIO)", f"Reserva #{reserva['id']} criada por {interaction.user.mention}", 0x2c2f33)

class EditarPorcentagensFuncModal(Modal, title="⚙️ Editar Porcentagens (Funcionários)"):
    funcionario = TextInput(label="% Funcionário", default="50", required=True)
    maquina = TextInput(label="% Máquina", default="40", required=True)
    fac = TextInput(label="% Facção", default="5", required=True)
    vip_fac = TextInput(label="% VIP Fac (bônus)", default="10", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return
        try:
            pcts = {
                "funcionario": float(self.funcionario.value.replace(",", ".")),
                "maquina": float(self.maquina.value.replace(",", ".")),
                "fac": float(self.fac.value.replace(",", ".")),
                "vip_fac": float(self.vip_fac.value.replace(",", "."))
            }
            dados["pedidos_funcionarios"]["config"]["porcentagens"] = pcts
            dados["pedidos_funcionarios"]["config"]["ultima_edicao"] = {"por": interaction.user.id, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            salvar_dados()
            total = pcts["funcionario"] + pcts["maquina"] + pcts["fac"] + pcts["vip_fac"]
            await interaction.response.send_message(f"✅ Porcentagens (Funcionários) atualizadas!\nFuncionário {pcts['funcionario']}% | Máquina {pcts['maquina']}% | Facção {pcts['fac']}% | VIP Fac {pcts['vip_fac']}% (total {total}%)", ephemeral=True)
            await log_reserva_func_embed(
                "⚙️ PORCENTAGENS EDITADAS (FUNCIONÁRIOS)",
                f"Porcentagens editadas por {interaction.user.mention}",
                0x2c2f33,
                fields=[
                    ("Funcionário", f"{pcts['funcionario']}%", True),
                    ("Máquina", f"{pcts['maquina']}%", True),
                    ("Facção", f"{pcts['fac']}%", True),
                    ("VIP Fac", f"{pcts['vip_fac']}%", True),
                    ("Total", f"{total}%", True)
                ]
            )
            await log_admin_embed("⚙️ PORCENTAGENS EDITADAS (FUNCIONÁRIOS)", f"Novas porcentagens: Funcionário {pcts['funcionario']}%, Máquina {pcts['maquina']}%, Facção {pcts['fac']}%, VIP Fac {pcts['vip_fac']}%", 0x2c2f33)
        except ValueError:
            await interaction.response.send_message("Valores inválidos. Use números.", ephemeral=True)

# ========= REMOÇÃO DE MEMBRO =========
class RemoverUsuarioModal(Modal, title="🗑️ Remover Usuário"):
    user_id = TextInput(label="ID do usuário", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not pode_remover_membro(interaction.user):
            await interaction.response.send_message("Você não tem permissão para remover membros.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            uid = int(self.user_id.value.strip())
            user = await bot.fetch_user(uid)
            if str(uid) in dados["usuarios_banidos"]:
                await interaction.followup.send("Usuário já removido!", ephemeral=True)
                return
            total = await limpar_logs_usuario(uid, user.name)
            await interaction.followup.send(f"✅ {user.mention} removido! {total} logs limpos.", ephemeral=True)
            await log_admin_embed("🗑️ USUÁRIO REMOVIDO", f"{user.mention} removido por {interaction.user.mention}\nLogs limpos: {total}", 0x4f545c)
            await atualizar_ranking()
        except Exception as e:
            await interaction.followup.send(f"Erro: {e}", ephemeral=True)

# ========= EVENTOS =========
@bot.event
async def on_member_remove(member):
    if str(member.id) in dados["usuarios_banidos"]:
        return
    await log_admin_embed("👋 USUÁRIO SAIU", f"{member.mention} saiu do servidor. Iniciando limpeza...", 0x4f545c)
    await limpar_logs_usuario(member.id, member.name)
    if str(member.id) in dados["canais"]:
        canal = member.guild.get_channel(dados["canais"][str(member.id)])
        if canal:
            try:
                await canal.delete(reason=f"Usuário {member.name} saiu")
            except:
                pass
        del dados["canais"][str(member.id)]
        salvar_dados()
    await log_admin_embed("🧹 LIMPEZA CONCLUÍDA", f"Usuário {member.mention} removido do sistema.", 0x4f545c)

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} online!")
    live_check_loop.start()

    for guild in bot.guilds:
        # Painel criar canal
        canal_criar = guild.get_channel(CANAL_CRIAR_FARM_ID)
        if canal_criar:
            async for msg in canal_criar.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            embed_criar = discord.Embed(
                title="📦 SISTEMA DE FARM",
                description="Clique no botão abaixo para criar seu canal privado!",
                color=0x2c2f33
            )
            await canal_criar.send(embed=embed_criar, view=BotaoCriarCanalView())

        # Painel de Registro
        canal_set = guild.get_channel(CANAL_SOLICITAR_SET_ID)
        if canal_set:
            async for msg in canal_set.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            embed_set = discord.Embed(
                title="📋 REGISTRO",
                description="Clique no botão abaixo para fazer seu registro. Preencha seu ID e nome no jogo.",
                color=0x2c2f33
            )
            view = View(timeout=None)
            button = Button(label="📝 Registro", style=discord.ButtonStyle.success, emoji="📝")
            async def button_callback(interaction):
                await interaction.response.send_modal(SolicitarSetModal())
            button.callback = button_callback
            view.add_item(button)
            await canal_set.send(embed=embed_set, view=view)

        # Painel de Reservas (Clientes)
        canal_reservas_clientes = guild.get_channel(CANAL_RESERVAS_CLIENTES_ID)
        if canal_reservas_clientes:
            async for msg in canal_reservas_clientes.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            embed_reservas = discord.Embed(
                title="💸 SISTEMA DE RESERVAS (CLIENTES)",
                description="Gerencie reserva de clientes.\n\n**Botões:**\n💸 Nova reserva\n⚙️ Editar Porcentagens (inclui VIP Fac)",
                color=0x2c2f33
            )
            await canal_reservas_clientes.send(embed=embed_reservas, view=ReservaView())

        # Painel de Reservas Funcionários
        canal_reservas_func = guild.get_channel(CANAL_RESERVAS_FUNC_PAINEL_ID)
        if canal_reservas_func:
            async for msg in canal_reservas_func.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            embed_reservas_func = discord.Embed(
                title="💸 SISTEMA DE RESERVAS (FUNCIONÁRIOS)",
                description="Gerencie reserva de funcionários.\n\n**Botões:**\n💸 Nova reserva (Func)\n⚙️ Editar Porcentagens (Func) – sem % Membros",
                color=0x2c2f33
            )
            await canal_reservas_func.send(embed=embed_reservas_func, view=ReservaFuncView())

        # Painel de Lives
        canal_lives = guild.get_channel(CANAL_LIVES_PAINEL_ID)
        if canal_lives:
            async for msg in canal_lives.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            view_lives = LiveConfigView(guild.id)
            embed_lives = await view_lives.build_embed()
            await canal_lives.send(embed=embed_lives, view=view_lives)

        # Painel de Compra e Venda
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

    await restaurar_canais_farms()
    await atualizar_ranking()
    await log_admin_embed("🤖 BOT INICIADO", f"Bot {bot.user.mention} online!\nSistemas ativos: Farm, Registro, Reservas (Clientes e Funcionários), Lives, Compra/Venda.", 0x2c2f33)

if __name__ == "__main__":
    carregar_dados()
    bot.run(TOKEN)