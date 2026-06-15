import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, UserSelect, Select
import asyncio
from datetime import datetime
import json
import os
import sys
import re

# ========= CONFIGURAÇÕES =========
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

# Canais para o sistema de SET
CANAL_SOLICITAR_SET_ID = 1236307426366591079
CANAL_REGISTROS_SET_ID = 1497880182265086106

# Categoria onde ficarão os canais privados de farm
CATEGORIA_FARMS_ID = 1515876568424255661

# Categoria do painel principal (onde fica o canal "criar-canal")
CATEGORIA_PAINEL_ID = 1515869907814973440

# Categoria para o canal de pedidos
CATEGORIA_PEDIDOS_ID = 1515879443380310147

# Logs
CHAT_LOGS_ID = 1515876949233504267
CHAT_ADMIN_LOGS_ID = 1515876971089760326
CHAT_RANK_ID = 1515877095685750894
LOG_REGISTROS_ID = int(os.getenv("LOG_REGISTROS_ID", "1498349960062570740"))
CHAT_PEDIDOS_LOG_ID = int(os.getenv("CHAT_PEDIDOS_LOG_ID", "0"))

# Grupos de permissões
CARGO_ADMIN_IDS = [CARGO_00_ID, CARGO_01_ID, CARGO_02_ID, CARGO_GERENTE_ID]

# ========= BANCO DE DADOS =========
dados = {
    "usuarios": {},
    "canais": {},
    "caixa_semana": {},
    "usuarios_banidos": [],
    "sets_pendentes": {},
    "pedidos": {
        "config": {"porcentagens": {"cliente": 50, "maquina": 40, "fac": 5, "membros": 5}, "ultima_edicao": None},
        "lista": []
    }
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
                dados["pedidos"] = {"config": {"porcentagens": {"cliente": 50, "maquina": 40, "fac": 5, "membros": 5}, "ultima_edicao": None}, "lista": []}
        return True
    except:
        return False

# ========= FUNÇÕES AUXILIARES =========
async def log_acao(acao, usuario, detalhes, cor=0x2c2f33):
    canal_logs = bot.get_channel(CHAT_LOGS_ID)
    if canal_logs:
        embed = discord.Embed(title=f"📌 LOG: {acao.upper()}", description=detalhes, color=cor, timestamp=datetime.now())
        if usuario:
            embed.set_author(name=usuario.name, icon_url=usuario.display_avatar.url)
        await canal_logs.send(embed=embed)

async def log_admin(titulo, descricao, cor=0x99aab5):
    canal = bot.get_channel(CHAT_ADMIN_LOGS_ID)
    if canal:
        await canal.send(embed=discord.Embed(title=titulo, description=descricao, color=cor, timestamp=datetime.now()))

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

# ========= CONFIGURAÇÃO DO BOT =========
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
    return tem_cargo(member, [CARGO_00_ID])

def pode_registrar_acao(member):
    return tem_cargo(member, CARGO_ADMIN_IDS)

def pode_aprovar_set(member):
    return pode_registrar_acao(member)

def pode_remover_membro(member):
    return pode_registrar_acao(member)

# ========= RANKING (apenas produtos de luxo) =========
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
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}°"
            txt += f"{emoji} **{u['nome']}** - {u[key]:,} itens\n"
        emb.add_field(name=nome, value=txt or "Nenhum dado ainda", inline=False)
    await canal.send(embed=emb)

# ========= SISTEMA DE SET =========
class SolicitarSetModal(Modal, title="📋 Solicitar SET"):
    id_jogo = TextInput(label="ID", placeholder="Seu ID no sistema", required=True)
    nome = TextInput(label="NOME", placeholder="Como quer ser chamado", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        self.id_val = self.id_jogo.value.strip()
        self.nome_val = self.nome.value.strip()
        view = RecrutadorSelectView(self)
        await interaction.followup.send("Selecione quem te recrutou:", view=view, ephemeral=True)

class RecrutadorSelectView(View):
    def __init__(self, modal):
        super().__init__(timeout=120)
        self.modal = modal
        select = UserSelect(placeholder="Escolha o recrutador", min_values=1, max_values=1)
        select.callback = self.select_callback
        self.add_item(select)
    async def select_callback(self, interaction: discord.Interaction):
        recrutador_id = int(interaction.data["values"][0])
        recrutador = interaction.guild.get_member(recrutador_id)
        if not recrutador:
            await interaction.response.send_message("Recrutador não encontrado.", ephemeral=True)
            return
        pedido_id = str(int(datetime.now().timestamp()))
        dados["sets_pendentes"][pedido_id] = {
            "solicitante_id": interaction.user.id,
            "solicitante_nome": self.modal.nome_val,
            "id_jogo": self.modal.id_val,
            "recrutador_id": recrutador_id,
            "recrutador_nome": recrutador.display_name,
            "status": "pendente",
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        salvar_dados()
        canal_registros = bot.get_channel(CANAL_REGISTROS_SET_ID)
        if canal_registros:
            embed = discord.Embed(
                title="🆕 NOVA SOLICITAÇÃO DE SET",
                description=f"**NOME:** {self.modal.nome_val}\n**ID:** {self.modal.id_val}\n**Solicitante:** <@{interaction.user.id}>\n**Recrutador:** {recrutador.mention}\n**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                color=0x2c2f33,
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"ID: {pedido_id}")
            view = AprovarSetView(pedido_id, interaction.user.id, recrutador_id)
            await canal_registros.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Solicitação enviada! Aguarde a aprovação.", ephemeral=True)
        self.stop()

class AprovarSetView(View):
    def __init__(self, pedido_id, solicitante_id, recrutador_id):
        super().__init__(timeout=None)
        self.pedido_id = pedido_id
        self.solicitante_id = solicitante_id
        self.recrutador_id = recrutador_id
    @discord.ui.button(label="✅ Aprovar SET", style=discord.ButtonStyle.success, emoji="✅")
    async def aprovar(self, interaction: discord.Interaction, button: Button):
        if not pode_aprovar_set(interaction.user):
            await interaction.response.send_message("Você não tem permissão para aprovar SETs.", ephemeral=True)
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
        cargo = guild.get_role(CARGO_MEMBRO_ID)
        if not cargo:
            await interaction.response.send_message("Cargo Membro não encontrado.", ephemeral=True)
            return
        try:
            await membro.add_roles(cargo, reason=f"SET aprovado por {interaction.user.name}")
            pedido["status"] = "aprovado"
            pedido["aprovado_por"] = interaction.user.id
            salvar_dados()
            await interaction.response.send_message(f"✅ SET aprovado! {membro.mention} agora é membro.", ephemeral=True)
            embed = discord.Embed(
                title="✅ SET APROVADO",
                description=f"**NOME:** {pedido['solicitante_nome']}\n**ID:** {pedido['id_jogo']}\n**Solicitante:** <@{self.solicitante_id}>\n**Recrutador:** <@{self.recrutador_id}>\n**Aprovado por:** {interaction.user.mention}",
                color=0x2c2f33,
                timestamp=datetime.now()
            )
            await interaction.message.edit(embed=embed, view=None)
        except Exception as e:
            await interaction.response.send_message(f"Erro ao atribuir cargo: {e}", ephemeral=True)
    @discord.ui.button(label="❌ Recusar SET", style=discord.ButtonStyle.danger, emoji="❌")
    async def recusar(self, interaction: discord.Interaction, button: Button):
        if not pode_aprovar_set(interaction.user):
            await interaction.response.send_message("Você não tem permissão para recusar SETs.", ephemeral=True)
            return
        pedido = dados["sets_pendentes"].get(self.pedido_id)
        if not pedido or pedido["status"] != "pendente":
            await interaction.response.send_message("Este pedido já foi processado ou não existe.", ephemeral=True)
            return
        pedido["status"] = "recusado"
        salvar_dados()
        embed = discord.Embed(title="❌ SET RECUSADO", description=f"Pedido ID: {self.pedido_id}\nRecusado por: {interaction.user.mention}", color=0x4f545c, timestamp=datetime.now())
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("SET recusado.", ephemeral=True)

# ========= RESTAURAÇÃO DE CANAIS DE FARM =========
async def restaurar_canais_farms():
    for user_id_str, canal_id in dados["canais"].items():
        canal = bot.get_channel(canal_id)
        if canal:
            async for msg in canal.history(limit=10):
                if msg.author == bot.user and msg.components:
                    break
            else:
                user_id = int(user_id_str)
                user = bot.get_user(user_id) or await bot.fetch_user(user_id)
                if user:
                    view = FarmChannelView(user_id, user.name, canal.id)
                    embed = discord.Embed(
                        title="🔐 SEU CANAL PRIVADO",
                        description="Use os botões abaixo para registrar farm.",
                        color=0x2c2f33
                    )
                    await canal.send(embed=embed, view=view)

# ========= MODAL FARM PRODUTOS (2 campos) =========
class FarmProdutosModal(Modal, title="📦 Registrar Farm Produtos"):
    slot = TextInput(label="SLOT (número)", placeholder="Ex: 1", required=True)
    produtos = TextInput(label="PRODUTOS (NOME:QTD, NOME:QTD)", placeholder="Ex: RELÓGIO DE LUXO:5, OBRA DE ARTE:2, BEBIDA IMPORTADA:10, AÇÕES DE EMPRESA:100, CARTEIRA NFT:1", required=True, style=discord.TextStyle.long)

    def __init__(self, user_id, user_name, canal):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        slot_num = self.slot.value.strip()
        if not slot_num.isdigit():
            await interaction.followup.send("Slot deve ser um número!", ephemeral=True)
            return
        produtos_texto = self.produtos.value
        produtos = []
        for item in produtos_texto.split(','):
            item = item.strip()
            if ':' not in item:
                continue
            nome, qtd_str = item.split(':', 1)
            nome = nome.strip().upper()
            try:
                qtd = int(qtd_str.strip())
            except:
                continue
            if qtd <= 0:
                continue
            if "RELÓGIO" in nome:
                nome_prod = "RELÓGIO DE LUXO"
            elif "OBRA" in nome:
                nome_prod = "OBRA DE ARTE"
            elif "BEBIDA" in nome:
                nome_prod = "BEBIDA IMPORTADA"
            elif "AÇÃO" in nome or "ACOES" in nome:
                nome_prod = "AÇÕES DE EMPRESA"
            elif "NFT" in nome or "CARTEIRA" in nome:
                nome_prod = "CARTEIRA NFT"
            else:
                continue
            produtos.append({"produto": nome_prod, "quantidade": qtd})
        if not produtos:
            await interaction.followup.send("Nenhum produto válido! Use o formato: NOME:QTD, NOME:QTD", ephemeral=True)
            return

        await interaction.followup.send("📸 Envie a **print da farm** aqui no canal.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return
        if not msg.attachments:
            await interaction.followup.send("Nenhuma imagem enviada.", ephemeral=True)
            return
        imagem_url = msg.attachments[0].url

        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": []}

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
        embed.set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros:
            await canal_registros.send(embed=embed)
        await interaction.followup.send("Farm registrada com sucesso!", ephemeral=True)
        await log_acao("registrar_farm", interaction.user, f"Produtos: {produtos}")
        await atualizar_ranking()

# ========= MODAL ADMIN DINHEIRO SUJO =========
class DinheiroSujoAdminModal(Modal, title="💰 Registrar Dinheiro Sujo"):
    valor = TextInput(label="Valor (R$)", placeholder="Ex: 5000", required=True)

    def __init__(self, user_id, user_name, canal):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal

    async def on_submit(self, interaction: discord.Interaction):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Você não tem permissão.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            valor = float(self.valor.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Valor inválido!", ephemeral=True)
            return

        await interaction.followup.send("📸 Envie a **print do comprovante**.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return
        imagem_url = msg.attachments[0].url

        # Selecionar membro que recebeu
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
        await self.canal.send(embed=embed)
        await interaction.response.send_message(f"R$ {self.valor:,.2f} registrado como dinheiro sujo para {self.target_user_name}!", ephemeral=True)
        await log_acao("registrar_dinheiro_sujo", interaction.user, f"Usuário: {self.target_user_name}\nValor: {self.valor}\nMembro: {membro_obj.name}")
        await atualizar_ranking()
        self.stop()

# ========= VIEW DO CANAL PRIVADO =========
class FarmChannelView(View):
    def __init__(self, user_id, user_name, canal_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.user_name = user_name
        self.canal_id = canal_id

    @discord.ui.button(label="📦 Farm Produtos", style=discord.ButtonStyle.secondary, emoji="📦", row=0)
    async def farm_produtos(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("Apenas o dono do canal pode registrar farm!", ephemeral=True)
            return
        await interaction.response.send_modal(FarmProdutosModal(self.user_id, self.user_name, interaction.channel))

    @discord.ui.button(label="💰 Registrar Dinheiro Sujo (Admin)", style=discord.ButtonStyle.danger, emoji="💰", row=0)
    async def dinheiro_sujo(self, interaction: discord.Interaction, button: Button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Apenas cargos 00,01,02 e Gerente podem registrar dinheiro sujo.", ephemeral=True)
            return
        await interaction.response.send_modal(DinheiroSujoAdminModal(self.user_id, self.user_name, interaction.channel))

    @discord.ui.button(label="✏️ Editar Registro", style=discord.ButtonStyle.secondary, emoji="✏️", row=1)
    async def editar_registro(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Função em desenvolvimento.", ephemeral=True)

    @discord.ui.button(label="📋 Meus Registros", style=discord.ButtonStyle.primary, emoji="📋", row=1)
    async def meus_registros(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Função em desenvolvimento.", ephemeral=True)

    @discord.ui.button(label="🗑️ Fechar Canal", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def fechar_canal(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        await interaction.response.send_message("⚠️ Tem certeza?", view=ConfirmarFechamentoView(self.user_id, interaction.channel), ephemeral=True)

class ConfirmarFechamentoView(View):
    def __init__(self, user_id, canal):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.canal = canal
    @discord.ui.button(label="Sim, fechar", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        if str(self.user_id) in dados["canais"]:
            del dados["canais"][str(self.user_id)]
            salvar_dados()
        await self.canal.delete()
        await interaction.followup.send("Canal fechado!", ephemeral=True)
        await log_acao("fechar_canal", interaction.user, f"Canal {self.canal.name} fechado", 0x4f545c)
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Cancelado!", ephemeral=True)

# ========= SISTEMA DE PEDIDOS =========
class PedidoView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="📝 Novo Pedido", style=discord.ButtonStyle.success, emoji="📝")
    async def novo_pedido(self, interaction: discord.Interaction, button: Button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Apenas cargos 00,01,02 e Gerente podem criar pedidos.", ephemeral=True)
            return
        await interaction.response.send_modal(NovoPedidoModal())
    @discord.ui.button(label="⚙️ Editar Porcentagens", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def editar_porcentagens(self, interaction: discord.Interaction, button: Button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Apenas cargos 00,01,02 e Gerente podem editar porcentagens.", ephemeral=True)
            return
        await interaction.response.send_modal(EditarPorcentagensModal())

class NovoPedidoModal(Modal, title="📝 Novo Pedido"):
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
        pedido = {
            "id": len(dados["pedidos"]["lista"]) + 1,
            "cliente": self.cliente.value.strip(),
            "valor_total": valor,
            "prazo_entrega": self.prazo_entrega.value.strip(),
            "descontado_caixa": descontado,
            "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "criado_por": interaction.user.id,
            "distribuicao": {
                "cliente": valor * pcts["cliente"] / 100,
                "maquina": valor * pcts["maquina"] / 100,
                "fac": valor * pcts["fac"] / 100,
                "membros": valor * pcts["membros"] / 100
            },
            "pago": False
        }
        dados["pedidos"]["lista"].append(pedido)
        salvar_dados()
        embed = discord.Embed(title="📝 NOVO PEDIDO", description=f"Cliente: {pedido['cliente']}\nValor: R$ {valor:,.2f}\nPrazo: {pedido['prazo_entrega']}\nDescontado: {descontado}", color=0x2c2f33)
        await interaction.followup.send(embed=embed, ephemeral=True)

class EditarPorcentagensModal(Modal, title="⚙️ Editar Porcentagens"):
    cliente = TextInput(label="% Cliente", default="50", required=True)
    maquina = TextInput(label="% Máquina", default="40", required=True)
    fac = TextInput(label="% Facção", default="5", required=True)
    membros = TextInput(label="% Membros", default="5", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return
        try:
            pcts = {
                "cliente": float(self.cliente.value.replace(",", ".")),
                "maquina": float(self.maquina.value.replace(",", ".")),
                "fac": float(self.fac.value.replace(",", ".")),
                "membros": float(self.membros.value.replace(",", "."))
            }
            if abs(sum(pcts.values()) - 100) > 0.01:
                await interaction.response.send_message("A soma deve ser 100%", ephemeral=True)
                return
            dados["pedidos"]["config"]["porcentagens"] = pcts
            dados["pedidos"]["config"]["ultima_edicao"] = {"por": interaction.user.id, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            salvar_dados()
            await interaction.response.send_message("Porcentagens atualizadas!", ephemeral=True)
        except:
            await interaction.response.send_message("Valores inválidos.", ephemeral=True)

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
            await log_admin("🗑️ USUÁRIO REMOVIDO", f"{user.mention} por {interaction.user.mention}")
            await atualizar_ranking()
        except:
            await interaction.followup.send("Erro ao remover usuário.", ephemeral=True)

# ========= BOTÃO CRIAR CANAL =========
class BotaoCriarCanalView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="🔓 Criar Meu Canal Privado", style=discord.ButtonStyle.success, emoji="🔓")
    async def criar_canal(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if interaction.guild is None:
            await interaction.followup.send("Use em um servidor!", ephemeral=True)
            return
        if str(interaction.user.id) in dados["canais"]:
            canal = interaction.guild.get_channel(dados["canais"][str(interaction.user.id)])
            if canal:
                await interaction.followup.send(f"Você já possui um canal: {canal.mention}", ephemeral=True)
                return
        categoria = interaction.guild.get_channel(CATEGORIA_FARMS_ID)
        if not categoria:
            await interaction.followup.send("Categoria não encontrada!", ephemeral=True)
            return
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        cargo_admin = interaction.guild.get_role(CARGO_00_ID)
        if cargo_admin:
            overwrites[cargo_admin] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        nome = f"farm-{interaction.user.name}".lower().replace(" ", "-")[:90]
        canal = await categoria.create_text_channel(nome, overwrites=overwrites)
        dados["canais"][str(interaction.user.id)] = canal.id
        salvar_dados()
        view = FarmChannelView(interaction.user.id, interaction.user.name, canal.id)
        embed = discord.Embed(title="🔐 SEU CANAL PRIVADO", description="Use os botões abaixo.", color=0x2c2f33)
        await canal.send(embed=embed, view=view)
        await interaction.followup.send(f"✅ Canal criado: {canal.mention}", ephemeral=True)
        await log_acao("criar_canal", interaction.user, f"Canal {canal.name} criado")
        await atualizar_ranking()

# ========= EVENTOS PRINCIPAIS =========
@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} online!")
    for guild in bot.guilds:
        # Painel criar canal
        categoria_painel = guild.get_channel(CATEGORIA_PAINEL_ID)
        if categoria_painel:
            canal_criar = discord.utils.get(categoria_painel.channels, name="criar-canal")
            if not canal_criar:
                canal_criar = await categoria_painel.create_text_channel("criar-canal")
            async for msg in canal_criar.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            embed = discord.Embed(title="🔓 SISTEMA DE FARM", description="Clique no botão abaixo para criar seu canal privado!", color=0x2c2f33)
            await canal_criar.send(embed=embed, view=BotaoCriarCanalView())

        # Painel SET
        canal_set = guild.get_channel(CANAL_SOLICITAR_SET_ID)
        if canal_set:
            async for msg in canal_set.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            embed_set = discord.Embed(title="📋 SOLICITAR SET", description="Clique no botão abaixo.", color=0x2c2f33)
            view = View(timeout=None)
            button = Button(label="📝 Solicitar SET", style=discord.ButtonStyle.success, emoji="📝")
            async def button_callback(interaction):
                await interaction.response.send_modal(SolicitarSetModal())
            button.callback = button_callback
            view.add_item(button)
            await canal_set.send(embed=embed_set, view=view)

        # Painel Pedidos
        categoria_pedidos = guild.get_channel(CATEGORIA_PEDIDOS_ID)
        if categoria_pedidos:
            canal_pedidos = discord.utils.get(categoria_pedidos.channels, name="pedidos")
            if not canal_pedidos:
                canal_pedidos = await categoria_pedidos.create_text_channel("pedidos")
            async for msg in canal_pedidos.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            embed_pedidos = discord.Embed(title="📦 SISTEMA DE PEDIDOS", description="Gerencie pedidos.", color=0x2c2f33)
            await canal_pedidos.send(embed=embed_pedidos, view=PedidoView())

        # Botão remover membro no canal criar-canal
        if categoria_painel:
            canal_criar = discord.utils.get(categoria_painel.channels, name="criar-canal")
            if canal_criar:
                found = False
                async for msg in canal_criar.history(limit=10):
                    if msg.author == bot.user and "Remover Membro" in (msg.content or ""):
                        found = True
                        break
                if not found:
                    view_remove = View(timeout=None)
                    remove_button = Button(label="🗑️ Remover Membro", style=discord.ButtonStyle.danger, emoji="🗑️")
                    async def remove_callback(interaction):
                        if not pode_remover_membro(interaction.user):
                            await interaction.response.send_message("Sem permissão.", ephemeral=True)
                            return
                        await interaction.response.send_modal(RemoverUsuarioModal())
                    remove_button.callback = remove_callback
                    view_remove.add_item(remove_button)
                    embed_remove = discord.Embed(title="🗑️ REMOVER MEMBRO", description="Remova um membro do sistema.", color=0x4f545c)
                    await canal_criar.send(embed=embed_remove, view=view_remove)

    await restaurar_canais_farms()
    await atualizar_ranking()
    await log_admin("🤖 BOT INICIADO", f"Bot {bot.user.mention} online!")

if __name__ == "__main__":
    carregar_dados()
    bot.run(TOKEN)
