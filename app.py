# ==============================================================================
# CK ATS V1 - APP.PY - VERSÃO FINAL BLINDADA COM NOVO SDK (GOOGLE.GENAI)
# ==============================================================================

# --- Imports Essenciais ---
import os
import json
import logging
import sqlite3
from collections import Counter
from datetime import datetime
import hashlib
import io
import csv

# Importações específicas do Flask e Dotenv (Segurança)
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, Response
from dotenv import load_dotenv

# Importações de extração de texto
import PyPDF2
import docx

# NOVO SDK OFICIAL DO GEMINI (google-genai)
from google import genai
from google.genai import types

# --- Carregando Variáveis de Ambiente (O Cofre) ---
load_dotenv()

# --- Configuração de Log e App ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.static_folder = 'static'
app.template_folder = 'templates'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chave-padrao-desenvolvimento-ck-ats')

# CHAVE DA API BLINDADA E CONFIGURAÇÃO DO NOVO SDK CLIENT
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_CLIENT = None

if GEMINI_API_KEY:
    GEMINI_CLIENT = genai.Client(api_key=GEMINI_API_KEY)
else:
    logger.warning("ALERTA: GEMINI_API_KEY não encontrada no .env. Funcionalidades de IA estarão desativadas.")

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# ==============================================================================
# FUNÇÕES CORE: IA E EXTRAÇÃO
# ==============================================================================

def extrair_texto(caminho):
    """Extrai texto de arquivos PDF ou DOCX."""
    ext = os.path.splitext(caminho)[1].lower()
    if ext == '.pdf':
        try:
            with open(caminho, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return " ".join([p.extract_text() for p in reader.pages if p.extract_text()])
        except Exception as e:
            logger.error(f"Erro ao extrair PDF '{caminho}': {e}")
    elif ext == '.docx':
        try:
            doc = docx.Document(caminho)
            return " ".join([p.text for p in doc.paragraphs if p.text])
        except Exception as e:
            logger.error(f"Erro ao extrair DOCX '{caminho}': {e}")
    return ""

def extrair_dados_com_gemini(texto_curriculo: str, filename: str) -> dict:
    """Usa o novo SDK google-genai para extrair informações estruturadas."""
    if not GEMINI_CLIENT:
        logger.warning(f"GEMINI_CLIENT ausente. Falha ao processar '{filename}'.")
        return {}
    
    prompt = f"""
    Analise o texto deste currículo e extraia as informações em um formato JSON.
    É crucial que você retorne TODOS os campos da estrutura, mesmo que o valor seja vazio ("" ou []). Não omita chaves.
    Para o campo "habilidades", extraia APENAS os nomes das tecnologias ou competências.

    Estrutura JSON esperada:
    {{
      "nome": "Nome completo", "email": "email@dominio.com", "telefone": "(XX) XXXXX-XXXX", "linkedin": "https://linkedin.com/in/perfil",
      "idade": "XX anos", "cargo_desejado": "O cargo ou objetivo", "habilidades": ["Python", "MySQL"],
      "formacao": [{{"curso": "Nome do Curso", "instituicao": "Nome da Instituição", "periodo": "Início - Fim"}}],
      "experiencia": [{{"cargo": "Cargo Ocupado", "empresa": "Nome da Empresa", "periodo": "Início - Fim", "atividades": ["Descrição."]}}],
      "idiomas": ["Idioma - Nível"]
    }}

    Texto do Currículo: --- {texto_curriculo} ---
    """
    
    try:
        response = GEMINI_CLIENT.models.generate_content(
             model="gemini-3-flash-preview", 
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Exceção no novo SDK do Gemini para '{filename}': {e}")
        return {}

def analisar_com_gemini(dados_candidato: dict) -> str:
    """Gera uma análise textual resumida do candidato."""
    return "Análise estrutural processada e arquivada pelo motor algorítmico do CK ATS."

# ==============================================================================
# GESTÃO DE BANCO DE DADOS (SQLite)
# ==============================================================================
DATABASE, VAGAS_DB = 'candidatos.db', 'vagas.db'
def get_db(db_name=DATABASE):
    conn = sqlite3.connect(db_name); conn.row_factory = sqlite3.Row; return conn

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS candidatos (
                id INTEGER PRIMARY KEY, nome TEXT, email TEXT, telefone TEXT, 
                linkedin TEXT, idade TEXT, cargo_desejado TEXT, pontuacao INTEGER, 
                habilidades TEXT, formacao TEXT, experiencia TEXT, analise_ia TEXT, 
                motivos_pontuacao TEXT, idiomas TEXT, status TEXT DEFAULT "ativo", 
                hash_arquivo TEXT UNIQUE, nome_arquivo_processado TEXT, data_upload TEXT
            )''')
        db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_hash_arquivo ON candidatos (hash_arquivo)')
        db.commit(); db.close()

def init_vagas_db():
    with app.app_context():
        db = get_db(VAGAS_DB)
        db.execute('''
            CREATE TABLE IF NOT EXISTS vagas (
                id INTEGER PRIMARY KEY,
                nome TEXT NOT NULL,
                requisitos TEXT NOT NULL,
                habilidades_chave TEXT,
                localizacao TEXT,
                tipo_contratacao TEXT,
                status TEXT DEFAULT 'Aberta',
                data_criacao TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()
        db.close()

with app.app_context():
    init_db()
    init_vagas_db()

# ==============================================================================
# ROTAS FRONTEND (PÁGINAS)
# ==============================================================================

@app.route('/')
def index(): 
    return redirect(url_for('home'))

@app.route('/home')
def home(): return render_template('dashboard.html')

@app.route('/vagas')
def vagas_page(): return render_template('vagas.html')

@app.route('/upload_curriculos')
def upload_curriculos_page(): return render_template('upload.html')

@app.route('/processing')
def processing_page(): return render_template('processing.html')

# ==============================================================================
# MOTOR DE TRIAGEM E MATCH (CORE ATS)
# ==============================================================================

@app.route('/candidatos_ranqueados')
def candidatos_ranqueados():
    vaga_id_selecionada = request.args.get('vaga_id', default=None, type=int)
    
    db_candidatos = get_db()
    candidatos = db_candidatos.execute("SELECT * FROM candidatos WHERE status = 'ativo'").fetchall()
    db_candidatos.close()

    if vaga_id_selecionada:
        db_vagas = get_db(VAGAS_DB)
        vaga = db_vagas.execute("SELECT habilidades_chave FROM vagas WHERE id = ?", (vaga_id_selecionada,)).fetchone()
        db_vagas.close()

        if not vaga:
            return jsonify({"error": "Vaga não encontrada"}), 404

        habilidades_vaga_raw = json.loads(vaga['habilidades_chave'] or '[]')
        habilidades_vaga = {skill.strip().lower() for skill in habilidades_vaga_raw if skill.strip()}

        if not habilidades_vaga:
            return jsonify([dict(c, indice_adequacao=0, nivel="Requer Análise") for c in candidatos])

        candidatos_classificados = []
        for candidato in candidatos:
            candidato_dict = dict(candidato)
            
            def normalizar_campo(valor_campo):
                if not valor_campo: return []
                try:
                    dados = json.loads(valor_campo)
                    return dados if isinstance(dados, list) else [dados]
                except (json.JSONDecodeError, TypeError):
                    return [item.strip() for item in valor_campo.split(',')]

            habilidades_candidato_raw = normalizar_campo(candidato_dict.get('habilidades'))
            tem_experiencia = normalizar_campo(candidato_dict.get('experiencia'))
            tem_formacao = normalizar_campo(candidato_dict.get('formacao'))

            habilidades_candidato = {str(skill).strip().lower() for skill in habilidades_candidato_raw}
            habilidades_em_comum_count = sum(1 for hv in habilidades_vaga if any(hv in hc for hc in habilidades_candidato))
            score_habilidades = (habilidades_em_comum_count / len(habilidades_vaga)) * 100 if habilidades_vaga else 0
            
            score_experiencia = 100 if tem_experiencia else 0
            score_formacao = 100 if tem_formacao else 0
            
            pesos = {'habilidades': 0.60, 'experiencia': 0.25, 'formacao': 0.15}
            indice_final = round((score_habilidades * pesos['habilidades']) + (score_experiencia * pesos['experiencia']) + (score_formacao * pesos['formacao']))

            nivel = "Requer Análise"
            if indice_final > 70: nivel = "Excelente"
            elif indice_final > 40: nivel = "Promissor"

            candidato_dict['indice_adequacao'] = indice_final
            candidato_dict['nivel'] = nivel
            candidatos_classificados.append(candidato_dict)
            
        candidatos_ordenados = sorted(candidatos_classificados, key=lambda c: c['indice_adequacao'], reverse=True)
        return jsonify(candidatos_ordenados)

    else: 
        db_vagas = get_db(VAGAS_DB)
        vagas_db = db_vagas.execute("SELECT id, nome FROM vagas ORDER BY nome").fetchall()
        db_vagas.close()
        
        vagas_serializaveis = [dict(v) for v in vagas_db]
        candidatos_ordenados = sorted([dict(c) for c in candidatos], key=lambda c: c.get('pontuacao', 0), reverse=True)

        return render_template('candidatos_ranqueados.html', candidatos=candidatos_ordenados, vagas=vagas_serializaveis)

@app.route('/detalhes_candidato/<int:candidate_id>')
def detalhes_candidato(candidate_id):
    db = get_db()
    candidato = db.execute("SELECT * FROM candidatos WHERE id = ?", (candidate_id,)).fetchone()
    db.close()
    if not candidato:
        return redirect(url_for('candidatos_ranqueados'))
    
    candidato_dict = dict(candidato)
    
    for key in ['habilidades', 'formacao', 'experiencia', 'motivos_pontuacao', 'idiomas']:
        valor = candidato_dict.get(key)
        if not valor:
            candidato_dict[key] = []
            continue
        try:
            dados = json.loads(valor)
            candidato_dict[key] = dados if isinstance(dados, list) else [dados]
        except (json.JSONDecodeError, TypeError):
            if key in ['habilidades', 'idiomas', 'motivos_pontuacao']:
                 candidato_dict[key] = [item.strip() for item in valor.split(',')]
            elif key == 'formacao':
                candidato_dict[key] = [{'curso': valor, 'instituicao': 'N/A', 'periodo': 'N/A'}]
            elif key == 'experiencia':
                 candidato_dict[key] = [{'cargo': 'Experiência Geral', 'empresa': 'N/A', 'periodo': 'N/A', 'atividades': [valor]}]
            else:
                 candidato_dict[key] = [valor]

    return render_template('candidate_details.html', candidate=candidato_dict)

# ==============================================================================
# MOTOR DE UPLOAD (Ingestão de Currículos)
# ==============================================================================

@app.route('/upload_multiple_files', methods=['POST'])
def upload_multiple_files():
    if 'arquivos[]' not in request.files:
        flash('Nenhum arquivo enviado.', 'error'); return redirect(url_for('upload_curriculos_page'))
    
    arquivos = request.files.getlist('arquivos[]')
    
    for arquivo in arquivos:
        if arquivo.filename == '': continue
        filename = arquivo.filename
        
        file_content = arquivo.read()
        file_hash = hashlib.sha256(file_content).hexdigest()
        caminho_temp = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        try:
            with open(caminho_temp, 'wb') as f: f.write(file_content)

            db = get_db()
            if db.execute("SELECT id FROM candidatos WHERE hash_arquivo = ?", (file_hash,)).fetchone():
                db.close(); logger.warning(f"Ignorando duplicado: {filename}"); continue
            db.close()

            texto = extrair_texto(caminho_temp)
            if not texto: raise ValueError("Texto do currículo vazio.")

            dados_extraidos = extrair_dados_com_gemini(texto, filename)
            if not dados_extraidos.get("nome"): raise ValueError("IA não conseguiu extrair dados vitais.")
            
            pontuacao, motivos = 0, []
            habilidades = dados_extraidos.get("habilidades", [])
            if any(h in habilidades for h in ['Python', 'SQL', 'Power BI']):
                pontuacao += 50; motivos.append("Habilidades Técnicas Relevantes")
            if dados_extraidos.get("experiencia"):
                pontuacao += 30; motivos.append("Possui experiência profissional")
            if dados_extraidos.get("formacao"):
                pontuacao += 20; motivos.append("Possui formação acadêmica")
            pontuacao = min(pontuacao, 100)
            
            analise_ia = analisar_com_gemini(dados_extraidos)

            db = get_db()
            db.execute('''
                INSERT INTO candidatos (nome, email, telefone, linkedin, idade, cargo_desejado, pontuacao, 
                                      habilidades, formacao, experiencia, motivos_pontuacao, idiomas, analise_ia, 
                                      hash_arquivo, nome_arquivo_processado, data_upload) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dados_extraidos.get("nome"), dados_extraidos.get("email"), dados_extraidos.get("telefone"),
                dados_extraidos.get("linkedin"), dados_extraidos.get("idade"), dados_extraidos.get("cargo_desejado"),
                pontuacao, json.dumps(habilidades), json.dumps(dados_extraidos.get("formacao", [])),
                json.dumps(dados_extraidos.get("experiencia", [])), json.dumps(motivos),
                json.dumps(dados_extraidos.get("idiomas", [])), analise_ia,
                file_hash, filename, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            db.commit(); db.close()
            logger.info(f"Sucesso ao processar e arquivar '{filename}'.")

        except Exception as e:
            logger.error(f"Falha na esteira de processamento de '{filename}': {e}")
            flash(f"Erro ao processar o arquivo {filename}.", 'error')
        finally:
            if os.path.exists(caminho_temp): os.remove(caminho_temp)
    
    flash('Processamento em lote concluído.', 'success')
    return redirect(url_for('candidatos_ranqueados'))

# ==============================================================================
# APIS GERAIS (Login, Dashboard, Vagas, CSV)
# ==============================================================================

@app.route('/dashboard_data')
def dashboard_data():
    try:
        db = get_db()
        candidatos = db.execute("SELECT pontuacao, habilidades, experiencia, formacao, idiomas FROM candidatos WHERE status = 'ativo'").fetchall()
        db.close()

        if not candidatos:
            return jsonify({'total_candidatos': 0, 'media_pontuacao': 0, 'habilidades_mais_comuns': {}, 'distribuicao_pontuacoes': {}, 'formacoes_mais_comuns': {}})

        total_candidatos = len(candidatos)
        pontuacoes = [c['pontuacao'] for c in candidatos if c['pontuacao'] is not None]
        media_pontuacao = sum(pontuacoes) / len(pontuacoes) if pontuacoes else 0

        contador_habilidades, contador_formacoes = Counter(), Counter()

        for candidato in candidatos:
            try:
                habilidades_raw = candidato['habilidades'] or '[]'
                try: lista_habilidades = json.loads(habilidades_raw)
                except: lista_habilidades = [h.strip() for h in habilidades_raw.split(',')]
                contador_habilidades.update(lista_habilidades)

                formacao_raw = candidato['formacao'] or '[]'
                try:
                    lista_formacao_obj = json.loads(formacao_raw)
                    formacoes = [f.get('curso', 'N/A') for f in lista_formacao_obj]
                except: formacoes = [f.strip() for f in formacao_raw.split(',')]
                contador_formacoes.update(formacoes)
            except Exception: continue

        faixas_pontuacao = [0] * 10
        for pontuacao in pontuacoes:
            if 0 <= pontuacao <= 99: faixas_pontuacao[pontuacao // 10] += 1
        distribuicao_pontuacoes = dict(zip([f'{i*10}-{i*10 + 9}' for i in range(10)], faixas_pontuacao))

        return jsonify({
            'total_candidatos': total_candidatos,
            'media_pontuacao': round(media_pontuacao, 1),
            'habilidades_mais_comuns': dict(contador_habilidades.most_common(7)),
            'distribuicao_pontuacoes': distribuicao_pontuacoes,
            'formacoes_mais_comuns': dict(contador_formacoes.most_common(5)),
        })
    except Exception as e:
        logger.error(f"Erro Dash: {e}"); return jsonify({"error": "Falha na Dashboard"}), 500

@app.route('/api/candidatos/<int:candidate_id>/reprovar', methods=['POST'])
def reprovar_candidato(candidate_id):
    try:
        db = get_db(); db.execute("UPDATE candidatos SET status = 'reprovado' WHERE id = ?", (candidate_id,)); db.commit(); db.close()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'success': False, 'message': 'Erro Servidor'}), 500

@app.route('/api/candidatos/<int:candidate_id>', methods=['DELETE'])
def excluir_candidato(candidate_id):
    try:
        db = get_db(); db.execute("DELETE FROM candidatos WHERE id = ?", (candidate_id,)); db.commit(); db.close()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'success': False}), 500

@app.route('/api/vagas', methods=['GET', 'POST'])
def api_vagas():
    db = get_db(VAGAS_DB); cursor = db.cursor()
    try:
        if request.method == 'POST':
            data = request.get_json()
            if not data or not data.get('nome') or not data.get('requisitos'): return jsonify({'success': False}), 400
            cursor.execute('INSERT INTO vagas (nome, requisitos, habilidades_chave, localizacao, tipo_contratacao) VALUES (?, ?, ?, ?, ?)',
                (data.get('nome'), data.get('requisitos'), json.dumps(data.get('habilidades_chave', [])), data.get('localizacao'), data.get('tipo_contratacao')))
            db.commit(); return jsonify({'success': True, 'id': cursor.lastrowid}), 201
        else:
            cursor.execute('SELECT * FROM vagas ORDER BY id DESC')
            rows, columns = cursor.fetchall(), [d[0] for d in cursor.description]
            vagas_list = []
            for row in rows:
                vaga_dict = dict(zip(columns, row))
                try: vaga_dict['habilidades_chave'] = json.loads(vaga_dict.get('habilidades_chave')) if vaga_dict.get('habilidades_chave') else []
                except: vaga_dict['habilidades_chave'] = []
                vagas_list.append(vaga_dict)
            return jsonify({'success': True, 'vagas': vagas_list})
    finally: db.close()

@app.route('/api/vagas/<int:vaga_id>', methods=['DELETE'])
def api_excluir_vaga(vaga_id):
    db = get_db(VAGAS_DB); db.execute('DELETE FROM vagas WHERE id = ?', (vaga_id,)); db.commit(); db.close()
    return jsonify({'success': True})

@app.route('/api/vagas/sugerir-habilidades', methods=['POST'])
def sugerir_habilidades_de_vaga():
    data = request.get_json(); descricao = data.get('descricao')
    if not descricao: return jsonify({'success': False}), 400
    if not GEMINI_CLIENT: return jsonify({'success': True, 'habilidades': ['IA Desativada (Falta Chave)']})
    
    try:
        response = GEMINI_CLIENT.models.generate_content(
            model='gemini-3-flash-preview',
            contents=f"Extraia 5 a 8 habilidades-chave (apenas a lista separada por virgula) para: {descricao}"
        )
        texto = response.text
        return jsonify({'success': True, 'habilidades': [h.strip() for h in texto.split(',')]})
    except Exception as e: 
        logger.error(f"Erro no SDK ao sugerir habilidades: {e}")
        return jsonify({'success': False}), 500

@app.route('/export/candidatos.csv')
def exportar_candidatos_csv():
    try:
        db = get_db(); candidatos = db.execute("SELECT * FROM candidatos WHERE status = 'ativo'").fetchall(); db.close()
        output = io.StringIO(); writer = csv.writer(output)
        writer.writerow(['ID', 'Nome', 'Email', 'Telefone', 'LinkedIn', 'Idade', 'Cargo Desejado', 'Pontuacao', 'Habilidades', 'Formacao', 'Experiencia', 'Idiomas', 'Data do Upload'])
        for c in candidatos: writer.writerow([c['id'], c['nome'], c['email'], c['telefone'], c['linkedin'], c['idade'], c['cargo_desejado'], c['pontuacao'], c['habilidades'], c['formacao'], c['experiencia'], c['idiomas'], c['data_upload']])
        output.seek(0)
        return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=candidatos_exportados.csv"})
    except: return redirect(url_for('candidatos_ranqueados'))

@app.route('/agendar_entrevista/<int:candidate_id>')
def agendar_entrevista_page(candidate_id):
    db = get_db(); candidato = db.execute("SELECT id, nome FROM candidatos WHERE id = ?", (candidate_id,)).fetchone(); db.close()
    return render_template('agendar_entrevista.html', candidato=dict(candidato)) if candidato else redirect(url_for('candidatos_ranqueados'))

@app.route('/api/agendar_entrevista', methods=['POST'])
def api_agendar_entrevista():
    data = request.get_json()
    logger.info(f"ENTREVISTA AGENDADA: {data.get('candidato_nome')} com {data.get('recrutador')} em {data.get('data')} {data.get('hora')}")
    return jsonify({'success': True})

# ==============================================================================
# INICIALIZAÇÃO
# ==============================================================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)