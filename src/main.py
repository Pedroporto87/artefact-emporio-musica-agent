"""CLI interativa do agente Marina."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent))

from agent import MusicaAgent


def print_header():
    """Imprime header amigável."""
    print("\n" + "="*60)
    print("🎵 EMPÓRIO DA MÚSICA - Atendimento por Chat")
    print("="*60)
    print("Olá! Eu sou Marina, sua assistente. 😊")
    print("\nComo posso ajudar você hoje?")
    print("(Digite 'sair' para encerrar a conversa)")
    print("="*60 + "\n")


def print_separator():
    """Imprime separador."""
    print("-" * 60)


def main():
    """Função principal - loop de conversa."""
    # Carregar variáveis de ambiente
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        print("❌ Erro: ANTHROPIC_API_KEY não definida!")
        print("   Por favor, configure a variável de ambiente ANTHROPIC_API_KEY")
        print("   ou crie um arquivo .env com: ANTHROPIC_API_KEY=sua_chave_aqui")
        sys.exit(1)

    # Inicializar agente
    print("🚀 Carregando dados da loja...")
    try:
        agent = MusicaAgent(api_key=api_key)
        print("✅ Agente pronto!")
    except Exception as e:
        print(f"❌ Erro ao inicializar agente: {e}")
        sys.exit(1)

    # Loop de conversa
    print_header()

    while True:
        # Receber entrada do usuário
        try:
            user_input = input("Você: ").strip()
        except (KeyboardInterrupt, EOFError):
            # Ctrl+C ou EOF
            print("\n\nAté logo! 👋")
            break

        # Verificar se usuário quer sair
        if user_input.lower() in ["sair", "exit", "quit", "bye"]:
            print("\nAgente: Obrigada por usar o atendimento do Empório da Música! 🎵")
            print("         Volte sempre! 😊\n")
            break

        if not user_input:
            continue

        # Processar mensagem
        print_separator()
        print("Agente: ", end="", flush=True)
        try:
            response = agent.process_message(user_input)
            print(response)
        except Exception as e:
            print(f"❌ Erro ao processar mensagem: {e}")
            # Continue mesmo com erro

        print_separator() + "\n"


def run_with_file(input_file: str, output_file: str = None):
    """
    Executa conversa a partir de arquivo de entrada.

    Útil para gerar exemplos de conversas.

    Args:
        input_file: Arquivo com mensagens (uma por linha)
        output_file: Arquivo para salvar conversas (opcional)
    """
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        print("❌ ANTHROPIC_API_KEY não definida!")
        sys.exit(1)

    agent = MusicaAgent(api_key=api_key)

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    conversation = []

    for line in lines:
        user_msg = line.strip()
        if not user_msg:
            continue

        print(f"Você: {user_msg}")
        response = agent.process_message(user_msg)
        print(f"Agente: {response}\n")

        conversation.append({
            "user": user_msg,
            "agent": response,
        })

    # Salvar em arquivo se especificado
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            for turn in conversation:
                f.write(f"**Você:** {turn['user']}\n\n")
                f.write(f"**Agente:** {turn['agent']}\n\n")
                f.write("---\n\n")
        print(f"✅ Conversa salva em: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Executar com arquivo de entrada
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        run_with_file(input_file, output_file)
    else:
        # Modo interativo
        main()
