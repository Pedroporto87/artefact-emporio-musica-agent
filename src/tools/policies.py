"""Ferramentas para consulta de políticas da loja (extraído do PDF)."""

from typing import Optional, Dict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class PolicyTools:
    def __init__(self, pdf_path: str = "data/políticas_da_loja.pdf"):
        self.pdf_path = Path(pdf_path)
        self._policies_cache = None

    def load_policies(self) -> Optional[str]:
        """Carrega e faz cache do texto do PDF de políticas."""
        if self._policies_cache is not None:
            return self._policies_cache

        if not self.pdf_path.exists():
            return None

        if not PDF_AVAILABLE:
            return None  # pdfplumber não instalado

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                full_text = "\n".join(text_parts)
                self._policies_cache = full_text
                return full_text
        except Exception as e:
            print(f"⚠️ Erro ao extrair PDF: {e}")
            return None

    def get_policies_excerpt(self, topic: str) -> Optional[Dict]:
        """
        Busca um trecho relevante das políticas por tópico.

        Args:
            topic: Tópico a buscar (ex: "devolução", "horário", "pagamento")

        Returns:
            Dicionário com topic, excerpt (trecho relevante), relevance_score
        """
        policies = self.load_policies()
        if not policies:
            return {
                "error": "Políticas não disponíveis",
                "message": "Desculpe, não conseguimos acessar o manual de políticas. "
                          "Por favor, entre em contato com nosso atendimento.",
            }

        # Normalizar tópico
        topic_lower = topic.lower()

        # Mapeamento de palavras-chave para seções
        keyword_map = {
            "devolução": ["devolução", "devolver", "retorno", "troca"],
            "troca": ["troca", "trocar", "devolver"],
            "horário": ["horário", "horário de funcionamento", "abre", "fecha", "atendimento"],
            "pagamento": ["pagamento", "pagar", "formas de pagamento", "cartão", "pix", "boleto"],
            "garantia": ["garantia", "defeito", "conserto"],
            "envio": ["envio", "entrega", "frete", "rastreamento", "tracking"],
            "política": ["política", "política de", "regra"],
        }

        # Encontrar palavras-chave relevantes
        relevant_keywords = []
        for key, keywords in keyword_map.items():
            if topic_lower == key or any(kw in topic_lower for kw in keywords):
                relevant_keywords.extend(keywords)

        # Se nenhuma palavra-chave, usar o tópico original
        if not relevant_keywords:
            relevant_keywords = [topic_lower]

        # Buscar linhas relevantes
        lines = policies.split("\n")
        relevant_lines = []

        for line in lines:
            line_lower = line.lower()
            for keyword in relevant_keywords:
                if keyword in line_lower:
                    relevant_lines.append(line)
                    break

        if not relevant_lines:
            return {
                "topic": topic,
                "excerpt": None,
                "message": "Desculpe, não encontramos informações sobre esse assunto. "
                          "Por favor, entre em contato com nosso atendimento.",
            }

        # Retornar as linhas relevantes (limitado a 500 caracteres)
        excerpt = "\n".join(relevant_lines[:5])  # Primeiras 5 linhas relevantes
        if len(excerpt) > 500:
            excerpt = excerpt[:500] + "..."

        return {
            "topic": topic,
            "excerpt": excerpt,
            "found": True,
        }

    def get_store_info(self) -> Dict:
        """Retorna informações básicas da loja."""
        return {
            "name": "Empório da Música",
            "city": "Campo Grande",
            "state": "MS",
            "message": "Bem-vindo ao Empório da Música! 🎵 "
                      "Somos especializados em instrumentos musicais de qualidade. "
                      "Como posso ajudar você hoje?",
        }

    def get_contact_info(self) -> Dict:
        """Retorna informações de contato da loja (extrair do PDF se disponível)."""
        # Se tiver no PDF, extrair de lá; caso contrário, retornar padrão
        policies = self.load_policies()
        if policies and "contato" in policies.lower():
            # TODO: parsear contato do PDF
            pass

        return {
            "city": "Campo Grande",
            "state": "MS",
            "message": "Para dúvidas adicionais, entre em contato com nosso atendimento. "
                      "Será um prazer ajudar! 😊",
        }

    def query_policies(self, question: str) -> str:
        """
        Responde uma pergunta sobre políticas usando o texto do PDF.

        Args:
            question: Pergunta do cliente

        Returns:
            Resposta baseada nas políticas, ou mensagem de encaminhamento
        """
        policies = self.load_policies()
        if not policies:
            return ("Desculpe, não conseguimos acessar o manual de políticas. "
                   "Por favor, entre em contato com nosso atendimento. 😊")

        # Buscar palavras-chave da pergunta
        question_lower = question.lower()

        # Palavras-chave comuns
        if any(word in question_lower for word in ["devolv", "retorn", "trocar"]):
            return self.get_policies_excerpt("devolução").get(
                "excerpt",
                "Temos uma política flexible de devoluções. "
                "Entre em contato para mais detalhes! 😊"
            )
        elif any(word in question_lower for word in ["horário", "abre", "fecha"]):
            return self.get_policies_excerpt("horário").get(
                "excerpt",
                "Você pode consultar nossos horários de funcionamento pelo nosso site. 😊"
            )
        elif any(word in question_lower for word in ["pagamen", "pagar", "cartão", "pix"]):
            return self.get_policies_excerpt("pagamento").get(
                "excerpt",
                "Aceitamos várias formas de pagamento. "
                "Qual você prefere? 💳"
            )
        else:
            # Pergunta genérica sobre políticas
            return self.get_policies_excerpt(question).get(
                "excerpt",
                "Sua pergunta é interessante! Por favor, entre em contato com nosso atendimento "
                "para detalhes específicos. 😊"
            )
