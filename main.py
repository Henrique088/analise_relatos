# # A URL base da API
# url = 'http://192.168.15.135:11434/api/generate'

# # Os dados que vamos enviar (o payload)
# data = {
#     "model": "deepseek-r1:1.5b-qwen-distill-q8_0",
#     "prompt": "Escreva um pequeno poema sobre o mar.",
#     "stream": False  # Pode mudar para True e iterar sobre a resposta se quiser streaming
# }
from flask import Flask, request, jsonify
import requests
import logging
import re

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configurações - Altere conforme necessário
OLLAMA_API_URL = "http://192.168.15.135:11434/api/generate"
MODEL_NAME = "deepseek-r1:1.5b-qwen-distill-q8_0"

def extrair_gravidade(resposta):
    """
    Função para extrair apenas a palavra de gravidade da resposta do modelo
    """
    # Remove tudo antes da última tag de think se existir
    if '<think>' in resposta and '</think>' in resposta:
        partes = resposta.split('</think>')
        if len(partes) > 1:
            resposta = partes[1].strip()
    
    # Procura por qualquer uma das três palavras, ignorando maiúsculas/minúsculas
    padrao = r'\b(grave|mediano|leve)\b'
    correspondencia = re.search(padrao, resposta, re.IGNORECASE)
    
    if correspondencia:
        return correspondencia.group(1).lower()
    else:
        # Se não encontrou, tenta simplificar ainda mais
        resposta_limpa = resposta.strip().lower()
        if resposta_limpa in ['grave', 'mediano', 'leve']:
            return resposta_limpa
        return "indeterminado"

def gerar_resposta_ollama(relato):
    """
    Função para enviar o relato para a API do Ollama e retornar a resposta
    """
    prompt = f"""CLASSIFICAÇÃO DE GRAVIDADE - REGRAS ESTRITAS:

RELATO: "{relato}"

CRITÉRIOS DE CLASSIFICAÇÃO:
- GRAVE: Situações críticas, emergenciais, risco de vida, pensamentos suicidas, violência
- MEDIANO: Problemas significativos mas não emergenciais, conflitos moderados, preocupações sérias  
- LEVE: Desconfortos menores, aborrecimentos do dia-a-dia, situações normais, sentimentos positivos

EXEMPLOS:
- "Pensei em me matar hoje" → GRAVE
- "Estou com muita dor no peito" → GRAVE  
- "Tive uma discussão forte no trabalho" → MEDIANO
- "Estou com dor de cabeça leve" → LEVE
- "Me sinto feliz hoje" → LEVE
- "Tudo tranquilo" → LEVE

INSTRUÇÕES FINAIS:
1. Analise o relato acima pelos critérios
2. Responda APENAS com uma palavra: grave, mediano ou leve
3. Não explique, não pense em voz alta, não use tags

RESPOSTA:"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,  # Temperatura zero para máxima consistência
            # "num_predict": 5,    # Apenas 5 tokens de resposta
            # "stop": ["\n", ".", ","]  # Para na primeira quebra de linha ou pontuação
        }
    }

    try:
        logger.info(f"Enviando relato: {relato[:50]}...")
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        resposta_bruta = data.get('response', '').strip()
        logger.info(f"Resposta bruta recebida: '{resposta_bruta}'")
        
        # Extrai apenas a palavra de gravidade
        gravidade = extrair_gravidade(resposta_bruta)
        
        return gravidade
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na comunicação com Ollama: {e}")
        return "erro_conexao"
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        return "erro_inesperado"

@app.route('/classificar-gravidade', methods=['GET'])
def classificar_gravidade():
    """
    Endpoint que recebe o relato via parâmetro GET 'texto'
    e retorna APENAS a classificação de gravidade
    """
    relato = request.args.get('texto', '').strip()
    
    if not relato:
        return jsonify({
            "erro": "Parâmetro 'texto' é obrigatório",
            "exemplo": "http://localhost:5000/classificar-gravidade?texto=meu+relato+aqui"
        }), 400
    
    classificacao = gerar_resposta_ollama(relato)
    
    return jsonify({
        "relato": relato,
        "gravidade": classificacao,
        "modelo": MODEL_NAME,
        "status": "sucesso"
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar se o servidor está rodando"""
    return jsonify({"status": "online", "servico": "classificador-gravidade"})

@app.route('/teste')
def teste():
    """Endpoint de teste com exemplos"""
    exemplos = [
        "Hoje estou me sentindo depressivo já pensei em suicidio",
        "Estou com uma leve dor de cabeça",
        "Tive uma discussão moderada no trabalho hoje",
        "Me sinto muito bem hoje, tudo tranquilo"
    ]
    
    resultados = []
    for exemplo in exemplos:
        classificacao = gerar_resposta_ollama(exemplo)
        resultados.append({"relato": exemplo, "gravidade": classificacao})
    
    return jsonify({"testes": resultados})

if __name__ == '__main__':
    print("=" * 60)
    print("Servidor Classificador de Gravidade")
    print("=" * 60)
    print(f"Modelo: {MODEL_NAME}")
    print(f"URL local: http://localhost:5000")
    print(f"Endpoint: http://localhost:5000/classificar-gravidade?texto=SEU_RELATO_AQUI")
    print(f"Teste: http://localhost:5000/teste")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)