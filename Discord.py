import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, UserSelect, Select
import asyncio
from datetime import datetime
import json
import os
import sys
import re

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
CATEGORIA_PEDIDOS_ID = 1515879443380310147

CHAT_LOGS_ID = 1515876949233504267
CHAT_ADMIN_LOGS_ID = 1515876971089760326
CHAT_RANK_ID = 1515877095685750894
LOG_REGISTROS_ID = int(os.getenv("LOG_REGISTROS_ID", "1498349960062570740"))
CHAT_PEDIDOS_LOG_ID = int(os.getenv("CHAT_PEDIDOS_LOG_ID", "0"))

CARGO_ADMIN_IDS = [CARGO_00_ID, CARGO_01_ID, CARGO_02_ID, CARGO_GERENTE_ID]
CARGO_REMOVER_MEMBRO_IDS = CARGO_ADMIN_IDS

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

async def log_embed(titulo, descricao, cor, thumbnail=None, fields=None):
    """Função para enviar embeds bonitos para o canal de logs"""
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
    return tem_cargo(member, [CARGO_00_ID])

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
            tot_relogio = sum(p.get("quantidade", 0) for f in data.get("farms", []) for p in f.get("produtos", []) if isinstance(p, dict) and p.get("produto") == "RELÓGIO DE LUXO")
            tot_obra = sum(p.get("quantidade", 0) for f in data.get("farms", []) for p in f.get("produtos", []) if isinstance(p, dict) and p.get("produto") == "OBRA DE ARTE")
            tot_bebida = sum(p.get("quantidade", 0) for f in data.get("farms", []) for p in f.get("produtos", []) if isinstance(p, dict) and p.get("produto") == "BEBIDA IMPORTADA")
            tot_acoes = sum(p.get("quantidade", 0) for f in data.get("farms", []) for p in f.get("produtos", []) if isinstance(p, dict) and p.get("produto") == "AÇÕES DE EMPRESA")
            tot_nft = sum(p.get("quantidade", 0) for f in data.get("farms", []) for p in f.get("produtos", []) if isinstance(p, dict) and p.get("produto") == "CARTEIRA NFT")
            usuarios_data.append({
                "nome": user.name,
                "user_id": uid,
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
            await interaction.response.send_message("Apenas o cargo 00 pode resetar o ranking.", ephemeral=True)
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
        user = interaction.data["values"][0]
        recrutador_id = int(user)
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
        view = EscolherCargoView(self.pedido_id, self.solicitante_id, self.recrutador_id)
        await interaction.response.send_message("Selecione o cargo que deseja atribuir ao novo membro:", view=view, ephemeral=True)
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
        try:
            solicitante = await bot.fetch_user(self.solicitante_id)
            await solicitante.send(f"❌ Seu pedido de SET foi **recusado** por {interaction.user.mention}.")
        except:
            pass
        embed = discord.Embed(title="❌ SET RECUSADO", description=f"Pedido ID: {self.pedido_id}\nRecusado por: {interaction.user.mention}", color=0x4f545c, timestamp=datetime.now())
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("SET recusado com sucesso!", ephemeral=True)

class EscolherCargoView(View):
    def __init__(self, pedido_id, solicitante_id, recrutador_id):
        super().__init__(timeout=120)
        self.pedido_id = pedido_id
        self.solicitante_id = solicitante_id
        self.recrutador_id = recrutador_id
        options = [discord.SelectOption(label="Membro", value=str(CARGO_MEMBRO_ID), description="Cargo padrão de membro", emoji="🛡️")]
        select = Select(placeholder="Escolha o cargo...", options=options, min_values=1, max_values=1)
        select.callback = self.cargo_selecionado
        self.add_item(select)
    async def cargo_selecionado(self, interaction: discord.Interaction):
        cargo_id = int(self.children[0].values[0])
        guild = interaction.guild
        membro = guild.get_member(self.solicitante_id)
        if not membro:
            await interaction.response.send_message("Solicitante não encontrado no servidor.", ephemeral=True)
            return
        cargo = guild.get_role(cargo_id)
        if not cargo:
            await interaction.response.send_message("Cargo não encontrado.", ephemeral=True)
            return
        try:
            await membro.add_roles(cargo, reason=f"Aprovado SET por {interaction.user.name}")
            pedido = dados["sets_pendentes"].get(self.pedido_id)
            if pedido:
                pedido["status"] = "aprovado"
                pedido["aprovado_por"] = interaction.user.id
                pedido["cargo_dado"] = cargo_id
                salvar_dados()
            recrutador = guild.get_member(self.recrutador_id)
            if recrutador:
                try:
                    await recrutador.send(f"✅ O SET de {membro.mention} foi aprovado por {interaction.user.mention}!")
                except:
                    pass
            try:
                await membro.send(f"✅ Parabéns! Seu SET foi **aprovado** e você recebeu o cargo {cargo.mention}. Bem-vindo(a)!")
            except:
                pass
            canal_registros = bot.get_channel(CANAL_REGISTROS_SET_ID)
            if canal_registros:
                embed = discord.Embed(
                    title="✅ SET APROVADO",
                    description=f"**NOME:** {pedido['solicitante_nome']}\n**ID:** {pedido['id_jogo']}\n**Solicitante:** <@{self.solicitante_id}>\n**Recrutador:** <@{self.recrutador_id}>\n**Cargo atribuído:** {cargo.mention}\n**Aprovado por:** {interaction.user.mention}",
                    color=0x2c2f33,
                    timestamp=datetime.now()
                )
                async for msg in canal_registros.history(limit=20):
                    if msg.author == bot.user and msg.embeds and str(self.pedido_id) in (msg.embeds[0].footer.text if msg.embeds[0].footer else ""):
                        await msg.edit(embed=embed, view=None)
                        break
            await interaction.response.send_message(f"✅ SET aprovado! Cargo {cargo.mention} atribuído a {membro.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Erro ao atribuir cargo: {e}", ephemeral=True)

# ========= RESTAURAÇÃO =========
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
                        description=f"Bem-vindo(a) {user.mention}!\n\n🔒 Apenas você e administradores têm acesso.\n\n**BOTÕES:**\n📦 **Farm Produtos**\n💰 **Registrar Dinheiro Sujo (Admin)**\n✏️ **Editar Registro**\n📋 **Meus Registros**\n📊 **Fechar Caixa**\n✏️ **Mudar Nome**\n📜 **Histórico Caixa**\n🔄 **Reset Semanal**\n🗑️ **Fechar Canal**",
                        color=0x2c2f33
                    )
                    await canal.send(embed=embed, view=view)

# ========= MODAL DE FARM PRODUTOS =========
class FarmProdutosModal(Modal, title="📦 Farm Produtos"):
    relogio = TextInput(label="RELÓGIO DE LUXO - Quantidade", placeholder="Ex: 5", required=False)
    obra = TextInput(label="OBRA DE ARTE - Quantidade", placeholder="Ex: 2", required=False)
    bebida = TextInput(label="BEBIDA IMPORTADA - Quantidade", placeholder="Ex: 10", required=False)
    acoes = TextInput(label="AÇÕES DE EMPRESA - Quantidade", placeholder="Ex: 100", required=False)
    nft = TextInput(label="CARTEIRA NFT - Quantidade", placeholder="Ex: 1", required=False)

    def __init__(self, user_id, user_name, canal):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        produtos = []
        for campo, nome in [(self.relogio, "RELÓGIO DE LUXO"), (self.obra, "OBRA DE ARTE"), (self.bebida, "BEBIDA IMPORTADA"), (self.acoes, "AÇÕES DE EMPRESA"), (self.nft, "CARTEIRA NFT")]:
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

        # Armazena os produtos temporariamente e pede o slot
        self.produtos = produtos
        await interaction.followup.send("📝 Agora digite o **número do SLOT** no chat.", ephemeral=False)
        
        def check_slot(m):
            return m.author == interaction.user and m.channel == self.canal and m.content.strip().isdigit()
        
        try:
            msg_slot = await bot.wait_for('message', timeout=60.0, check=check_slot)
            slot_num = int(msg_slot.content.strip())
            await msg_slot.delete()
        except asyncio.TimeoutError:
            await self.canal.send("⏰ Tempo esgotado! Registro cancelado.", delete_after=10)
            return

        # Após receber o slot, pede a print
        await self.canal.send("📸 Agora envie a **print da farm** aqui no canal.")
        def check_print(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments
        try:
            msg_print = await bot.wait_for('message', timeout=60.0, check=check_print)
            imagem_url = msg_print.attachments[0].url
            await msg_print.delete()
        except asyncio.TimeoutError:
            await self.canal.send("⏰ Tempo esgotado! Registro cancelado.", delete_after=10)
            return

        # Salva o registro
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": []}

        registro = {
            "produtos": self.produtos,
            "slot": slot_num,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "print_url": imagem_url,
            "validado": True,
            "farm_id": len(dados["usuarios"][str(self.user_id)]["farms"]) + 1
        }
        dados["usuarios"][str(self.user_id)]["farms"].append(registro)
        salvar_dados()

        embed = discord.Embed(title="✅ FARM PRODUTOS REGISTRADA", description=f"**Usuário:** <@{self.user_id}>\n**Slot:** {slot_num}\n", color=0x2c2f33)
        desc = "".join(f"🔹 **{p['produto']}:** {p['quantidade']} itens\n" for p in self.produtos)
        embed.description += desc
        embed.add_field(name="📅 Data", value=datetime.now().strftime("%d/%m/%Y às %H:%M"), inline=False)
        embed.add_field(name="📦 Total de farms", value=f"{len(dados['usuarios'][str(self.user_id)]['farms'])} farms", inline=False)
        embed.set_image(url=imagem_url)
        embed.set_footer(text=f"Farm ID: {registro['farm_id']}")
        await self.canal.send(embed=embed)
        await log_embed("📦 FARM PRODUTOS REGISTRADA", f"Usuário: <@{self.user_id}>\nSlot: {slot_num}\nProdutos: {desc}", 0x2c2f33, thumbnail=interaction.user.display_avatar.url)
        await log_admin_embed("📦 NOVA FARM PRODUTOS", f"Usuário: {interaction.user.mention}\nProdutos: {desc}\nSlot: {slot_num}", 0x2c2f33)
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
        if not pode_registrar_acao(interaction.user):
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

    @discord.ui.button(label="📦 Farm Produtos", style=discord.ButtonStyle.secondary, emoji="📦", row=0)
    async def farm_produtos(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("Apenas o dono do canal pode registrar farm!", ephemeral=True)
            return
        await interaction.response.send_modal(FarmProdutosModal(self.user_id, self.user_name, interaction.channel))

    @discord.ui.button(label="💰 Registrar Dinheiro Sujo (Admin)", style=discord.ButtonStyle.danger, emoji="💰", row=0)
    async def registrar_dinheiro_sujo_admin(self, interaction: discord.Interaction, button: Button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Apenas cargos 00,01,02 e Gerente podem registrar dinheiro sujo.", ephemeral=True)
            return
        await interaction.response.send_modal(DinheiroSujoAdminModal(self.user_id, self.user_name, interaction.channel))

    @discord.ui.button(label="✏️ Editar Registro", style=discord.ButtonStyle.secondary, emoji="✏️", row=0)
    async def editar_registro(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Função em desenvolvimento. Em breve!", ephemeral=True)

    @discord.ui.button(label="📊 Fechar Caixa", style=discord.ButtonStyle.secondary, emoji="📊", row=1)
    async def fechar_caixa(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Função em desenvolvimento. Em breve!", ephemeral=True)

    @discord.ui.button(label="✏️ Mudar Nome", style=discord.ButtonStyle.secondary, emoji="✏️", row=1)
    async def mudar_nome(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem mudar o nome.", ephemeral=True)
            return
        await interaction.response.send_modal(MudarNomeModal(interaction.channel))

    @discord.ui.button(label="📜 Histórico Caixa", style=discord.ButtonStyle.secondary, emoji="📜", row=1)
    async def historico_caixa(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Função em desenvolvimento. Em breve!", ephemeral=True)

    @discord.ui.button(label="📋 Meus Registros", style=discord.ButtonStyle.primary, emoji="📋", row=2)
    async def meus_registros(self, interaction: discord.Interaction, button: Button):
        user_data = dados["usuarios"].get(str(self.user_id), {})
        farms = user_data.get("farms", [])
        if not farms:
            await interaction.response.send_message("Você ainda não tem registros de farm.", ephemeral=True)
            return
        embed = discord.Embed(title=f"📋 SEUS REGISTROS - {self.user_name}", color=0x2c2f33)
        for farm in farms[-10:]:
            produtos_str = ", ".join(f"{p['produto']}: {p['quantidade']}" for p in farm["produtos"])
            embed.add_field(name=f"Farm #{farm.get('farm_id','?')} - Slot {farm.get('slot','?')}", value=f"**Produtos:** {produtos_str}\n**Data:** {farm['data']}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔄 Reset Semanal", style=discord.ButtonStyle.danger, emoji="🔄", row=2)
    async def reset_semanal(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem resetar a semana.", ephemeral=True)
            return
        # Implementação real
        confirm_view = ConfirmResetSemanalView(self.user_id, self.user_name, interaction.channel)
        await interaction.response.send_message("⚠️ **Tem certeza que deseja resetar a semana?** Isso apagará todos os registros de farm, pagamentos e dinheiro sujo deste usuário.", view=confirm_view, ephemeral=True)

    @discord.ui.button(label="🗑️ Fechar Canal", style=discord.ButtonStyle.danger, emoji="🗑️", row=2)
    async def fechar_canal(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem fechar o canal.", ephemeral=True)
            return
        confirm_view = ConfirmarFechamentoView(self.user_id, interaction.channel)
        await interaction.response.send_message("⚠️ **Tem certeza que deseja fechar este canal?**", view=confirm_view, ephemeral=True)

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

class ConfirmarFechamentoView(View):
    def __init__(self, user_id, canal):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.canal = canal
    @discord.ui.button(label="Sim, fechar canal", style=discord.ButtonStyle.danger, emoji="✅")
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
        await log_admin_embed("🗑️ CANAL FECHADO", f"Canal de {interaction.user.mention} foi fechado por {interaction.user.mention}", 0x4f545c)
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Cancelado!", ephemeral=True)

class MudarNomeModal(Modal, title="✏️ Mudar Nome do Canal"):
    novo_nome = TextInput(label="Novo nome", placeholder="Ex: farm-lucas", required=True, max_length=90)
    def __init__(self, canal):
        super().__init__()
        self.canal = canal
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        nome = ''.join(c for c in self.novo_nome.value.lower().replace(" ", "-") if c.isalnum() or c == '-') or "farm"
        try:
            await self.canal.edit(name=nome)
            await interaction.followup.send(f"Nome alterado para {nome}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Erro: {str(e)[:100]}", ephemeral=True)

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
        if not interaction.guild.me.guild_permissions.manage_channels:
            await interaction.followup.send("Bot precisa de permissão de Administrador.", ephemeral=True)
            return
        if str(interaction.user.id) in dados["canais"]:
            canal = interaction.guild.get_channel(dados["canais"][str(interaction.user.id)])
            if canal:
                await interaction.followup.send(f"Você já possui um canal! Acesse: {canal.mention}", ephemeral=True)
                return
            else:
                del dados["canais"][str(interaction.user.id)]
                salvar_dados()
        try:
            categoria = interaction.guild.get_channel(CATEGORIA_FARMS_ID)
            if not categoria:
                await interaction.followup.send("Categoria não encontrada!", ephemeral=True)
                return
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True, add_reactions=True, read_message_history=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, attach_files=True, embed_links=True, read_message_history=True)
            }
            cargo_admin = interaction.guild.get_role(CARGO_00_ID)
            if cargo_admin:
                overwrites[cargo_admin] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True, manage_channels=True)
            nome = f"farm-{interaction.user.name}".lower().replace(" ", "-")[:90]
            canal = await categoria.create_text_channel(nome, overwrites=overwrites)
            dados["canais"][str(interaction.user.id)] = canal.id
            salvar_dados()
            view = FarmChannelView(interaction.user.id, interaction.user.name, canal.id)
            embed = discord.Embed(
                title="🔐 SEU CANAL PRIVADO",
                description=f"Bem-vindo(a) {interaction.user.mention}!\n\n🔒 Apenas você e administradores têm acesso.\n\n**BOTÕES:**\n📦 **Farm Produtos**\n💰 **Registrar Dinheiro Sujo (Admin)**\n✏️ **Editar Registro**\n📋 **Meus Registros**",
                color=0x2c2f33
            )
            await canal.send(embed=embed, view=view)
            await log_embed("🔓 CANAL CRIADO", f"{interaction.user.mention} criou seu canal privado: {canal.mention}", 0x2c2f33, thumbnail=interaction.user.display_avatar.url)
            await log_admin_embed("🔓 CANAL CRIADO", f"Usuário: {interaction.user.mention}\nCanal: {canal.mention}", 0x2c2f33)
            await interaction.followup.send(f"✅ Canal criado! Acesse: {canal.mention}", ephemeral=True)
            await atualizar_ranking()
        except Exception as e:
            await interaction.followup.send(f"Erro: {str(e)[:200]}", ephemeral=True)

# ========= SISTEMA DE PEDIDOS =========
class PedidoView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="📝 Novo Pedido", style=discord.ButtonStyle.success, emoji="📝")
    async def novo_pedido(self, interaction: discord.Interaction, button: Button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Apenas cargos 00,01,02 ou Gerente podem criar pedidos.", ephemeral=True)
            return
        await interaction.response.send_modal(NovoPedidoModal())
    @discord.ui.button(label="⚙️ Editar Porcentagens", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def editar_porcentagens(self, interaction: discord.Interaction, button: Button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Apenas cargos 00,01,02 ou Gerente podem editar porcentagens.", ephemeral=True)
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
        cliente_part = valor * pcts["cliente"] / 100
        maquina_part = valor * pcts["maquina"] / 100
        fac_part = valor * pcts["fac"] / 100
        membros_part = valor * pcts["membros"] / 100
        pedido = {
            "id": len(dados["pedidos"]["lista"]) + 1,
            "cliente": self.cliente.value.strip(),
            "valor_total": valor,
            "prazo_entrega": self.prazo_entrega.value.strip(),
            "descontado_caixa": descontado,
            "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "criado_por": interaction.user.id,
            "distribuicao": {"cliente": cliente_part, "maquina": maquina_part, "fac": fac_part, "membros": membros_part},
            "pago": False
        }
        dados["pedidos"]["lista"].append(pedido)
        salvar_dados()
        embed = discord.Embed(title="📝 NOVO PEDIDO CRIADO", color=0x2c2f33, timestamp=datetime.now())
        embed.add_field(name="Cliente", value=pedido["cliente"], inline=True)
        embed.add_field(name="Valor Total", value=f"R$ {valor:,.2f}", inline=True)
        embed.add_field(name="Prazo", value=pedido["prazo_entrega"], inline=True)
        embed.add_field(name="Descontado", value=descontado, inline=True)
        embed.add_field(name="Distribuição", value=f"Cliente: R$ {cliente_part:,.2f} ({pcts['cliente']}%)\nMáquina: R$ {maquina_part:,.2f} ({pcts['maquina']}%)\nFacção: R$ {fac_part:,.2f} ({pcts['fac']}%)\nMembros: R$ {membros_part:,.2f} ({pcts['membros']}%)", inline=False)
        embed.set_footer(text=f"Pedido #{pedido['id']}")
        await interaction.followup.send(embed=embed, ephemeral=True)
        await log_admin_embed("📝 NOVO PEDIDO", f"Cliente: {pedido['cliente']}\nValor: R$ {valor:,.2f}\nPrazo: {pedido['prazo_entrega']}", 0x2c2f33)

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
            await log_admin_embed("⚙️ PORCENTAGENS EDITADAS", f"Novas porcentagens: Cliente {pcts['cliente']}%, Máquina {pcts['maquina']}%, Facção {pcts['fac']}%, Membros {pcts['membros']}%", 0x2c2f33)
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
            embed_criar = discord.Embed(
                title="🔓 SISTEMA DE FARM",
                description="Clique no botão abaixo para criar seu canal privado!",
                color=0x2c2f33
            )
            await canal_criar.send(embed=embed_criar, view=BotaoCriarCanalView())
        # Painel SET
        canal_set = guild.get_channel(CANAL_SOLICITAR_SET_ID)
        if canal_set:
            async for msg in canal_set.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            embed_set = discord.Embed(
                title="📋 SOLICITAR SET",
                description="Clique no botão abaixo para solicitar seu SET.",
                color=0x2c2f33
            )
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
            embed_pedidos = discord.Embed(
                title="📦 SISTEMA DE PEDIDOS",
                description="Gerencie pedidos de clientes.\n\n**Botões:**\n📝 Novo Pedido\n⚙️ Editar Porcentagens",
                color=0x2c2f33
            )
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
                            await interaction.response.send_message("Você não tem permissão para remover membros.", ephemeral=True)
                            return
                        await interaction.response.send_modal(RemoverUsuarioModal())
                    remove_button.callback = remove_callback
                    view_remove.add_item(remove_button)
                    embed_remove = discord.Embed(
                        title="🗑️ REMOVER MEMBRO",
                        description="Remova um membro do sistema (limpa registros e deleta canal).\n\n**Permissões:** Cargos 00,01,02 e Gerente.",
                        color=0x4f545c
                    )
                    await canal_criar.send(embed=embed_remove, view=view_remove)

    await restaurar_canais_farms()
    await atualizar_ranking()
    await log_admin_embed("🤖 BOT INICIADO", f"Bot {bot.user.mention} online!", 0x2c2f33)

if __name__ == "__main__":
    carregar_dados()
    bot.run(TOKEN)
