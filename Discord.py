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

# Outros IDs (não usados em painéis removidos, mas mantidos para compatibilidade)
CANAL_LOGS_COMPRA_VENDA_ID = int(os.getenv("CANAL_LOGS_COMPRA_VENDA_ID", "1509201907842023444"))
CHAT_PEDIDOS_LOG_ID = int(os.getenv("CHAT_PEDIDOS_LOG_ID", "0"))

# Grupos de permissões
CARGO_REGISTRAR_ACAO_IDS = [CARGO_00_ID, CARGO_01_ID, CARGO_02_ID, CARGO_GERENTE_ID]
CARGO_REMOVER_MEMBRO_IDS = CARGO_REGISTRAR_ACAO_IDS

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

async def log_acao(acao, usuario, detalhes, cor=None):
    cores = {"criar_canal": 0x2c2f33, "registrar_farm": 0x2c2f33, "registrar_dinheiro_sujo": 0x4f545c, "pagar": 0x99aab5, "fechar_canal": 0x4f545c, "fechar_caixa": 0x99aab5, "reset_rank": 0x4f545c, "usuario_removido": 0x4f545c, "editar_farm": 0x2c2f33, "editar_dinheiro_sujo": 0x2c2f33}
    cor_final = cores.get(acao, 0x2c2f33) if cor is None else cor
    canal_logs = bot.get_channel(CHAT_LOGS_ID)
    if canal_logs:
        embed = discord.Embed(title=f"📌 LOG: {acao.upper()}", description=detalhes, color=cor_final, timestamp=datetime.now())
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

# ========= CONFIGURAÇÃO DE INTENTS =========
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
    return tem_cargo(member, CARGO_REGISTRAR_ACAO_IDS)

def pode_aprovar_set(member):
    return pode_registrar_acao(member)

def pode_remover_membro(member):
    return tem_cargo(member, CARGO_REMOVER_MEMBRO_IDS)

# ========= RANKING (sem CHUMBO, CAPSULA, PÓLVORA) =========
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
            # Só produtos de luxo
            tot_relogio = sum(p.get("quantidade", 0) for f in data.get("farms", []) for p in f.get("produtos", []) if isinstance(p, dict) and p.get("produto") == "RELÓGIO DE LUXO")
            tot_obra = sum(p.get("quantidade", 0) for f in data.get("farms", []) for p in f.get("produtos", []) if isinstance(p, dict) and p.get("produto") == "OBRA DE ARTE")
            tot_bebida = sum(p.get("quantidade", 0) for f in data.get("farms", []) for p in f.get("produtos", []) if isinstance(p, dict) and p.get("produto") == "BEBIDA IMPORTADA")
            tot_acoes = sum(p.get("quantidade", 0) for f in data.get("farms", []) for p in f.get("produtos", []) if isinstance(p, dict) and p.get("produto") == "AÇÕES DE EMPRESA")
            tot_nft = sum(p.get("quantidade", 0) for f in data.get("farms", []) for p in f.get("produtos", []) if isinstance(p, dict) and p.get("produto") == "CARTEIRA NFT")
            tot_pag = sum(p["valor"] for p in data.get("pagamentos", []))
            qtd_pag = len(data.get("pagamentos", []))
            din_sujo = data.get("dinheiro_sujo", 0)
            usuarios_data.append({
                "nome": user.name,
                "user_id": uid,
                "total_relogio": tot_relogio,
                "total_obra": tot_obra,
                "total_bebida": tot_bebida,
                "total_acoes": tot_acoes,
                "total_nft": tot_nft,
                "total_pagamentos": tot_pag,
                "quantidade_pagamentos": qtd_pag,
                "dinheiro_sujo": din_sujo
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

    lista_salario = sorted(usuarios_data, key=lambda x: x["total_pagamentos"], reverse=True)[:5]
    txt = ""
    for i, u in enumerate(lista_salario, 1):
        if u["total_pagamentos"] == 0:
            continue
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}°"
        txt += f"{emoji} **{u['nome']}** - R$ {u['total_pagamentos']:,.2f} ({u['quantidade_pagamentos']} pagamentos)\n"
    emb.add_field(name="💰 TOP SALÁRIO", value=txt or "Nenhum dado ainda", inline=False)

    lista_sujo = sorted(usuarios_data, key=lambda x: x["dinheiro_sujo"], reverse=True)[:5]
    txt = ""
    for i, u in enumerate(lista_sujo, 1):
        if u["dinheiro_sujo"] == 0:
            continue
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}°"
        txt += f"{emoji} **{u['nome']}** - R$ {u['dinheiro_sujo']:,.2f}\n"
    emb.add_field(name="💀 DINHEIRO SUJO", value=txt or "Nenhum dado ainda", inline=False)

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
        dados["dinheiro_sujo"] = {}
        salvar_dados()
        await log_acao("reset_rank", interaction.user, f"Ranking resetado por {interaction.user.mention}", 0x4f545c)
        await log_admin("RANKING RESETADO", f"Admin: {interaction.user.mention}\nData: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0x4f545c)
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
                    tipo = "ADMIN" if is_admin(user) else "MEMBRO"
                    embed = discord.Embed(
                        title="🔐 SEU CANAL PRIVADO",
                        description=f"Bem-vindo(a) {user.mention}!\n\n🔒 Apenas você e administradores têm acesso.\n\n**BOTÕES DISPONÍVEIS PARA {tipo}:**\n📦 **Farm Produtos** - Registrar farm de produtos (com print)\n💰 **Farm Dinheiro Sujo** - Registrar dinheiro sujo (com print)\n✏️ **Editar Registro** - Corrigir um registro\n📋 **Meus Registros** - Ver histórico completo",
                        color=0x2c2f33
                    )
                    if tipo == "ADMIN":
                        embed.description += "\n\n**BOTÕES ADMINISTRATIVOS:**\n📊 **Fechar Caixa** - Fechar caixa semanal\n✏️ **Mudar Nome** - Renomear canal\n📜 **Histórico Caixa** - Ver fechamentos\n🔄 **Reset Semanal** - Limpar dados da semana\n🗑️ **Fechar Canal** - Deletar canal"
                    await canal.send(embed=embed, view=view)

# ========= MODAIS DE FARM =========
class DinheiroSujoModal(Modal, title="💰 Registrar Dinheiro Sujo"):
    quantidade = TextInput(label="Valor (R$)", placeholder="Ex: 5000", required=True)
    membro = TextInput(label="Membro que recebeu o dinheiro (ID ou @)", placeholder="Ex: @usuario ou ID", required=True)
    produtos_devolvidos = TextInput(label="Produtos que ele devolveu (opcional)", placeholder="Ex: 5 relógios, 2 obras", required=False)

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
            valor = float(self.quantidade.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Valor inválido!", ephemeral=True)
            return
        membro_input = self.membro.value.strip()
        # tentar extrair ID
        import re
        ids = re.findall(r'\d+', membro_input)
        membro_id = int(ids[0]) if ids else None
        if not membro_id:
            await interaction.followup.send("Membro inválido! Use o ID ou menção.", ephemeral=True)
            return
        membro_obj = interaction.guild.get_member(membro_id)
        if not membro_obj:
            await interaction.followup.send("Membro não encontrado no servidor.", ephemeral=True)
            return
        produtos_dev = self.produtos_devolvidos.value.strip() or "Nenhum"

        await interaction.followup.send("📸 Agora envie a **print do comprovante** aqui no canal.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return
        imagem_url = msg.attachments[0].url

        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": []}
        if "transacoes_dinheiro_sujo" not in dados["usuarios"][str(self.user_id)]:
            dados["usuarios"][str(self.user_id)]["transacoes_dinheiro_sujo"] = []

        transacao = {
            "valor": valor,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "print_url": imagem_url,
            "registrado_por": interaction.user.id,
            "membro_recebedor": membro_id,
            "membro_nome": membro_obj.name,
            "produtos_devolvidos": produtos_dev
        }
        dados["usuarios"][str(self.user_id)]["transacoes_dinheiro_sujo"].append(transacao)
        dados["usuarios"][str(self.user_id)]["dinheiro_sujo"] = sum(t["valor"] for t in dados["usuarios"][str(self.user_id)]["transacoes_dinheiro_sujo"])
        salvar_dados()

        embed = discord.Embed(title="💰 DINHEIRO SUJO REGISTRADO", description=f"**Usuário:** <@{self.user_id}>\n**Valor:** R$ {valor:,.2f}\n**Membro que recebeu:** {membro_obj.mention}\n**Produtos devolvidos:** {produtos_dev}\n**Registrado por:** {interaction.user.mention}", color=0x4f545c, timestamp=datetime.now())
        embed.set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros:
            await canal_registros.send(embed=embed)
        await interaction.followup.send(f"R$ {valor:,.2f} registrado como dinheiro sujo para {self.user_name}!", ephemeral=True)
        await log_acao("registrar_dinheiro_sujo", interaction.user, f"Usuário: {self.user_name}\nValor: R$ {valor:,.2f}\nMembro: {membro_obj.name}", 0x4f545c)
        await atualizar_ranking()

class FarmProdutosModal(Modal, title="📦 Registrar Farm Produtos"):
    slot = TextInput(label="SLOT (número)", placeholder="Ex: 1, 2, 3...", required=True)
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
        # Primeiro, responder o modal com defer para não expirar
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
        slot_num = self.slot.value.strip()
        if not slot_num.isdigit():
            await interaction.followup.send("Slot deve ser um número!", ephemeral=True)
            return

        # Agora pedir a print
        await interaction.followup.send("📸 Agora envie a **print da farm** aqui no canal.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
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
        embed.add_field(name="📅 Data", value=datetime.now().strftime("%d/%m/%Y às %H:%M"), inline=False)
        embed.add_field(name="📦 Total de farms", value=f"{len(dados['usuarios'][str(self.user_id)]['farms'])} farms", inline=False)
        embed.set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros:
            await canal_registros.send(embed=embed)
        await interaction.followup.send(embed=embed, ephemeral=True)
        produtos_str = ', '.join(f"{p['produto']}: {p['quantidade']}" for p in produtos)
        await log_acao("registrar_farm", interaction.user, f"Produtos: {produtos_str} | Slot: {slot_num}")
        await log_admin("📦 NOVA FARM PRODUTOS", f"Usuário: {interaction.user.mention}\nProdutos: {produtos_str}\nSlot: {slot_num}", 0x2c2f33)
        await atualizar_ranking()

class PagamentoFarmModal(Modal, title="💵 Registrar Pagamento"):
    valor = TextInput(label="Valor do Pagamento (R$)", placeholder="Ex: 500", required=True)
    def __init__(self, user_id, user_name, canal):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores (cargo 00) podem registrar pagamentos.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            valor = float(self.valor.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Valor inválido!", ephemeral=True)
            return
        await interaction.followup.send("📸 Agora envie a **print do comprovante** aqui no canal.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": []}
        dados["usuarios"][str(self.user_id)]["pagamentos"].append({"valor": valor, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "admin": interaction.user.id, "admin_nome": interaction.user.name, "tipo": "Pagamento", "print_url": imagem_url})
        salvar_dados()
        try:
            user_dest = await bot.fetch_user(int(self.user_id))
            await user_dest.send(embed=discord.Embed(title="💸 PAGAMENTO RECEBIDO", description=f"Você recebeu R$ {valor:,.2f}!", color=0x2c2f33).set_image(url=imagem_url))
        except:
            pass
        embed = discord.Embed(title="💸 PAGAMENTO REGISTRADO", description=f"**Usuário:** <@{self.user_id}>\n**Valor:** R$ {valor:,.2f}\n**Admin:** {interaction.user.mention}", color=0x2c2f33, timestamp=datetime.now()).set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros:
            await canal_registros.send(embed=embed)
        await interaction.followup.send(f"Pagamento de R$ {valor:,.2f} registrado!", ephemeral=True)
        await log_acao("pagar", interaction.user, f"Usuário: {self.user_name}\nValor: R$ {valor:,.2f}", 0x99aab5)
        await atualizar_ranking()

class FechamentoSummaryView(View):
    def __init__(self, user_id, user_name, canal, total_sujo, lavagem, faccao, membro_base):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.total_sujo = total_sujo
        self.lavagem = lavagem
        self.faccao = faccao
        self.membro_base = membro_base
    @discord.ui.button(label="Continuar Fechamento", style=discord.ButtonStyle.success, emoji="✅")
    async def continuar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores (cargo 00)!", ephemeral=True)
            return
        modal = FechamentoCaixaModal(self.user_id, self.user_name, self.canal, self.total_sujo, self.lavagem, self.faccao, self.membro_base)
        await interaction.response.send_modal(modal)

class FechamentoCaixaModal(Modal, title="📊 Finalizar Fechamento"):
    meta_farm = TextInput(label="Meta de Farm (Sim/Não)", placeholder="Digite Sim ou Não", required=True)
    bonus = TextInput(label="Bônus (R$) - Opcional", placeholder="Ex: 500 (deixe 0 se não houver)", required=False, default="0")
    observacao = TextInput(label="💌 Observação (mensagem carinhosa)", placeholder="Deixe uma mensagem para o usuário...", required=False, style=discord.TextStyle.long)
    def __init__(self, user_id, user_name, canal, total_sujo, lavagem, faccao, membro_base):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.total_sujo = total_sujo
        self.lavagem = lavagem
        self.faccao = faccao
        self.membro_base = membro_base
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores (cargo 00)!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        meta = self.meta_farm.value.strip().lower()
        if meta not in ["sim", "não", "nao"]:
            await interaction.followup.send("Meta deve ser Sim/Não!", ephemeral=True)
            return
        meta = "Sim" if meta == "sim" else "Não"
        bonus_str = self.bonus.value.strip() or "0"
        try:
            bonus_valor = float(bonus_str.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Bônus inválido!", ephemeral=True)
            return
        obs = self.observacao.value.strip() if self.observacao.value else None
        pagamento_final = self.membro_base + bonus_valor
        await interaction.followup.send("📸 Agora envie a **print do comprovante** aqui no canal.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado!", ephemeral=True)
            return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": []}
        user_data = dados["usuarios"][str(self.user_id)]
        if pagamento_final > 0:
            user_data["pagamentos"].append({"valor": pagamento_final, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "admin": interaction.user.id, "admin_nome": interaction.user.name, "tipo": "Fechamento de Caixa Semanal", "detalhes": {"total_sujo": self.total_sujo, "lavagem": self.lavagem, "faccao": self.faccao, "membro_base": self.membro_base, "bonus": bonus_valor}, "print_url": imagem_url})
        # calcular totais de produtos (luxo)
        tot_relogio = sum(p.get("quantidade", 0) for f in user_data.get("farms", []) for p in f.get("produtos", []) if isinstance(p, dict) and p.get("produto") == "RELÓGIO DE LUXO")
        tot_obra = sum(p.get("quantidade", 0) for f in user_data.get("farms", []) for p in f.get("produtos", []) if isinstance(p, dict) and p.get("produto") == "OBRA DE ARTE")
        tot_bebida = sum(p.get("quantidade", 0) for f in user_data.get("farms", []) for p in f.get("produtos", []) if isinstance(p, dict) and p.get("produto") == "BEBIDA IMPORTADA")
        tot_acoes = sum(p.get("quantidade", 0) for f in user_data.get("farms", []) for p in f.get("produtos", []) if isinstance(p, dict) and p.get("produto") == "AÇÕES DE EMPRESA")
        tot_nft = sum(p.get("quantidade", 0) for f in user_data.get("farms", []) for p in f.get("produtos", []) if isinstance(p, dict) and p.get("produto") == "CARTEIRA NFT")

        fechamento = {
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.name,
            "admin_id": interaction.user.id,
            "usuario": self.user_name,
            "usuario_id": self.user_id,
            "meta_farm": meta,
            "produtos": {
                "relogio_luxo": tot_relogio,
                "obra_arte": tot_obra,
                "bebida_importada": tot_bebida,
                "acoes_empresa": tot_acoes,
                "carteira_nft": tot_nft
            },
            "dinheiro_sujo": {
                "total": self.total_sujo,
                "lavagem": self.lavagem,
                "faccao": self.faccao,
                "membro_base": self.membro_base,
                "bonus": bonus_valor,
                "pago": pagamento_final
            },
            "print_url": imagem_url,
            "observacao": obs
        }
        if str(self.user_id) not in dados["caixa_semana"]:
            dados["caixa_semana"][str(self.user_id)] = []
        dados["caixa_semana"][str(self.user_id)].append(fechamento)
        salvar_dados()
        embed = discord.Embed(title="📊 FECHAMENTO DE CAIXA SEMANAL", description=f"**{self.user_name}** fechou a semana!", color=0x99aab5, timestamp=datetime.now())
        embed.add_field(name="🎯 Meta de Farm", value=meta, inline=False)
        if any([tot_relogio > 0, tot_obra > 0, tot_bebida > 0, tot_acoes > 0, tot_nft > 0]):
            embed.add_field(name="📦 Produtos", value=f"⌚ Relógio Luxo: {tot_relogio}\n🖼️ Obra Arte: {tot_obra}\n🍷 Bebida Importada: {tot_bebida}\n📈 Ações: {tot_acoes}\n🖼️ NFT: {tot_nft}", inline=False)
        embed.add_field(name="💰 Total Farmado", value=f"R$ {self.total_sujo:,.2f}", inline=False)
        embed.add_field(name="🧼 Lavagem (25%)", value=f"R$ {self.lavagem:,.2f}", inline=True)
        embed.add_field(name="🏛️ Facção (60%)", value=f"R$ {self.faccao:,.2f}", inline=True)
        embed.add_field(name="🛡️ Membro Base (40%)", value=f"R$ {self.membro_base:,.2f}", inline=True)
        if bonus_valor > 0:
            embed.add_field(name="🎁 Bônus", value=f"R$ {bonus_valor:,.2f}", inline=True)
        embed.add_field(name="💵 Pagamento Final", value=f"R$ {pagamento_final:,.2f}", inline=False)
        embed.add_field(name="👤 Responsável", value=interaction.user.mention, inline=False)
        if obs:
            embed.add_field(name="💌 Mensagem", value=obs, inline=False)
        embed.set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros:
            await canal_registros.send(embed=embed)
        await interaction.followup.send(f"Pagamento de R$ {pagamento_final:,.2f} registrado!", ephemeral=True)
        await log_acao("fechar_caixa", interaction.user, f"Usuário: {self.user_name}\nPagamento: R$ {pagamento_final}", 0x99aab5)
        await atualizar_ranking()

# ========= EDIÇÃO (simplificada) =========
class EditarRegistroSelect(Select):
    def __init__(self, user_id, user_name):
        self.user_id = str(user_id)
        self.user_name = user_name
        user_data = dados["usuarios"].get(self.user_id, {})
        farms = user_data.get("farms", [])
        options = []
        for idx, farm in enumerate(farms):
            farm_id = farm.get("farm_id", idx + 1)
            if "slot" in farm:
                produtos_desc = ", ".join(f"{p['produto']}: {p['quantidade']}" for p in farm["produtos"])
                label = f"Farm #{farm_id} [Slot {farm['slot']}] - {produtos_desc}"
            else:
                produtos_desc = ", ".join(f"{p['produto']}: {p['quantidade']}" for p in farm["produtos"])
                label = f"Farm #{farm_id} - {produtos_desc}"
            description = f"Data: {farm['data']}"[:100]
            options.append(discord.SelectOption(label=label, description=description, value=str(idx)))
        if not options:
            options.append(discord.SelectOption(label="Nenhum registro encontrado", value="none", default=True))
        super().__init__(placeholder="Selecione o registro de farm...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("Nenhum registro de farm para editar.", ephemeral=True)
            return
        idx = int(self.values[0])
        user_data = dados["usuarios"].get(self.user_id)
        if not user_data or idx >= len(user_data["farms"]):
            await interaction.response.send_message("Registro não encontrado.", ephemeral=True)
            return
        farm = user_data["farms"][idx]
        modal = EditarFarmModal(self.user_id, self.user_name, interaction.channel, idx, farm)
        await interaction.response.send_modal(modal)

class EditarFarmModal(Modal, title="✏️ Editar Registro de Farm"):
    slot = TextInput(label="SLOT (número)", required=False)
    relogio = TextInput(label="RELÓGIO DE LUXO - Nova quantidade", required=False)
    obra = TextInput(label="OBRA DE ARTE - Nova quantidade", required=False)
    bebida = TextInput(label="BEBIDA IMPORTADA - Nova quantidade", required=False)
    acoes = TextInput(label="AÇÕES DE EMPRESA - Nova quantidade", required=False)
    nft = TextInput(label="CARTEIRA NFT - Nova quantidade", required=False)

    def __init__(self, user_id, user_name, canal, farm_index, farm_atual):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.farm_index = farm_index
        self.farm_atual = farm_atual
        if "slot" in farm_atual:
            self.slot.default = str(farm_atual.get("slot", ""))
        produtos_atuais = {p["produto"]: p["quantidade"] for p in farm_atual["produtos"]}
        self.relogio.default = str(produtos_atuais.get("RELÓGIO DE LUXO", ""))
        self.obra.default = str(produtos_atuais.get("OBRA DE ARTE", ""))
        self.bebida.default = str(produtos_atuais.get("BEBIDA IMPORTADA", ""))
        self.acoes.default = str(produtos_atuais.get("AÇÕES DE EMPRESA", ""))
        self.nft.default = str(produtos_atuais.get("CARTEIRA NFT", ""))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        novos_produtos = []
        for campo, nome in [(self.relogio, "RELÓGIO DE LUXO"), (self.obra, "OBRA DE ARTE"), (self.bebida, "BEBIDA IMPORTADA"), (self.acoes, "AÇÕES DE EMPRESA"), (self.nft, "CARTEIRA NFT")]:
            if campo.value and campo.value.strip():
                try:
                    qtd = int(campo.value.strip())
                    if qtd > 0:
                        novos_produtos.append({"produto": nome, "quantidade": qtd})
                except ValueError:
                    pass
        if not novos_produtos:
            await interaction.followup.send("Nenhum produto válido. Edição cancelada.", ephemeral=True)
            return
        slot_num = self.slot.value.strip() if self.slot.value else None
        if slot_num and not slot_num.isdigit():
            await interaction.followup.send("Slot deve ser um número!", ephemeral=True)
            return
        await interaction.followup.send("📸 Envie a **nova print** comprovando a edição.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado. Edição cancelada.", ephemeral=True)
            return
        nova_imagem_url = msg.attachments[0].url
        user_data = dados["usuarios"].get(self.user_id)
        if not user_data or self.farm_index >= len(user_data["farms"]):
            await interaction.followup.send("Registro não encontrado.", ephemeral=True)
            return
        antigo = user_data["farms"][self.farm_index]
        novo_registro = {
            "produtos": novos_produtos,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "print_url": nova_imagem_url,
            "validado": True,
            "farm_id": antigo.get("farm_id", self.farm_index + 1)
        }
        if slot_num:
            novo_registro["slot"] = int(slot_num)
        elif "slot" in antigo:
            novo_registro["slot"] = antigo["slot"]
        user_data["farms"][self.farm_index] = novo_registro
        salvar_dados()
        embed = discord.Embed(title="✏️ REGISTRO DE FARM EDITADO", description=f"**Usuário:** <@{self.user_id}>\n**Farm ID:** {novo_registro['farm_id']}", color=0x99aab5, timestamp=datetime.now())
        produtos_str = "\n".join(f"🔹 **{p['produto']}:** {p['quantidade']} itens" for p in novos_produtos)
        embed.add_field(name="📦 Novos valores", value=produtos_str, inline=False)
        embed.add_field(name="📅 Data da edição", value=novo_registro["data"], inline=False)
        embed.set_image(url=nova_imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros:
            await canal_registros.send(embed=embed)
        await interaction.followup.send(f"Registro #{novo_registro['farm_id']} editado com sucesso!", ephemeral=True)
        await log_acao("editar_farm", interaction.user, f"Usuário: {self.user_name}\nFarm ID: {novo_registro['farm_id']}\nNovos produtos: {produtos_str}", 0x99aab5)
        await atualizar_ranking()

class EditarDinheiroSujoSelect(Select):
    def __init__(self, user_id, user_name):
        self.user_id = str(user_id)
        self.user_name = user_name
        user_data = dados["usuarios"].get(self.user_id, {})
        transacoes = user_data.get("transacoes_dinheiro_sujo", [])
        options = []
        for idx, trans in enumerate(transacoes):
            valor = trans["valor"]
            data = trans["data"]
            label = f"R$ {valor:,.2f} - {data}"[:100]
            options.append(discord.SelectOption(label=label, value=str(idx)))
        if not options:
            options.append(discord.SelectOption(label="Nenhum depósito encontrado", value="none", default=True))
        super().__init__(placeholder="Escolha o depósito de dinheiro sujo...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("Nenhum depósito de dinheiro sujo para editar.", ephemeral=True)
            return
        idx = int(self.values[0])
        user_data = dados["usuarios"].get(self.user_id)
        if not user_data or idx >= len(user_data.get("transacoes_dinheiro_sujo", [])):
            await interaction.response.send_message("Registro não encontrado.", ephemeral=True)
            return
        trans = user_data["transacoes_dinheiro_sujo"][idx]
        modal = EditarDinheiroSujoModal(self.user_id, self.user_name, interaction.channel, idx, trans)
        await interaction.response.send_modal(modal)

class EditarDinheiroSujoModal(Modal, title="✏️ Editar Depósito de Dinheiro Sujo"):
    novo_valor = TextInput(label="Novo valor (R$)", placeholder="Ex: 5000", required=True)
    def __init__(self, user_id, user_name, canal, trans_index, trans_atual):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.trans_index = trans_index
        self.trans_atual = trans_atual
        self.novo_valor.default = str(trans_atual["valor"])
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            novo_valor = float(self.novo_valor.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Valor inválido.", ephemeral=True)
            return
        await interaction.followup.send("📸 Envie a **nova print** do comprovante.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado.", ephemeral=True)
            return
        nova_imagem_url = msg.attachments[0].url
        user_data = dados["usuarios"].get(self.user_id)
        if not user_data or self.trans_index >= len(user_data.get("transacoes_dinheiro_sujo", [])):
            await interaction.followup.send("Registro não encontrado.", ephemeral=True)
            return
        antiga = user_data["transacoes_dinheiro_sujo"][self.trans_index]
        nova_trans = {"valor": novo_valor, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "print_url": nova_imagem_url, "registrado_por": interaction.user.id}
        user_data["transacoes_dinheiro_sujo"][self.trans_index] = nova_trans
        user_data["dinheiro_sujo"] = sum(t["valor"] for t in user_data["transacoes_dinheiro_sujo"])
        salvar_dados()
        embed = discord.Embed(title="✏️ DEPÓSITO DE DINHEIRO SUJO EDITADO", description=f"**Usuário:** <@{self.user_id}>\n**Valor antigo:** R$ {antiga['valor']:,.2f}\n**Novo valor:** R$ {novo_valor:,.2f}", color=0x99aab5, timestamp=datetime.now())
        embed.add_field(name="📅 Data da edição", value=nova_trans["data"], inline=False)
        embed.set_image(url=nova_imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros:
            await canal_registros.send(embed=embed)
        await interaction.followup.send(f"Depósito editado! Novo valor: R$ {novo_valor:,.2f}", ephemeral=True)
        await log_acao("editar_dinheiro_sujo", interaction.user, f"Usuário: {self.user_name}\nNovo valor: R$ {novo_valor:,.2f}", 0x99aab5)
        await atualizar_ranking()

class EscolherTipoEdicaoView(View):
    def __init__(self, user_id, user_name):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.user_name = user_name
        self.add_item(TipoEdicaoSelect(user_id, user_name))

class TipoEdicaoSelect(Select):
    def __init__(self, user_id, user_name):
        self.user_id = str(user_id)
        self.user_name = user_name
        options = [
            discord.SelectOption(label="📦 Produtos", description="Editar um registro de farm (produtos de luxo)", value="produtos"),
            discord.SelectOption(label="💰 Dinheiro Sujo", description="Editar um depósito de dinheiro sujo", value="dinheiro_sujo")
        ]
        super().__init__(placeholder="O que você deseja editar?", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        tipo = self.values[0]
        if tipo == "produtos":
            select = EditarRegistroSelect(self.user_id, self.user_name)
            view = View(timeout=None)
            view.add_item(select)
            await interaction.response.send_message("Selecione o registro de farm que deseja editar:", view=view, ephemeral=True)
        else:
            select = EditarDinheiroSujoSelect(self.user_id, self.user_name)
            view = View(timeout=None)
            view.add_item(select)
            await interaction.response.send_message("Selecione o depósito de dinheiro sujo que deseja editar:", view=view, ephemeral=True)

async def enviar_historico_farms(interaction, user_id, user_name):
    user_data = dados["usuarios"].get(str(user_id), {})
    farms = user_data.get("farms", [])
    transacoes = user_data.get("transacoes_dinheiro_sujo", [])
    if not farms and not transacoes:
        await interaction.followup.send("Você ainda não tem nenhum registro (farm de produtos ou dinheiro sujo).", ephemeral=True)
        return
    embed = discord.Embed(title=f"📋 Histórico de Registros - {user_name}", color=0x2c2f33)
    todos = []
    for farm in farms:
        todos.append({"tipo": "farm", "data": farm["data"], "detalhes": farm})
    for trans in transacoes:
        todos.append({"tipo": "dinheiro_sujo", "data": trans["data"], "detalhes": trans})
    todos.sort(key=lambda x: x["data"], reverse=True)
    ultimos = todos[:10]
    for registro in ultimos:
        tipo = registro["tipo"]
        detalhes = registro["detalhes"]
        if tipo == "farm":
            farm_id = detalhes.get("farm_id", "?")
            slot_info = f" (Slot {detalhes['slot']})" if "slot" in detalhes else ""
            produtos_str = ", ".join(f"{p['produto']}: {p['quantidade']}" for p in detalhes["produtos"])
            print_url = detalhes.get("print_url", "")
            valor = f"**Farm #{farm_id}{slot_info}** - {produtos_str}"
            if print_url:
                valor += f"\n🖼️ [Ver print]({print_url})"
            embed.add_field(name=f"📦 Farm #{farm_id}{slot_info} ({registro['data']})", value=valor, inline=False)
        else:
            valor_ds = detalhes["valor"]
            print_url = detalhes.get("print_url", "")
            valor = f"💰 R$ {valor_ds:,.2f}"
            if print_url:
                valor += f"\n🖼️ [Ver print]({print_url})"
            embed.add_field(name=f"💵 Dinheiro Sujo ({registro['data']})", value=valor, inline=False)
    await interaction.followup.send(embed=embed, ephemeral=True)

class FarmChannelView(View):
    def __init__(self, user_id, user_name, canal_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.user_name = user_name
        self.canal_id = canal_id

    @discord.ui.button(label="📦 Farm Produtos", style=discord.ButtonStyle.secondary, emoji="📦", row=0)
    async def farm_produtos(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("Apenas o dono do canal!", ephemeral=True)
            return
        await interaction.response.send_modal(FarmProdutosModal(self.user_id, self.user_name, interaction.channel))

    @discord.ui.button(label="💰 Farm Dinheiro Sujo", style=discord.ButtonStyle.secondary, emoji="💰", row=0)
    async def farm_dinheiro_sujo(self, interaction: discord.Interaction, button: Button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Você não tem permissão para registrar dinheiro sujo.", ephemeral=True)
            return
        await interaction.response.send_modal(DinheiroSujoModal(self.user_id, self.user_name, interaction.channel))

    @discord.ui.button(label="✏️ Editar Registro", style=discord.ButtonStyle.secondary, emoji="✏️", row=0)
    async def editar_registro(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("Apenas o dono do canal ou admin pode editar.", ephemeral=True)
            return
        view = EscolherTipoEdicaoView(self.user_id, self.user_name)
        await interaction.response.send_message("Escolha o tipo de registro que deseja editar:", view=view, ephemeral=True)

    @discord.ui.button(label="📊 Fechar Caixa", style=discord.ButtonStyle.secondary, emoji="📊", row=1)
    async def fechar_caixa(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores (cargo 00)!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        user_data = dados["usuarios"].get(str(self.user_id), {})
        total_sujo = user_data.get("dinheiro_sujo", 0.0)
        if total_sujo <= 0:
            await interaction.followup.send("Nenhum dinheiro sujo acumulado.", ephemeral=True)
            return
        lavagem = total_sujo * 0.25
        restante = total_sujo - lavagem
        faccao = restante * 0.60
        membro_base = restante * 0.40
        embed = discord.Embed(title="📊 RESUMO DO FECHAMENTO", color=0x99aab5)
        embed.add_field(name="💰 Total Farmado", value=f"R$ {total_sujo:,.2f}", inline=False)
        embed.add_field(name="🧼 Lavagem (25%)", value=f"R$ {lavagem:,.2f}", inline=True)
        embed.add_field(name="🏛️ Facção (60% do restante)", value=f"R$ {faccao:,.2f}", inline=True)
        embed.add_field(name="🛡️ Membro Base (40%)", value=f"R$ {membro_base:,.2f}", inline=True)
        embed.set_footer(text="Clique no botão abaixo para continuar.")
        view = FechamentoSummaryView(self.user_id, self.user_name, interaction.channel, total_sujo, lavagem, faccao, membro_base)
        await interaction.followup.send(embed=embed, view=view, ephemeral=False)

    @discord.ui.button(label="✏️ Mudar Nome", style=discord.ButtonStyle.secondary, emoji="✏️", row=1)
    async def mudar_nome(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores (cargo 00)!", ephemeral=True)
            return
        await interaction.response.send_modal(MudarNomeModal(interaction.channel))

    @discord.ui.button(label="📜 Histórico Caixa", style=discord.ButtonStyle.secondary, emoji="📜", row=1)
    async def historico_caixa(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores (cargo 00)!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        fechamentos = dados["caixa_semana"].get(str(self.user_id), [])
        if not fechamentos:
            await interaction.followup.send("Nenhum fechamento.", ephemeral=True)
            return
        embed = discord.Embed(title="📜 HISTÓRICO DE CAIXA", description=f"Últimos {min(10, len(fechamentos))} registros", color=0x2c2f33)
        for fech in fechamentos[-10:]:
            data = datetime.strptime(fech["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
            txt = f"Meta: {fech.get('meta_farm', '?')}\n"
            if "produtos" in fech:
                p = fech["produtos"]
                txt += f"Relógio: {p.get('relogio_luxo', 0)} | Obra: {p.get('obra_arte', 0)} | Bebida: {p.get('bebida_importada', 0)} | Ações: {p.get('acoes_empresa', 0)} | NFT: {p.get('carteira_nft', 0)}\n"
            if "dinheiro_sujo" in fech:
                ds = fech["dinheiro_sujo"]
                txt += f"Farm Sujo: R$ {ds['total']:,.2f}\nLavagem: R$ {ds['lavagem']:,.2f}\nFacção: R$ {ds['faccao']:,.2f}\nMembro Base: R$ {ds['membro_base']:,.2f}"
                if ds.get('bonus', 0) > 0:
                    txt += f"\nBônus: R$ {ds['bonus']:,.2f}"
                    txt += f"\n**Pago: R$ {ds['pago']:,.2f}**"
            if fech.get('observacao'):
                txt += f"\n💌 {fech['observacao']}"
            embed.add_field(name=f"📅 {data}", value=txt, inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="📋 Meus Registros", style=discord.ButtonStyle.primary, emoji="📋", row=2)
    async def meus_registros(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        await enviar_historico_farms(interaction, self.user_id, self.user_name)

    @discord.ui.button(label="🔄 Reset Semanal", style=discord.ButtonStyle.danger, emoji="🔄", row=2)
    async def reset_semanal(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores (cargo 00)!", ephemeral=True)
            return
        confirm_view = ConfirmResetSemanalView(self.user_id, self.user_name, interaction.channel)
        await interaction.response.send_message("⚠️ **Tem certeza que deseja resetar a semana?**", view=confirm_view, ephemeral=True)

    @discord.ui.button(label="🗑️ Fechar Canal", style=discord.ButtonStyle.danger, emoji="🗑️", row=2)
    async def fechar_canal(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores (cargo 00)!", ephemeral=True)
            return
        await interaction.response.send_message("⚠️ Tem certeza?", view=ConfirmarFechamentoView(self.user_id, interaction.channel), ephemeral=True)

class ConfirmResetSemanalView(View):
    def __init__(self, user_id, user_name, canal):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
    @discord.ui.button(label="Sim, resetar semana", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if str(self.user_id) in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)]["farms"] = []
            dados["usuarios"][str(self.user_id)]["pagamentos"] = []
            dados["usuarios"][str(self.user_id)]["dinheiro_sujo"] = 0.0
            dados["usuarios"][str(self.user_id)]["transacoes_dinheiro_sujo"] = []
            salvar_dados()
        await interaction.followup.send("✅ Semana resetada com sucesso!", ephemeral=True)
        await log_admin("🔄 RESET SEMANAL", f"Usuário: {self.user_name}\nAdmin: {interaction.user.mention}", 0x99aab5)
        await atualizar_ranking()
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Reset cancelado.", ephemeral=True)

class ConfirmarFechamentoView(View):
    def __init__(self, user_id, canal):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.canal = canal
    @discord.ui.button(label="Sim, fechar", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores (cargo 00)!", ephemeral=True)
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

class MudarNomeModal(Modal, title="✏️ Mudar Nome do Canal"):
    novo_nome = TextInput(label="Novo nome", placeholder="Ex: farm-lucas", required=True, max_length=90)
    def __init__(self, canal):
        super().__init__()
        self.canal = canal
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores (cargo 00)!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        nome = ''.join(c for c in self.novo_nome.value.lower().replace(" ", "-") if c.isalnum() or c == '-') or "farm"
        try:
            await self.canal.edit(name=nome)
            await interaction.followup.send(f"Nome alterado para {nome}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Erro: {str(e)[:100]}", ephemeral=True)

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
    @discord.ui.button(label="📋 Listar Pedidos", style=discord.ButtonStyle.secondary, emoji="📋")
    async def listar_pedidos(self, interaction: discord.Interaction, button: Button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        pedidos = dados["pedidos"]["lista"]
        if not pedidos:
            await interaction.followup.send("Nenhum pedido registrado.", ephemeral=True)
            return
        embed = discord.Embed(title="📋 LISTA DE PEDIDOS", color=0x2c2f33)
        for p in pedidos[-10:]:
            status = "✅ Pago" if p.get("pago") else "⏳ Pendente" if p.get("descontado_caixa") == "Pendente" else "💰 Descontado do Caixa" if p.get("descontado_caixa") == "Sim" else "❌ Não descontado"
            valor_str = f"R$ {p['valor_total']:,.2f}"
            embed.add_field(name=f"{p['cliente']} - {valor_str}", value=f"Prazo: {p['prazo_entrega']}\nStatus: {status}", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
    @discord.ui.button(label="⚙️ Editar Porcentagens", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def editar_porcentagens(self, interaction: discord.Interaction, button: Button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("Apenas cargos 00,01,02 ou Gerente podem editar porcentagens.", ephemeral=True)
            return
        await interaction.response.send_modal(EditarPorcentagensModal())

class NovoPedidoModal(Modal, title="📝 Novo Pedido"):
    cliente = TextInput(label="Nome do Cliente", placeholder="Ex: João Silva", required=True)
    valor_total = TextInput(label="Valor Total Sujo (R$)", placeholder="Ex: 10000", required=True)
    prazo_entrega = TextInput(label="Prazo de Entrega", placeholder="Ex: 25/12/2025", required=True)
    descontado_caixa = TextInput(label="Descontado do Caixa? (Sim/Não/Pendente)", placeholder="Sim, Não ou Pendente", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            valor = float(self.valor_total.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Valor inválido!", ephemeral=True)
            return
        prazo = self.prazo_entrega.value.strip()
        descontado = self.descontado_caixa.value.strip().capitalize()
        if descontado not in ["Sim", "Não", "Pendente"]:
            await interaction.followup.send("Descontado do Caixa deve ser Sim, Não ou Pendente.", ephemeral=True)
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
            "prazo_entrega": prazo,
            "descontado_caixa": descontado,
            "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "criado_por": interaction.user.id,
            "distribuicao": {
                "cliente": cliente_part,
                "maquina": maquina_part,
                "fac": fac_part,
                "membros": membros_part
            },
            "pago": False
        }
        dados["pedidos"]["lista"].append(pedido)
        salvar_dados()
        canal_log = bot.get_channel(CHAT_PEDIDOS_LOG_ID) if CHAT_PEDIDOS_LOG_ID else None
        embed = discord.Embed(title="📝 NOVO PEDIDO CRIADO", color=0x2c2f33, timestamp=datetime.now())
        embed.add_field(name="Cliente", value=pedido["cliente"], inline=True)
        embed.add_field(name="Valor Total", value=f"R$ {valor:,.2f}", inline=True)
        embed.add_field(name="Prazo", value=prazo, inline=True)
        embed.add_field(name="Descontado Caixa", value=descontado, inline=True)
        embed.add_field(name="Distribuição (50/40/5/5)", value=f"Cliente: R$ {cliente_part:,.2f}\nMáquina: R$ {maquina_part:,.2f}\nFacção: R$ {fac_part:,.2f}\nMembros: R$ {membros_part:,.2f}", inline=False)
        embed.set_footer(text=f"Criado por {interaction.user.name}")
        if canal_log:
            await canal_log.send(embed=embed)
        await interaction.followup.send(f"✅ Pedido #{pedido['id']} criado para **{pedido['cliente']}**!", ephemeral=True)

class EditarPorcentagensModal(Modal, title="⚙️ Editar Porcentagens"):
    cliente = TextInput(label="% Cliente", placeholder="Ex: 50", required=True)
    maquina = TextInput(label="% Máquina", placeholder="Ex: 40", required=True)
    fac = TextInput(label="% Facção", placeholder="Ex: 5", required=True)
    membros = TextInput(label="% Membros", placeholder="Ex: 5", required=True)
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
            total = sum(pcts.values())
            if abs(total - 100) > 0.01:
                await interaction.response.send_message(f"A soma das porcentagens deve ser 100% (atual: {total}%).", ephemeral=True)
                return
            dados["pedidos"]["config"]["porcentagens"] = pcts
            dados["pedidos"]["config"]["ultima_edicao"] = {
                "por": interaction.user.id,
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            salvar_dados()
            await interaction.response.send_message(f"✅ Porcentagens atualizadas para: Cliente {pcts['cliente']}% / Máquina {pcts['maquina']}% / Facção {pcts['fac']}% / Membros {pcts['membros']}%", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Valores inválidos.", ephemeral=True)

# ========= REMOÇÃO DE MEMBRO =========
class RemoverUsuarioModal(Modal, title="🗑️ Remover Usuário"):
    user_id = TextInput(label="ID do usuário", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not pode_remover_membro(interaction.user):
            await interaction.response.send_message("Você não tem permissão para remover membros. Apenas Líder (00), 01, 02 ou Gerente.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            uid = int(self.user_id.value.strip())
            user = await interaction.client.fetch_user(uid)
            if str(uid) in dados["usuarios_banidos"]:
                await interaction.followup.send("Usuário já removido!", ephemeral=True)
                return
            total = await limpar_logs_usuario(uid, user.name)
            await interaction.followup.send(f"✅ {user.mention} removido! Limpas: {total}", ephemeral=True)
            await log_admin("🗑️ USUÁRIO REMOVIDO", f"{user.mention} por {interaction.user.mention}", 0x4f545c)
            await atualizar_ranking()
        except Exception as e:
            await interaction.followup.send(f"Erro: {e}", ephemeral=True)

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
            tipo = "ADMIN" if is_admin(interaction.user) else "MEMBRO"
            embed = discord.Embed(
                title="🔐 SEU CANAL PRIVADO",
                description=f"Bem-vindo(a) {interaction.user.mention}!\n\n🔒 Apenas você e administradores têm acesso.\n\n**BOTÕES DISPONÍVEIS PARA {tipo}:**\n📦 **Farm Produtos** - Registrar farm de produtos (com print)\n💰 **Farm Dinheiro Sujo** - Registrar dinheiro sujo (com print)\n✏️ **Editar Registro** - Corrigir um registro\n📋 **Meus Registros** - Ver histórico completo",
                color=0x2c2f33
            )
            if tipo == "ADMIN":
                embed.description += "\n\n**BOTÕES ADMINISTRATIVOS:**\n📊 **Fechar Caixa** - Fechar caixa semanal\n✏️ **Mudar Nome** - Renomear canal\n📜 **Histórico Caixa** - Ver fechamentos\n🔄 **Reset Semanal** - Limpar dados da semana\n🗑️ **Fechar Canal** - Deletar canal"
            await canal.send(embed=embed, view=view)
            await log_acao("criar_canal", interaction.user, f"Canal criado: {canal.mention}", 0x2c2f33)
            await interaction.followup.send(f"✅ Canal criado! Acesse: {canal.mention}", ephemeral=True)
            await atualizar_ranking()
        except Exception as e:
            await interaction.followup.send(f"Erro: {str(e)[:200]}", ephemeral=True)

# ========= EVENTOS =========
@bot.event
async def on_member_remove(member):
    if str(member.id) in dados["usuarios_banidos"]:
        return
    await log_admin("👋 USUÁRIO SAIU", f"{member.mention} saiu. Iniciando limpeza...")
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
    await log_admin("🧹 LIMPEZA CONCLUÍDA", f"{member.mention} removido do sistema.")

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} online!")

    for guild in bot.guilds:
        # Painel de criação de canal (farm)
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
                description="Clique no botão abaixo para criar seu canal privado!\n\n🔒 Apenas você e os administradores terão acesso.",
                color=0x2c2f33
            )
            await canal_criar.send(embed=embed_criar, view=BotaoCriarCanalView())

        # Painel de SET
        canal_set = guild.get_channel(CANAL_SOLICITAR_SET_ID)
        if canal_set:
            async for msg in canal_set.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            embed_set = discord.Embed(
                title="📋 SOLICITAR SET",
                description="Clique no botão abaixo para solicitar seu SET (recrutamento).\n\nPreencha o formulário e aguarde a aprovação de um administrador (cargos 00,01,02 ou Gerente).",
                color=0x2c2f33
            )
            view = View(timeout=None)
            button = Button(label="📝 Solicitar SET", style=discord.ButtonStyle.success, emoji="📝", custom_id="solicitar_set")
            async def button_callback(interaction):
                await interaction.response.send_modal(SolicitarSetModal())
            button.callback = button_callback
            view.add_item(button)
            await canal_set.send(embed=embed_set, view=view)

        # Painel de Pedidos na categoria específica
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
                description="Gerencie pedidos de clientes. As porcentagens padrão são: Cliente 50%, Máquina 40%, Facção 5%, Membros 5%.\n\nApenas cargos 00,01,02 e Gerente podem criar e editar.",
                color=0x2c2f33
            )
            await canal_pedidos.send(embed=embed_pedidos, view=PedidoView())

        # Botão de remover membro (adicionei no mesmo canal de criar-canal ou em outro lugar? Vou colocar no canal de criar-canal como um botão extra)
        if categoria_painel:
            # Vamos adicionar um segundo embed com botão de remover membro no mesmo canal "criar-canal"
            canal_criar = discord.utils.get(categoria_painel.channels, name="criar-canal")
            if canal_criar:
                # Verificar se já existe mensagem com botão de remover
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
                            await interaction.response.send_message("Você não tem permissão para remover membros. Apenas Líder (00), 01, 02 ou Gerente.", ephemeral=True)
                            return
                        await interaction.response.send_modal(RemoverUsuarioModal())
                    remove_button.callback = remove_callback
                    view_remove.add_item(remove_button)
                    embed_remove = discord.Embed(
                        title="🗑️ REMOVER MEMBRO",
                        description="Caso precise remover um membro do sistema (apagar registros e canal privado), utilize o botão abaixo.\n\n**Permissões:** Cargos 00, 01, 02 e Gerente.",
                        color=0x4f545c
                    )
                    await canal_criar.send(embed=embed_remove, view=view_remove)

    # Restaurar views dos canais privados existentes
    await restaurar_canais_farms()

    await atualizar_ranking()
    await log_admin("🤖 BOT INICIADO", f"Bot {bot.user.mention} online!", 0x2c2f33)

if __name__ == "__main__":
    carregar_dados()
    bot.run(TOKEN)
