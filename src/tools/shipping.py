"""Estimativa de frete: regra do manual em Campo Grande, Melhor Envio para outras cidades."""

import json
import os
import re
import urllib.error
import urllib.request
from typing import Dict, List, Optional

STORE_CEP = "79202333"  # Rua 14 de Maio, 3200 — Centro, Campo Grande/MS
VIACEP_URL = "https://viacep.com.br/ws/{cep}/json/"
MELHOR_ENVIO_URL = os.getenv("MELHOR_ENVIO_URL", "https://sandbox.melhorenvio.com.br") + "/api/v2/me/shipment/calculate"
TIMEOUT_S = 15

# Os CSVs não têm peso nem dimensões. Valores estimados da embalagem por categoria (cm, kg).
PACKAGE_BY_CATEGORY = {
    1: {"width": 40, "height": 12, "length": 105, "weight": 4.5},  # Guitarras
    2: {"width": 40, "height": 12, "length": 120, "weight": 5.0},  # Baixos
    5: {"width": 45, "height": 15, "length": 110, "weight": 2.5},  # Violões
    9: {"width": 25, "height": 10, "length": 70, "weight": 0.8},   # Ukuleles
}
# Manual 5.2: baterias acústicas e pianos digitais exigem frete especial com cotação individual.
SPECIAL_FREIGHT_CATEGORIES = {3, 4}

MANUAL_MODALITIES = [
    {"modalidade": "PAC (Correios)", "prazo": "5 a 12 dias úteis"},
    {"modalidade": "SEDEX (Correios)", "prazo": "2 a 5 dias úteis"},
    {"modalidade": "Jadlog (.package)", "prazo": "3 a 8 dias úteis"},
]
ESTIMATE_NOTICE = "Estimativa. O valor final é confirmado pela equipe no fechamento do pedido."


def _http_json(url: str, body: Optional[dict] = None, headers: Optional[dict] = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.loads(resp.read())


def lookup_cep(cep: str) -> Optional[Dict]:
    data = _http_json(VIACEP_URL.format(cep=cep))
    if data.get("erro"):
        return None
    return {"cidade": data.get("localidade"), "uf": data.get("uf"), "bairro": data.get("bairro")}


def quote_melhor_envio(cep: str, package: Dict, insurance_value: float, quantity: int, token: str) -> List[Dict]:
    body = {
        "from": {"postal_code": STORE_CEP},
        "to": {"postal_code": cep},
        "products": [{"id": "item", **package, "insurance_value": round(insurance_value, 2), "quantity": quantity}],
        "options": {"receipt": False, "own_hand": False},
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": os.getenv("MELHOR_ENVIO_USER_AGENT", "Emporio da Musica (contato@emporiodamusica.com.br)"),
    }
    return parse_quote(_http_json(MELHOR_ENVIO_URL, body, headers))


def parse_quote(services: List[Dict]) -> List[Dict]:
    """Mantém só os serviços disponíveis (a API devolve 'error' nos recusados), do mais barato ao mais caro."""
    options = []
    for s in services:
        price = s.get("custom_price") or s.get("price")
        if s.get("error") or price is None:
            continue
        options.append({
            "transportadora": (s.get("company") or {}).get("name"),
            "servico": s.get("name"),
            "preco": round(float(price), 2),
            "prazo_dias_uteis": s.get("custom_delivery_time") or s.get("delivery_time"),
        })
    return sorted(options, key=lambda o: o["preco"])


def estimate_shipping(cep: str, product: Dict, quantity: int = 1) -> Dict:
    """`product` precisa de category_id e preço de venda (promoção já aplicada)."""
    cep = re.sub(r"\D", "", cep or "")
    if len(cep) != 8:
        return {"status": "cep_invalido", "mensagem": "O CEP precisa ter 8 dígitos. Peça o CEP ao cliente."}

    try:
        destino = lookup_cep(cep)
    except (urllib.error.URLError, TimeoutError, ValueError):
        return {"status": "servico_indisponivel", "mensagem": "Não foi possível consultar o CEP agora.",
                "modalidades_do_manual": MANUAL_MODALITIES}
    if destino is None:
        return {"status": "cep_nao_encontrado", "mensagem": f"O CEP {cep} não existe. Confirme com o cliente."}

    total = product["sale_price"] * quantity
    if destino["cidade"] == "Campo Grande" and destino["uf"] == "MS":
        return {
            "status": "ok", "destino": destino, "origem": "Campo Grande/MS",
            "opcoes": [{
                "transportadora": "Motoboy próprio da loja",
                "servico": "Entrega local",
                "preco": 0.0 if total > 500 else 35.0,
                "prazo": "1 a 3 dias úteis",
            }],
            "regra": "Manual 5.1: frete grátis acima de R$ 500,00; abaixo disso, taxa fixa de R$ 35,00.",
        }

    if product["category_id"] in SPECIAL_FREIGHT_CATEGORIES:
        return {"status": "frete_especial", "destino": destino,
                "mensagem": "Manual 5.2: instrumentos de grande porte exigem cotação individual com a equipe."}

    token = os.getenv("MELHOR_ENVIO_TOKEN")
    if not token:
        return {"status": "sem_cotacao", "destino": destino, "modalidades_do_manual": MANUAL_MODALITIES,
                "mensagem": "Cotação automática indisponível. Informe modalidades e prazos e encaminhe à equipe."}

    try:
        opcoes = quote_melhor_envio(cep, PACKAGE_BY_CATEGORY[product["category_id"]], product["sale_price"],
                                    quantity, token)
    except (urllib.error.URLError, TimeoutError, ValueError):
        return {"status": "servico_indisponivel", "destino": destino, "modalidades_do_manual": MANUAL_MODALITIES,
                "mensagem": "A cotação automática falhou. Informe modalidades e prazos do manual."}
    if not opcoes:
        return {"status": "sem_servico_disponivel", "destino": destino,
                "mensagem": "Nenhuma transportadora atende esse envio. Encaminhe para cotação com a equipe."}
    return {"status": "ok", "destino": destino, "origem": "Campo Grande/MS", "opcoes": opcoes,
            "aviso": ESTIMATE_NOTICE}
