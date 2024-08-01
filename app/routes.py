import datetime
from email.message import EmailMessage
import mimetypes
import os
import re
import smtplib
import ssl
import zipfile
from flask import Blueprint, jsonify, render_template, flash, send_file, url_for, redirect, request, session
import requests
from app.forms import Filtro

bp = Blueprint('routes', __name__)

@bp.route('/')
@bp.route('/index')
def index():
    form = Filtro(obj=None)
    return render_template('index.html', form=form)


@bp.route('/buscar_contas', methods=['GET', 'POST'])
def buscarContas():
    form = Filtro(request.args)
    empresaGeradora = form.empresa.data

    session['empresaGeradora'] = empresaGeradora
    
    if empresaGeradora == 'up380':
        url = "https://upfinance.kamino.tech/api/financeiro/recebimentos/paginada"
        headers = {
            "App": "b929d3c0-eaac-409f-ab8b-10b86e2c5cec",
            "CN": "Upfinance9736",
            "Hash": "gEpBSoJCgT46hH5+gTpEPkqFOn6ASYA6QD6ASUaEQYFFgYSBSko+SUaCgUo6gYRJRzpEgT5AOklFQYQ6R0lBhICFR4GAfoE+mZKFiY9+j4GESkdCRkRH",
            "IDUsr": "47",
            "Usr": "99086dc9-ce87-4c01-852e-782ebf7cbac0"
        }
    elif empresaGeradora == 'unymos':
        url = "https://unymos.kamino.tech/api/financeiro/recebimentos/paginada"
        headers = {
            "App": "b929d3c0-eaac-409f-ab8b-10b86e2c5cec",
            "CN": "UNYMOSGESTAOESI5245",
            "Hash": "gEpBSoJCgT46hH5+gTpEPkqFOn6ASYA6QD6ASUaEQYFFgYSBREFHR4JBSkc6gkl+gjpEPkFEOn5KQT46foGEhUREgEVCgYGCmY+ejpGWhoSWl36RhJaJRUFERUc+",
            "IDUsr": "70",
            "Usr": "4277d297-d8ad-4024-a920-acef44b53ccd"
        }
    else:
        return jsonify({'error': f'Empresa não reconhecida. {empresaGeradora}'}), 400
    
    data_inicial = form.data_inicial.data
    data_final = form.data_final.data
    params = {}
    if data_inicial:
        params['CompetDe'] = data_inicial.strftime('%Y-%m-%d')
    if data_final:
        params['CompetAte'] = data_final.strftime('%Y-%m-%d')

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f"Erro ao fazer a requisição da API: {e}"}), 500
    
    data = response.json()
    keys_to_extract = [
        "ID",
        "Pessoa.NomeExibicao",
        "Pessoa.TelefonePrincipal",
        "Pessoa.EmailPrincipal",
        "NomeTipoReceb",
        "DtaVenc",
        "DtaPagto",
        "VlrVenc",
        "DtaCompet"
    ]
    
    extracted_data = []
    for dados in data['Dados']:
        extracted_item = {}
        for key in keys_to_extract:
            current_level = dados
            nested_keys = key.split('.')
            for nested_key in nested_keys:
                if current_level is None or nested_key not in current_level:
                    current_level = None
                    break
                current_level = current_level.get(nested_key)
            
            if key in ["DtaVenc", "DtaPagto", "DtaCompet"] and current_level:
                current_level = datetime.datetime.strptime(current_level, "%Y-%m-%dT%H:%M:%S").strftime("%d-%m-%Y")
            if current_level is not None:
                extracted_item[key] = current_level
        if "Kamino" in extracted_item.get("NomeTipoReceb", ""):
            extracted_data.append(extracted_item)
    
    return render_template('index.html', data=extracted_data, form=form)


@bp.route('/processar_selecionados', methods=['POST', 'GET'])
def processar_selecionados():
    selecionados = request.form.getlist('selecionar')
    data = request.form.to_dict(flat=False)

    print("Selecionados:", selecionados)

    selected_data = []
    pdf_files = []  # Lista para armazenar os nomes dos arquivos PDF temporários

    for item_id in selecionados:
        print(f"Processando item_id: {item_id}")
        if f'data[{item_id}][ID]' in data and data[f'data[{item_id}][ID]']:
            selected_item = {
                'ID': data[f'data[{item_id}][ID]'][0],
                'Nome': data[f'data[{item_id}][Pessoa.NomeExibicao]'][0] if f'data[{item_id}][Pessoa.NomeExibicao]' in data else '',
                'Telefone': data[f'data[{item_id}][Pessoa.TelefonePrincipal]'][0] if f'data[{item_id}][Pessoa.TelefonePrincipal]' in data else '',
                'Email': data[f'data[{item_id}][Pessoa.EmailPrincipal]'][0] if f'data[{item_id}][Pessoa.EmailPrincipal]' in data else '',
                'TipoReceb': data[f'data[{item_id}][NomeTipoReceb]'][0] if f'data[{item_id}][NomeTipoReceb]' in data else '',
                'DtaVenc': data[f'data[{item_id}][DtaVenc]'][0] if f'data[{item_id}][DtaVenc]' in data else '',
                'DtaPagto': data[f'data[{item_id}][DtaPagto]'][0] if f'data[{item_id}][DtaPagto]' in data else '',
                'VlrVenc': data[f'data[{item_id}][VlrVenc]'][0] if f'data[{item_id}][VlrVenc]' in data else '',
                'DtaCompet': data[f'data[{item_id}][DtaCompet]'][0] if f'data[{item_id}][DtaCompet]' in data else ''
            }

            print(f"Item selecionado: {selected_item}")
            selected_data.append(selected_item)

            empresaGeradora = session.get('empresaGeradora')

            if empresaGeradora == 'up380':
                url = f"https://upfinance.kamino.tech/api/financeiro/contarec/{selected_item['ID']}/boleto"

                headers = {
                    "App": "b929d3c0-eaac-409f-ab8b-10b86e2c5cec",
                    "CN": "Upfinance9736",
                    "Hash": "gEpBSoJCgT46hH5+gTpEPkqFOn6ASYA6QD6ASUaEQYFFgYSBSko+SUaCgUo6gYRJRzpEgT5AOklFQYQ6R0lBhICFR4GAfoE+mZKFiY9+j4GESkdCRkRH",
                    "IDUsr": "47",
                    "Usr": "99086dc9-ce87-4c01-852e-782ebf7cbac0"
                        
                }

            elif empresaGeradora == 'unymos':
                url = f"https://unymos.kamino.tech/api/financeiro/contarec/{selected_item['ID']}/boleto"

                headers = {
                    "App": "b929d3c0-eaac-409f-ab8b-10b86e2c5cec",
                    "CN": "UNYMOSGESTAOESI5245",
                    "Hash": "gEpBSoJCgT46hH5+gTpEPkqFOn6ASYA6QD6ASUaEQYFFgYSBREFHR4JBSkc6gkl+gjpEPkFEOn5KQT46foGEhUREgEVCgYGCmY+ejpGWhoSWl36RhJaJRUFERUc+",
                    "IDUsr": "70",
                    "Usr": "4277d297-d8ad-4024-a920-acef44b53ccd"
                }


            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    content_type = response.headers['Content-Type'].lower()
                    extension = mimetypes.guess_extension(content_type)
                    if not extension:
                        extension = '.bin'

                    sanitized_name = sanitize_filename(selected_item['Nome'])
                    pdf_filename = f"Boleto_{selected_item['ID']}_{sanitized_name}.pdf"
                    pdf_files.append(pdf_filename)  # Adicionando o nome do arquivo à lista
                    

                    print(f"Nome do arquivo: {pdf_filename}")

                    # Salvando o arquivo localmente
                    with open(pdf_filename, 'wb') as f:
                        f.write(response.content)

                    #================================================================================
                    # Envio de e-mail automatico

                    email_senha = open('pass.txt', 'r').read()
                    email_origem = 'boleto.e.nfe@gmail.com'
                    
                    assunto = open('assunto_email.html', 'r').read()
                    if empresaGeradora == "unymos":
                        body = open('corpo_email_unymos.html', 'r').read()
                    if empresaGeradora == 'up380':
                        body = open('corpo_email_up380.html', 'r').read()

                    mensagem = EmailMessage()
                    email_destinatario = selected_item['Email']
                    email_destino = (email_destinatario)
                    mensagem["From"] = email_origem
                    mensagem["To"] = email_destino
                    mensagem["Subject"] = assunto

                    mensagem.add_alternative(body, subtype='html')
                    safe = ssl.create_default_context()

                    anexo_path = pdf_filename
                    mime_type, mime_subtype = mimetypes.guess_type(anexo_path)[0].split('/')

                    with open(anexo_path, 'rb') as ap:
                        mensagem.add_attachment(ap.read(), maintype=mime_type, subtype=mime_subtype, filename=anexo_path)

                    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=safe) as smtp:
                        smtp.login(email_origem, email_senha)
                        smtp.sendmail(email_origem, email_destino, mensagem.as_string())

                    #================================================================================
                else:
                    print(f"Erro na requisição: {response.status_code}")
                    print(response.text)

            except requests.exceptions.RequestException as e:
                print(f"Erro de conexão: {e}")

    # Compactar todos os arquivos PDF em um arquivo ZIP
    zip_filename = 'Boletos.zip'
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for pdf_file in pdf_files:
            zipf.write(pdf_file)

    for file in pdf_files:
        delete_pdf(file)
                          
    form = Filtro()
    return render_template('index.html', form=form)

    # Enviar o arquivo ZIP para download
    #return send_file(zip_filename,
    #                as_attachment=True,
    #                 mimetype='application/zip')

def sanitize_filename(filename):
    return re.sub(r'(?u)[^-\w.]', '', filename).strip().replace(' ', '_')

def delete_pdf(arquivo):

    # Verifica se o arquivo existe
    if os.path.exists(arquivo):
        try:
            os.remove(arquivo)
            print(f"Arquivo {arquivo} apagado com sucesso.")
        except Exception as e:
            print(f"Erro ao apagar o arquivo: {e}")
    else:
        print(f"O arquivo {arquivo} não existe.")
