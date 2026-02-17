from flask import Flask, request, jsonify
import json
import requests
import logging
import re
from flask_cors import CORS # Recomendado para evitar erros no React

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app) # Libera o acesso para o seu frontend React

OLLAMA_API_URL = "http://192.168.15.135:11434/api/generate"
MODEL_NAME = "llama3" # Atualizado para Llama 3

def gerar_cards_dashboard(mood, intensidade, periodo):
    """
    Gera cards personalizados com base no estado emocional e período do dia.
    """
    # Criamos um contexto dinâmico para a IA
    contexto_usuario = f"O usuário relatou estar se sentindo '{mood}' (intensidade {intensidade}/5) durante o período da '{periodo}'."

    prompt = f"""
    {contexto_usuario}

    Com base nisso, gere 3 cards para um dashboard de saúde mental em português.
    A 'Dica do Dia' deve ser prática para o momento, a 'Estatística' deve ser um dado de bem-estar relevante ao mood, e a 'Motivação' deve ser um acolhimento.

    Retorne APENAS um objeto JSON puro, sem textos extras, seguindo rigorosamente este modelo:
    {{
      "periodo": "{periodo}",
      "cards": [
        {{"title": "Dica do Dia", "content": "..."}},
        {{"title": "Estatística", "content": "..."}},
        {{"title": "Motivação", "content": "..."}}
      ]
    }}
    """

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": { "temperature": 0.8 } # Aumentado levemente para maior criatividade na personalização
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=40)
        response.raise_for_status()

        resposta_ollama = response.json()
        logger.info(f"Resposta bruta do Ollama: {resposta_ollama}")  # Debug
        
        resposta_texto = response.json().get('response', '').strip()
        return json.loads(resposta_texto)
        
    except Exception as e:
        logger.error(f"Erro ao gerar cards personalizados: {e}")
        # Fallback também estruturado no novo formato
        return {
            "periodo": periodo,
            "cards": [
                {"title": "Dica do Dia", "content": "Tire 5 minutos para uma respiração consciente agora."},
                {"title": "Lembrete", "content": "Sua saúde mental é uma prioridade, não um luxo."},
                {"title": "Apoio", "content": "Estamos aqui para acompanhar sua jornada, passo a passo."}
            ]
        }

def gerar_resposta_ollama(relato):
    """
    Classifica a gravidade do relato de forma direta.
    """
    prompt = f"""Você é um assistente de triagem psicológica altamente treinado.
Analise o relato do usuário abaixo para identificar o nível de suporte necessário.

RELATO: "{relato}"

CRITÉRIOS DE ANÁLISE:
1. Sentimento: Qual a emoção predominante?
2. Risco: Existe menção a autolesão, ideação suicida ou violência? (Isso torna o caso GRAVE imediatamente)
3. Urgência: O usuário parece estar em crise aguda ou é um desabafo de cansaço acumulado?

CLASSIFICAÇÕES POSSÍVEIS:
- LEVE: Estresse cotidiano, sentimentos positivos ou desabafos sem sinais de ruptura emocional.
- MEDIANO: Tristeza profunda, ansiedade nítida, conflitos interpessoais sérios, mas sem risco de vida.
- GRAVE: Ideação suicida, automutilação, crises de pânico agudas ou desesperança extrema ("não aguento mais" sem contexto).

Responda APENAS em formato JSON:
{{
  "analise_curta": "breve justificativa da sua decisão",
  "gravidade": "leve/mediano/grave",
  "pontuacao_risco": 1-10
}}
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": { "temperature": 0.0 } # 0.0 para ser bem objetivo
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
        response.raise_for_status()

        print(response.json())        
        # Pega a resposta e limpa pontuações
        classificacao = response.json().get('response', '').strip().lower()
        # Filtra apenas a palavra desejada caso a IA escreva uma frase
        if 'grave' in classificacao: return 'grave'
        if 'mediano' in classificacao: return 'mediano'
        return 'leve'
        
    except Exception as e:
        logger.error(f"Erro na classificação: {e}")
        return "indeterminado"

@app.route('/classificar-gravidade', methods=['GET'])
def classificar_gravidade():
    relato = request.args.get('texto', '').strip()
    if not relato:
        return jsonify({"erro": "Texto obrigatório"}), 400
    
    classificacao = gerar_resposta_ollama(relato)
    return jsonify({"relato": relato, "gravidade": classificacao})

@app.route('/cards-dashboard', methods=['GET'])
def get_cards():
    mood = request.args.get('mood', '').strip()
    intensidade = request.args.get('intensidade', '').strip()
    periodo = request.args.get('periodo', '').strip()
    
    cards = gerar_cards_dashboard(mood, intensidade, periodo)
    return jsonify(cards)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)